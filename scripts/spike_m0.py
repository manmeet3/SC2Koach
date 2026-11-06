"""M0 spike: check the design's data assumptions against real replays.

Usage: python scripts/spike_m0.py [replay_dir] [--out out/spike]

Writes (to the gitignored out/ dir):
  results.jsonl     one record per replay (no player names)
  summary.json      aggregated answers to the M0 checklist
  manual-check.md   values to compare against the in-game UI (has player names; local only)
and prints the summary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics as st
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import sc2reader

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sc2koach.errors import UnsupportedReplayError  # noqa: E402
from sc2koach.gamedata import (  # noqa: E402
    EXTRA_SUPPLIES,
    EXTRA_SUPPLIES_ABILITY,
    FLYING_TOWN_HALLS,
    LAND_ABILITIES,
    SUPPLY_CAP,
    TOWN_HALL_BUILD_TYPES,
    WORKER_TYPES,
    supply_table,
)
from sc2koach.gametime import LOOPS_PER_SECOND, STATS_INTERVAL_LOOPS  # noqa: E402
from sc2koach.parser import classify_mode  # noqa: E402

ZERG_DRONE_BUILDINGS = {
    "Hatchery", "Extractor", "SpawningPool", "EvolutionChamber", "RoachWarren", "BanelingNest",
    "SpineCrawler", "SporeCrawler", "HydraliskDen", "LurkerDenMP", "InfestationPit", "Spire",
    "NydusNetwork", "UltraliskCavern",
}  # fmt: skip


def sec(loop: float) -> float:
    return loop / LOOPS_PER_SECOND


def _pid(ev) -> int | None:
    p = getattr(ev, "player", None)
    return getattr(p, "pid", None)


def analyze(path: Path) -> dict:
    rec: dict = {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    t0 = time.perf_counter()
    try:
        r = sc2reader.load_replay(str(path), load_level=4)
    except Exception as exc:
        rec.update(load_ok=False, error=f"{type(exc).__name__}: {exc}"[:200])
        return rec
    rec.update(load_ok=True, load_s=round(time.perf_counter() - t0, 3), build=r.build)
    rec["duration_s"] = round(sec(r.frames), 1)
    rec["is_ladder"] = bool(r.is_ladder)
    try:
        mode = classify_mode(r)
        rec.update(supported=True, mode=mode.mode)
    except UnsupportedReplayError as exc:
        rec.update(supported=False, reason=str(exc), type=r.type)
        return rec

    players = {p.pid: p for p in r.players}
    race = {pid: p.play_race for pid, p in players.items()}
    rec["races"] = sorted(race.values())
    rec["composition"] = " vs ".join(
        "".join(sorted(p.play_race[0] for p in t.players)) for t in r.teams
    )

    # 2 MMR, 9 slots/toon handles
    ratings = {pid: p.init_data.get("scaled_rating") for pid, p in players.items()}
    rec["mmr_present"] = sum(1 for v in ratings.values() if v and v > 0)
    rec["n_players"] = len(players)
    rec["teammates_share_mmr"] = [
        len({ratings[p.pid] for p in t.players}) == 1 for t in r.teams if len(t.players) > 1
    ]
    rec["toon_handles_ok"] = all(p.toon_handle for p in players.values())
    rec["sids_by_team"] = [sorted(p.sid for p in t.players) for t in r.teams]
    rec["archon_leader_ids"] = sorted({str(p.archon_leader_id) for p in players.values()})

    # Walk tracker events once.
    unit_type: dict[int, str] = {}
    unit_owner: dict[int, int] = {}
    alive: set[int] = set()
    finished: set[int] = set()
    provided: dict[int, float] = {}
    cap = defaultdict(float)
    town_halls: dict[int, list] = defaultdict(list)  # pid -> [(loop, x, y, unit_id, source)]
    drone_deaths_by_loop: dict[int, Counter] = defaultdict(Counter)
    zerg_building_inits: list[tuple[int, int]] = []
    overlords_born = Counter()
    landings: list[dict] = []
    coords: list[tuple[float, float]] = []
    snaps: list[dict] = []

    def worker_count(pid: int) -> int:
        return sum(
            1 for u in alive if unit_owner.get(u) == pid and unit_type.get(u) in WORKER_TYPES
        )

    def living_supply(pid: int) -> float:
        total = 0.0
        for u in alive:
            if unit_owner.get(u) == pid and u in finished:
                total += supply_cost.get(u, 0.0)
        return total

    supply_cost: dict[int, float] = {}
    tracker = sorted(r.tracker_events, key=lambda e: e.frame)
    first_stats = {}
    for e in tracker:
        if type(e).__name__ == "PlayerStatsEvent" and e.pid in players:
            first_stats.setdefault(e.pid, e)
    tables = {
        pid: supply_table(race[pid], first_stats[pid].food_made if pid in first_stats else 0)
        for pid in players
    }
    rec["starting_workers"] = sorted({s.workers_active_count for s in first_stats.values()})
    extra_supplies = sorted(
        (e.frame, _pid(e), getattr(e, "target_unit_id", None))
        for e in r.game_events
        if type(e).__name__ == "TargetUnitCommandEvent"
        and getattr(e, "ability_name", None) == EXTRA_SUPPLIES_ABILITY
    )
    rec["extra_supplies_casts"] = len(extra_supplies)
    xs_i = 0
    for e in tracker:
        while xs_i < len(extra_supplies) and extra_supplies[xs_i][0] <= e.frame:
            _, xs_pid, target = extra_supplies[xs_i]
            if target in provided and unit_owner.get(target) == xs_pid:
                provided[target] += EXTRA_SUPPLIES
                cap[xs_pid] += EXTRA_SUPPLIES
            xs_i += 1
        n = type(e).__name__
        if n == "UnitBornEvent" or n == "UnitInitEvent":
            pid = e.control_pid
            unit_type[e.unit_id] = e.unit_type_name
            unit_owner[e.unit_id] = pid
            alive.add(e.unit_id)
            supply_cost[e.unit_id] = float(getattr(e.unit, "supply", 0) or 0)
            if e.x is not None:
                coords.append((e.x, e.y))
            if n == "UnitBornEvent":
                finished.add(e.unit_id)
                if pid in players and e.unit_type_name in tables[pid]:
                    provided[e.unit_id] = tables[pid][e.unit_type_name]
                    cap[pid] += provided[e.unit_id]
                if e.unit_type_name == "Overlord" and e.frame > 0:
                    overlords_born[pid] += 1
            if e.unit_type_name in TOWN_HALL_BUILD_TYPES and pid in players:
                town_halls[pid].append((e.frame, e.x, e.y, e.unit_id, n))
            if (
                n == "UnitInitEvent"
                and race.get(pid) == "Zerg"
                and e.unit_type_name in ZERG_DRONE_BUILDINGS
            ):
                zerg_building_inits.append((e.frame, pid))
        elif n == "UnitDoneEvent":
            finished.add(e.unit_id)
            t = unit_type.get(e.unit_id)
            pid = unit_owner.get(e.unit_id)
            if pid in players and t in tables[pid] and e.unit_id not in provided:
                provided[e.unit_id] = tables[pid][t]
                cap[pid] += provided[e.unit_id]
        elif n == "UnitDiedEvent":
            u = e.unit_id
            pid = unit_owner.get(u)
            if unit_type.get(u) == "Drone" and e.killer_pid is None:
                drone_deaths_by_loop[e.frame][pid] += 1
            alive.discard(u)
            if u in provided:
                cap[pid] -= provided.pop(u)
        elif n == "UnitTypeChangeEvent":
            prev = unit_type.get(e.unit_id)
            unit_type[e.unit_id] = e.unit_type_name
            if prev in FLYING_TOWN_HALLS and e.unit_type_name == FLYING_TOWN_HALLS[prev]:
                landings.append(
                    {"loop": e.frame, "unit": e.unit_id, "pid": unit_owner.get(e.unit_id)}
                )
        elif n == "PlayerStatsEvent" and e.pid in players:
            snaps.append(
                {
                    "loop": e.frame,
                    "pid": e.pid,
                    "regular": e.frame % STATS_INTERVAL_LOOPS == 0,
                    "food_used": e.food_used,
                    "food_made": e.food_made,
                    "workers_active": e.workers_active_count,
                    "workers_events": worker_count(e.pid),
                    "cap_events": min(SUPPLY_CAP, cap[e.pid]),
                    "living_supply": living_supply(e.pid),
                    "min_rate": e.minerals_collection_rate,
                    "gas_rate": e.vespene_collection_rate,
                    "minerals": e.minerals_current,
                    "army_current": e.minerals_used_current_army + e.vespene_used_current_army,
                    "army_active": e.minerals_used_active_forces + e.vespene_used_active_forces,
                    "min_collected_est": (
                        e.minerals_current
                        + e.minerals_used_in_progress_army
                        + e.minerals_used_in_progress_economy
                        + e.minerals_used_in_progress_technology
                        + e.minerals_used_current_army
                        + e.minerals_used_current_economy
                        + e.minerals_used_current_technology
                        + e.minerals_lost_army
                        + e.minerals_lost_economy
                        + e.minerals_lost_technology
                    ),
                }
            )

    # 3 food_used vs living (finished) supply; 7 cap rebuild vs snapshot; 5 workers
    reg = [s for s in snaps if s["regular"] and s["loop"] > 0]
    rec["cap_match_frac"] = _frac(
        reg, lambda s: abs(min(SUPPLY_CAP, s["food_made"]) - s["cap_events"]) < 0.01
    )
    rec["cap_match_by_race"] = {
        rc: _frac(
            [s for s in reg if race[s["pid"]] == rc],
            lambda s: abs(min(SUPPLY_CAP, s["food_made"]) - s["cap_events"]) < 0.01,
        )
        for rc in set(race.values())
    }
    rec["used_minus_living"] = [round(s["food_used"] - s["living_supply"], 2) for s in reg]
    rec["used_gt_living_frac"] = _frac(reg, lambda s: s["food_used"] - s["living_supply"] >= 1)
    rec["used_lt_living_frac"] = _frac(reg, lambda s: s["living_supply"] - s["food_used"] >= 1)
    rec["workers"] = [
        {
            "race": race[s["pid"]],
            "t": round(sec(s["loop"]), 1),
            "snap": s["workers_active"],
            "events": s["workers_events"],
        }
        for s in reg
        if sec(s["loop"]) <= 480
    ]
    rec["army_fields"] = [
        (s["army_current"], s["army_active"]) for s in reg if s["army_current"] or s["army_active"]
    ]

    # 4 collection-rate unit: collected minerals per real minute vs reported rate (T/P only)
    traders = set()
    trade_events = Counter()
    for e in r.game_events:
        n = type(e).__name__
        if n in ("ResourceTradeEvent", "ResourceRequestEvent", "ResourceRequestFulfillEvent"):
            trade_events[n] += 1
            if _pid(e) is not None:
                traders.add(_pid(e))
            rec_p = getattr(e, "recipient", None)
            if rec_p is not None:
                traders.add(rec_p.pid)
    rec["trade_events"] = dict(trade_events)
    ratios = []
    for pid in players:
        if race[pid] == "Zerg" or pid in traders:
            continue
        w = [s for s in reg if s["pid"] == pid and 120 <= sec(s["loop"]) <= 360]
        if len(w) < 5:
            continue
        minutes = (sec(w[-1]["loop"]) - sec(w[0]["loop"])) / 60
        collected = w[-1]["min_collected_est"] - w[0]["min_collected_est"]
        mean_rate = st.mean(s["min_rate"] for s in w[:-1])
        if mean_rate > 0:
            ratios.append(collected / (mean_rate * minutes))
    rec["rate_ratios"] = ratios

    # 5b Zerg drone -> building emits UnitDiedEvent (no killer) at the same loop
    matched = 0
    for loop, pid in zerg_building_inits:
        for dl in range(loop - 2, loop + 3):
            if drone_deaths_by_loop.get(dl, {}).get(pid):
                drone_deaths_by_loop[dl][pid] -= 1
                matched += 1
                break
    rec["zerg_building_inits"] = len(zerg_building_inits)
    rec["zerg_inits_with_drone_death"] = matched
    rec["overlords_born"] = {
        str(pid): overlords_born[pid] for pid in players if race[pid] == "Zerg"
    }

    # 8 coordinates / natural distance
    rec["max_coord"] = max((max(x, y) for x, y in coords), default=None)
    nat = []
    for ths in town_halls.values():
        ths = sorted(ths)
        start = next((t for t in ths if t[4] == "UnitBornEvent"), None)
        if not start:
            continue
        others = [t for t in ths if t[4] == "UnitInitEvent" and _dist(t, start) > 5]
        if others:
            nat.append(round(_dist(others[0], start), 1))
    rec["natural_distances"] = nat

    # 10 leaves
    leaves = []
    for e in r.game_events:
        if type(e).__name__ == "PlayerLeaveEvent" and _pid(e) in players:
            pid = _pid(e)
            later = [s for s in snaps if s["pid"] == pid and s["loop"] > e.frame]
            at_leave = any(s["pid"] == pid and s["loop"] == e.frame for s in snaps)
            leaves.append(
                {
                    "before_end_s": round(sec(r.frames - e.frame), 1),
                    "snaps_after": len(later),
                    "extra_snap_at_leave": at_leave,
                }
            )
    rec["leaves"] = leaves
    rec["mid_game_leavers"] = sum(1 for lv in leaves if lv["before_end_s"] > 10)

    # 12 landings vs Land commands
    land_cmds = [
        (e.frame, _pid(e), e.location)
        for e in r.game_events
        if type(e).__name__ == "TargetPointCommandEvent"
        and getattr(e, "ability_name", None) in LAND_ABILITIES
    ]
    land_out = []
    for ld in landings:
        cands = [c for c in land_cmds if c[1] == ld["pid"] and c[0] <= ld["loop"]]
        if not cands:
            land_out.append({"matched": False})
            continue
        c = max(cands)
        hx, hy = c[2][0], c[2][1]
        own = [t for t in town_halls.get(ld["pid"], []) if t[0] <= ld["loop"]]
        nearest = min((_dist((0, hx, hy), t) for t in own), default=None)
        land_out.append(
            {
                "matched": True,
                "lag_s": round(sec(ld["loop"] - c[0]), 2),
                "nearest_own_th": None if nearest is None else round(nearest, 1),
            }
        )
    rec["landings"] = land_out
    return rec


def _frac(items, pred) -> float | None:
    items = list(items)
    return round(sum(1 for i in items if pred(i)) / len(items), 4) if items else None


def _ratio(n: int, total: int) -> str:
    return f"{n}/{total}"


def _dist(a, b) -> float:
    return math.hypot(a[1] - b[1], a[2] - b[2])


def _pct(vals, q):
    vals = sorted(vals)
    if not vals:
        return None
    return vals[min(len(vals) - 1, int(q * len(vals)))]


def summarize(recs: list[dict]) -> dict:
    ok = [r for r in recs if r.get("load_ok")]
    team = [r for r in ok if r.get("supported")]
    s: dict = {
        "replays": len(recs),
        "builds": dict(Counter(r["build"] for r in ok).most_common()),
        "1_load": {
            "ok": len(ok),
            "failed": [r["error"] for r in recs if not r.get("load_ok")],
        },
        "modes": dict(Counter(r.get("mode") or f"unsupported:{r.get('type')}" for r in ok)),
        "unsupported_reasons": dict(Counter(r["reason"] for r in ok if not r.get("supported"))),
        "archon_leader_ids_seen": dict(Counter(v for r in team for v in r["archon_leader_ids"])),
        "ladder": sum(1 for r in team if r["is_ladder"]),
        "games_under_60s": sum(1 for r in team if r["duration_s"] < 60),
        "starting_workers_by_build": {
            str(b): sorted({str(r.get("starting_workers")) for r in team if r["build"] == b})
            for b in sorted({r["build"] for r in team})
        },
    }
    players = sum(r["n_players"] for r in team)
    shares = [x for r in team for x in r["teammates_share_mmr"]]
    s["2_mmr"] = {
        "players_with_mmr": f"{sum(r['mmr_present'] for r in team)}/{players}",
        "teams_where_all_members_share_rating": f"{sum(shares)}/{len(shares)}",
    }
    diffs = [d for r in team for d in r["used_minus_living"]]
    s["3_food_used"] = {
        "snapshots": len(diffs),
        "used_ge_living_plus1_frac": round(sum(d >= 1 for d in diffs) / len(diffs), 3),
        "used_le_living_minus1_frac": round(sum(d <= -1 for d in diffs) / len(diffs), 3),
        "diff_p10_p50_p90": [_pct(diffs, 0.1), _pct(diffs, 0.5), _pct(diffs, 0.9)],
    }
    ratios = [x for r in team for x in r["rate_ratios"]]
    s["4_rate_unit"] = {
        "players": len(ratios),
        "collected_over_rate_p10_p50_p90": [round(_pct(ratios, q), 3) for q in (0.1, 0.5, 0.9)]
        if ratios
        else None,
        "interpretation": "~1.0 = per real (Faster) minute; ~1.4 = per Normal minute",
    }
    by_race = defaultdict(list)
    at4 = defaultdict(list)
    for r in team:
        for w in r["workers"]:
            by_race[w["race"]].append(w["events"] - w["snap"])
            if 235 <= w["t"] <= 236:
                at4[w["race"]].append(w["events"] - w["snap"])
    s["5_workers"] = {
        rc: {
            "snapshots_to_8m": len(v),
            "exact_match_frac": round(sum(d == 0 for d in v) / len(v), 3),
            "events_minus_snap_p10_p50_p90": [_pct(v, 0.1), _pct(v, 0.5), _pct(v, 0.9)],
            "at_3m56_p10_p50_p90": [_pct(at4[rc], 0.1), _pct(at4[rc], 0.5), _pct(at4[rc], 0.9)],
        }
        for rc, v in by_race.items()
    }
    zi = sum(r["zerg_building_inits"] for r in team)
    s["5_zerg_drone_morph_death"] = f"{sum(r['zerg_inits_with_drone_death'] for r in team)}/{zi}"
    pairs = [p for r in team for p in r["army_fields"]]
    s["6_army_fields"] = {
        "nonzero_snapshots": len(pairs),
        "current_eq_active_frac": round(sum(a == b for a, b in pairs) / len(pairs), 3),
        "active_minus_current_p50_p90": [
            _pct([b - a for a, b in pairs], 0.5),
            _pct([b - a for a, b in pairs], 0.9),
        ],
    }
    zerg_players = [v for r in team for v in r["overlords_born"].values()]
    capm = [r["cap_match_frac"] for r in team if r["cap_match_frac"] is not None]
    cap_race = defaultdict(list)
    for r in team:
        for rc, v in r["cap_match_by_race"].items():
            if v is not None:
                cap_race[rc].append(v)
    s["7_supply_cap"] = {
        "zerg_players_with_overlord_born_events": _ratio(
            sum(v > 0 for v in zerg_players), len(zerg_players)
        ),
        "event_cap_equals_snapshot_food_made_mean": round(st.mean(capm), 4),
        "by_race_mean": {rc: round(st.mean(v), 4) for rc, v in cap_race.items()},
    }
    nat = [d for r in team for d in r["natural_distances"]]
    s["8_coords"] = {
        "max_coord": max(r["max_coord"] or 0 for r in team),
        "natural_distance_p10_p50_p90": [_pct(nat, 0.1), _pct(nat, 0.5), _pct(nat, 0.9)],
    }
    patterns = Counter(str(r["sids_by_team"]) for r in team)
    s["9_slots"] = {
        "toon_handles_ok": f"{sum(r['toon_handles_ok'] for r in team)}/{len(team)}",
        "sid_patterns": dict(patterns.most_common(6)),
    }
    leaves = [lv for r in team for lv in r["leaves"]]
    mid = [lv for lv in leaves if lv["before_end_s"] > 10]
    s["10_leaves"] = {
        "leave_events": len(leaves),
        "mid_game(>10s before end)": len(mid),
        "games_with_mid_game_leaver": sum(1 for r in team if r["mid_game_leavers"]),
        "mid_game_leavers_with_snaps_after": _ratio(
            sum(lv["snaps_after"] > 0 for lv in mid), len(mid)
        ),
        "mid_game_leavers_with_extra_snap_at_leave": _ratio(
            sum(lv["extra_snap_at_leave"] for lv in mid), len(mid)
        ),
    }
    te = Counter()
    for r in team:
        te.update(r["trade_events"])
    s["11_trades"] = {
        "events": dict(te),
        "games_with_any": sum(1 for r in team if r["trade_events"]),
    }
    lands = [ld for r in team for ld in r["landings"]]
    m = [ld for ld in lands if ld["matched"]]
    s["12_landings"] = {
        "landings": len(lands),
        "with_land_command": len(m),
        "lag_s_p50_p90": [_pct([x["lag_s"] for x in m], 0.5), _pct([x["lag_s"] for x in m], 0.9)],
        "landed_>15_from_own_town_halls": sum(
            1 for x in m if x["nearest_own_th"] is not None and x["nearest_own_th"] > 15
        ),
    }
    s["13_timing"] = {
        "load_s_p50_max": [_pct([r["load_s"] for r in ok], 0.5), max(r["load_s"] for r in ok)],
        "longest_3v3_duration_s_load_s": max(
            ((r["duration_s"], r["load_s"]) for r in team if r["mode"] == "3v3"), default=None
        ),
    }
    return s


def pick_fixtures(recs: list[dict]) -> list[dict]:
    """One replay per fixture slot among normal-length games; no player names."""
    team = [
        r
        for r in recs
        if r.get("supported") and r["mode"] in ("2v2", "3v3") and 480 <= r["duration_s"] <= 1800
    ]
    latest = max(r["build"] for r in team)
    tags = {
        "terran": lambda r: "Terran" in r["races"],
        "protoss": lambda r: "Protoss" in r["races"],
        "zerg": lambda r: "Zerg" in r["races"],
        "mid_game_leaver": lambda r: r["mid_game_leavers"] > 0,
        "resource_trade": lambda r: bool(r["trade_events"]),
        "cc_landing": lambda r: any(ld.get("matched") for ld in r["landings"]),
        "ruleset_8_workers": lambda r: r.get("starting_workers") == [8],
        "latest_build": lambda r: r["build"] == latest,
    }
    standard = lambda r: r.get("starting_workers") == [12]  # noqa: E731
    slots = [
        # Busiest game: every race, leaver, trade, CC landing, latest build.
        lambda r: r["mode"] == "3v3" and standard(r),
        # Clean baseline: nobody leaves early.
        lambda r: r["mode"] == "3v3" and standard(r) and r["mid_game_leavers"] == 0,
        # 2v2 on the 8-starting-worker ruleset (build 97563).
        lambda r: r["mode"] == "2v2" and r.get("starting_workers") == [8],
    ]
    chosen: list[dict] = []
    for slot in slots:
        cands = [r for r in team if slot(r) and r not in chosen]
        if cands:
            chosen.append(
                max(
                    cands,
                    key=lambda r: (sum(f(r) for f in tags.values()), -abs(r["duration_s"] - 1000)),
                )
            )
    out = []
    for r in chosen:
        out.append(
            {
                "file": r["file"],
                "sha256": r["sha256"],
                "build": r["build"],
                "mode": r["mode"],
                "composition": r["composition"],
                "duration_s": r["duration_s"],
                "tags": sorted(k for k, f in tags.items() if f(r)),
            }
        )
    return out


def manual_sheet(replay_dir: Path, fixtures: list[dict]) -> str:
    """Values to check against the in-game UI. Contains player names: local only."""
    lines = [
        "# M0 manual check (local only — contains player names)",
        "",
        "Open each replay, pause at each time, and compare with the in-game panels:",
        "supply (top bar / Income tab), Workers (Income tab), Income per minute (Income tab),",
        "Army value (Army tab). Note which army column matches the in-game number.",
        "",
    ]
    for fx in fixtures[:3]:
        r = sc2reader.load_replay(str(replay_dir / fx["file"]), load_level=4)
        lines += [f"## {fx['file']} ({fx['mode']}, {fx['composition']})", ""]
        lines.append(
            "| Time | Player | Race | Supply | Workers | Income min/gas "
            "| Army (current) | Army (active) |"
        )
        lines.append("|---|---|---|---|---|---|---|---|")
        for target in (240, 360, 480):
            loop = round(target * LOOPS_PER_SECOND / STATS_INTERVAL_LOOPS) * STATS_INTERVAL_LOOPS
            for e in r.tracker_events:
                if type(e).__name__ == "PlayerStatsEvent" and e.frame == loop and e.player:
                    t = sec(e.frame)
                    lines.append(
                        f"| {int(t // 60)}:{int(t % 60):02d} | {e.player.name} "
                        f"| {e.player.play_race} | "
                        f"{e.food_used:g}/{e.food_made:g} | {e.workers_active_count} | "
                        f"{e.minerals_collection_rate}/{e.vespene_collection_rate} | "
                        f"{e.minerals_used_current_army + e.vespene_used_current_army} | "
                        f"{e.minerals_used_active_forces + e.vespene_used_active_forces} |"
                    )
        lines.append("")
    lines += [
        "## CC landing",
        "",
        "For the fixture tagged `cc_landing`, confirm the landed CC/Orbital position matches",
        "where the game shows it (results.jsonl lists the landing times).",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("replay_dir", nargs="?", default="replays")
    ap.add_argument("--out", default="out/spike")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    replay_dir, out = Path(args.replay_dir), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    paths = sorted(replay_dir.glob("*.SC2Replay"))
    t0 = time.perf_counter()
    with ProcessPoolExecutor(args.workers) as ex:
        recs = list(ex.map(analyze, paths, chunksize=4))
    with (out / "results.jsonl").open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    summary = summarize(recs)
    summary["wall_s"] = round(time.perf_counter() - t0, 1)
    fixtures = pick_fixtures(recs)
    summary["fixtures"] = fixtures
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    manifest = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "replays.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(fixtures, indent=2) + "\n", encoding="utf-8")
    (out / "manual-check.md").write_text(manual_sheet(replay_dir, fixtures), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
