"""Build a normalized ReplayModel (with GameRules) from a raw sc2reader replay (design §4, §5)."""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .. import gamedata
from ..gametime import STATS_INTERVAL_LOOPS, loop_to_seconds
from ..models import (
    AnalysisWarning,
    ExtraSuppliesCast,
    GameInfo,
    GameRules,
    LandCommand,
    Player,
    PlayerRules,
    Point,
    ReplayModel,
    ResourceTrade,
    Snapshot,
    Team,
    UnitEvent,
)
from ..supply import compute_drift
from .loader import ModeInfo, load_replay

# Everyone "leaves" when the game ends; leaves this close to the final loop are not leaves.
END_LEAVE_GRACE_S = 1.0
# Drift thresholds (design §4): below these a game_data_drift warning is raised.
MIN_CAP_AGREEMENT = 0.95
MIN_WORKER_AGREEMENT = 0.99

RACES = ("Terran", "Protoss", "Zerg")
_TRACKER_KINDS = {
    "UnitBornEvent": "born",
    "UnitInitEvent": "init",
    "UnitDoneEvent": "done",
    "UnitDiedEvent": "died",
    "UnitTypeChangeEvent": "type_change",
}


# --------------------------------------------------------------------------- pure helpers


def is_regular(loop: int) -> bool:
    """Regular stats snapshot: the first one (loop 1) and every 160 loops after."""
    return loop == 1 or loop % STATS_INTERVAL_LOOPS == 0


def composition(races: Iterable[str]) -> str:
    """Race initials sorted alphabetically, e.g. ["Zerg", "Protoss", "Terran"] -> "PTZ"."""
    return "".join(sorted(r[0] for r in races))


def team_result(result: Any) -> str:
    return result if result in ("Win", "Loss", "Tie") else "Unknown"


def iso_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def ruleset_id(starts: dict[int, tuple[str, int, float]]) -> str:
    """Signature of observed starting conditions: {pid: (race, workers, supply)} -> "w12-th15".

    Uses the most common starting worker count and the CC/Nexus supply of Terran/Protoss
    players ("zh<hatchery supply>" when every player is Zerg).
    """
    if not starts:
        return "unknown"
    workers = _most_common(w for _, w, _ in starts.values())
    tp = [s for race, _, s in starts.values() if race != "Zerg"]
    if tp:
        return f"w{_num(workers)}-th{_num(_most_common(tp))}"
    zh = _most_common(s - gamedata.SUPPLY_PROVIDED["Overlord"] for _, _, s in starts.values())
    return f"w{_num(workers)}-zh{_num(zh)}"


def _most_common(values: Iterable[float]) -> float:
    counts = Counter(values)
    # Ties go to the larger value so the result doesn't depend on player order.
    return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]


def assign_counterparts(players: list[Player], teams: list[Team]) -> list[Player]:
    """Nominal counterparts (design §5): i-th of one team pairs with i-th of the other.

    Players are ordered by lobby slot, falling back to player id when any slot is missing.
    """
    if len(teams) != 2 or len(teams[0].players) != len(teams[1].players):
        return players
    by_id = {p.id: p for p in players}
    members = [[by_id[pid] for pid in t.players if pid in by_id] for t in teams]
    if len(members[0]) != len(members[1]):
        return players
    use_slot = all(p.lobby_slot is not None for team in members for p in team)
    key = (lambda p: (p.lobby_slot, p.id)) if use_slot else (lambda p: p.id)
    source = "slot" if use_slot else "player_id"
    a, b = (sorted(team, key=key) for team in members)
    pairs: dict[int, int] = {}
    for x, y in zip(a, b, strict=True):
        pairs[x.id], pairs[y.id] = y.id, x.id
    return [
        p.model_copy(update={"counterpart_id": pairs[p.id], "counterpart_source": source})
        if p.id in pairs
        else p
        for p in players
    ]


def match_request(requests: list[dict], request_id: int, fulfiller: int, loop: int) -> dict | None:
    """Find the open ResourceRequestEvent a fulfill/cancel refers to.

    sc2reader doesn't number requests; the game assigns ids in order of creation. Without
    request samples (none in M0), accept a 1-based or 0-based index into the creation order,
    preferring 1-based, and require an open request created at or before `loop` by someone
    other than the fulfiller (pass fulfiller=-1 for cancels).
    """
    for idx in (request_id - 1, request_id):
        if 0 <= idx < len(requests):
            r = requests[idx]
            if r["open"] and r["loop"] <= loop and r["player"] != fulfiller:
                return r
    return None


# --------------------------------------------------------------------------- builder


def _pid(event: Any) -> int | None:
    return getattr(getattr(event, "player", None), "pid", None)


def _type_info(datapack: Any, name: str | None) -> Any:
    if datapack is None or name is None:
        return None
    return datapack.units.get(name)


def _is_structure(name: str, info: Any) -> bool:
    if name in gamedata.NON_STRUCTURE_TYPES:
        return False
    return name in gamedata.STRUCTURE_EXTRA_TYPES or bool(info and info.is_building)


def build_replay_model(path: str | Path) -> ReplayModel:
    """Load a replay and return its ReplayModel. Raises UnsupportedReplayError / ParseError."""
    path = Path(path)
    replay, mode = load_replay(path)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    return _build(replay, mode, sha)


def _build(replay: Any, mode: ModeInfo, sha: str) -> ReplayModel:
    warnings: list[AnalysisWarning] = []
    for msg in mode.warnings:
        code = "not_ladder" if "ladder game" in msg else "mode_not_targeted"
        warnings.append(AnalysisWarning(code=code, message=msg))

    end_loop = int(replay.frames)
    duration = loop_to_seconds(end_loop)
    build = int(replay.build)
    release = getattr(replay, "release_string", None)
    datapack = getattr(replay, "datapack", None)

    raw_players = {
        p.pid: p
        for p in replay.players
        if not getattr(p, "is_observer", False) and p.play_race in RACES
    }
    races = {pid: p.play_race for pid, p in raw_players.items()}
    team_of = {p.pid: p.team.number for p in raw_players.values()}

    teams = [
        Team(
            id=t.number,
            result=team_result(getattr(t, "result", None)),
            composition=composition(races[p.pid] for p in t.players if p.pid in races),
            players=sorted(p.pid for p in t.players if p.pid in races),
        )
        for t in sorted(replay.teams, key=lambda t: t.number)
        if any(p.pid in races for p in t.players)
    ]

    tracker = _walk_tracker(replay, races, datapack)
    game = _walk_game_events(replay, races, end_loop, tracker["depots"])
    warnings += game["warnings"]

    if tracker["unknown_types"]:
        names = sorted(tracker["unknown_types"])
        warnings.append(
            AnalysisWarning(
                code="unknown_unit_type",
                message=(
                    f"{len(names)} unit type(s) not in sc2reader data pack "
                    f"{getattr(datapack, 'id', None)}: {', '.join(names[:10])}"
                    + (" ..." if len(names) > 10 else "")
                    + "; treated as costing 0 and providing 0 supply."
                ),
            )
        )

    players: list[Player] = []
    for pid in sorted(raw_players):
        p = raw_players[pid]
        rating = (getattr(p, "init_data", None) or {}).get("scaled_rating")
        left = game["left_at"].get(pid)
        elim = tracker["eliminated_at"].get(pid)
        spawn = tracker["spawn"].get(pid)
        players.append(
            Player(
                id=pid,
                team=team_of[pid],
                name=str(p.name),
                race=races[pid],
                mmr=int(rating) if rating and rating > 0 else None,
                lobby_slot=getattr(p, "sid", None),
                toon_handle=getattr(p, "toon_handle", None) or None,
                spawn_point=Point(x=spawn[0], y=spawn[1]) if spawn else None,
                left_at=left,
                eliminated_at=elim,
                end_t=min(x for x in (left, elim, duration) if x is not None),
            )
        )
    players = assign_counterparts(players, teams)

    rules, rule_warnings = _rules(build, release, datapack, races, tracker["snapshots"])
    warnings += rule_warnings

    model = ReplayModel(
        game=GameInfo(
            map=str(replay.map_name),
            duration_s=duration,
            end_loop=end_loop,
            build=build,
            release=release,
            mode=mode.mode,
            is_ladder=bool(getattr(replay, "is_ladder", False)),
            played_at=iso_utc(getattr(replay, "date", None)),
            replay_sha256=sha,
        ),
        rules=rules,
        focus_player_id=None,
        teams=teams,
        players=players,
        snapshots=tracker["snapshots"],
        unit_events=tracker["unit_events"],
        resource_trades=game["resource_trades"],
        land_commands=game["land_commands"],
        extra_supplies=game["extra_supplies"],
        warnings=warnings,
    )
    model.rules.drift = compute_drift(model)
    drift_warning = _drift_warning(build, model.rules.drift, set(races.values()))
    if drift_warning:
        model.warnings.append(drift_warning)
    return model


def _walk_tracker(replay: Any, races: dict[int, str], datapack: Any) -> dict:
    snapshots: list[Snapshot] = []
    unit_events: list[UnitEvent] = []
    types: dict[int, str] = {}
    owners: dict[int, int] = {}
    structures: dict[int, set[int]] = {pid: set() for pid in races}
    eliminated: dict[int, float | None] = {}
    spawn: dict[int, tuple[float, float]] = {}
    unknown: set[str] = set()

    def set_structure(pid: int | None, uid: int, name: str, info: Any, t: float) -> None:
        if pid not in structures:
            return
        if _is_structure(name, info):
            structures[pid].add(uid)
            eliminated[pid] = None
        elif uid in structures[pid]:
            structures[pid].discard(uid)
            if not structures[pid]:
                eliminated[pid] = t

    for e in sorted(replay.tracker_events, key=lambda ev: ev.frame):
        name = type(e).__name__
        loop = int(e.frame)
        t = loop_to_seconds(loop)
        if name == "PlayerStatsEvent":
            if e.pid in races:
                snapshots.append(_snapshot(e, loop, t))
            continue
        if name == "UnitOwnerChangeEvent":
            uid, new = e.unit_id, getattr(e, "control_pid", None)
            old = owners.get(uid)
            if old in structures and uid in structures[old]:
                structures[old].discard(uid)
                if not structures[old]:
                    eliminated[old] = t
            owners[uid] = new
            if uid in types:
                set_structure(new, uid, types[uid], _type_info(datapack, types[uid]), t)
            continue
        kind = _TRACKER_KINDS.get(name)
        if kind is None:
            continue
        uid = e.unit_id
        if kind in ("born", "init"):
            types[uid] = e.unit_type_name
            owners[uid] = e.control_pid
        elif kind == "type_change":
            types[uid] = e.unit_type_name
        owner = owners.get(uid)
        utype = types.get(uid)
        if owner not in races or utype is None:
            continue
        info = _type_info(datapack, utype)
        if info is None:
            unknown.add(utype)

        x = y = None
        killer = None
        if kind in ("born", "init", "died"):
            x, y = e.x, e.y
        if kind == "died":
            k = getattr(e, "killer_pid", None)
            if k is None:
                k = getattr(e, "killing_player_id", None)
            killer = k if k in races else None
            if owner in structures and uid in structures[owner]:
                structures[owner].discard(uid)
                if not structures[owner]:
                    eliminated[owner] = t
        elif kind in ("born", "init", "type_change"):
            set_structure(owner, uid, utype, info, t)
        if (
            kind == "born"
            and loop == 0
            and utype in gamedata.TOWN_HALL_BUILD_TYPES
            and owner not in spawn
        ):
            spawn[owner] = (float(x), float(y))

        unit = getattr(e, "unit", None)
        unit_events.append(
            UnitEvent(
                t=t,
                loop=loop,
                player=owner,
                kind=kind,
                unit_id=uid,
                unit_type=utype,
                x=None if x is None else float(x),
                y=None if y is None else float(y),
                killer=killer,
                minerals=int(getattr(info, "minerals", 0) or 0),
                vespene=int(getattr(info, "vespene", 0) or 0),
                supply=float(getattr(info, "supply", 0) or 0),
                is_army=bool(getattr(info, "is_army", False)),
                is_building=bool(getattr(info, "is_building", False)),
                is_worker=utype in gamedata.WORKER_TYPES
                or (
                    bool(getattr(info, "is_worker", False))
                    and utype not in gamedata.NON_WORKER_TYPES
                ),
                hallucinated=bool(getattr(unit, "hallucinated", False)),
            )
        )

    snapshots.sort(key=lambda s: (s.loop, s.player))
    return {
        "snapshots": snapshots,
        "unit_events": unit_events,
        "eliminated_at": {pid: v for pid, v in eliminated.items() if v is not None},
        "spawn": spawn,
        "unknown_types": unknown,
        "depots": {uid for uid, n in types.items() if n in gamedata.EXTRA_SUPPLIES_TARGETS},
    }


def _snapshot(e: Any, loop: int, t: float) -> Snapshot:
    return Snapshot(
        t=t,
        loop=loop,
        regular=is_regular(loop),
        player=e.pid,
        minerals=int(e.minerals_current),
        gas=int(e.vespene_current),
        income_per_min=float(e.minerals_collection_rate + e.vespene_collection_rate),
        supply_used=float(e.food_used),
        supply_made=float(e.food_made),
        workers=int(e.workers_active_count),
        army_value=int(e.minerals_used_current_army + e.vespene_used_current_army),
        army_lost=int(e.minerals_lost_army + e.vespene_lost_army),
        army_killed=int(e.minerals_killed_army + e.vespene_killed_army),
    )


def _walk_game_events(replay: Any, races: dict[int, str], end_loop: int, depots: set[int]) -> dict:
    left_at: dict[int, float] = {}
    trades: list[ResourceTrade] = []
    lands: list[LandCommand] = []
    casts: list[ExtraSuppliesCast] = []
    requests: list[dict] = []
    warnings: list[AnalysisWarning] = []
    grace = END_LEAVE_GRACE_S * 22.4
    unmatched = 0

    for e in sorted(replay.game_events, key=lambda ev: ev.frame):
        name = type(e).__name__
        loop = int(e.frame)
        t = loop_to_seconds(loop)
        pid = _pid(e)
        if name == "PlayerLeaveEvent":
            if pid in races and pid not in left_at and end_loop - loop > grace:
                left_at[pid] = t
        elif name == "TargetPointCommandEvent":
            if pid in races and getattr(e, "ability_name", None) in gamedata.LAND_ABILITIES:
                loc = e.location
                lands.append(LandCommand(t=t, player=pid, x=float(loc[0]), y=float(loc[1])))
        elif name in ("TargetUnitCommandEvent", "UpdateTargetUnitCommandEvent"):
            # Update events inherit the previous ability, so they can be stale: keep only casts
            # on supply depots, the only valid target.
            if (
                pid in races
                and getattr(e, "ability_name", None) == gamedata.EXTRA_SUPPLIES_ABILITY
                and e.target_unit_id in depots
            ):
                casts.append(
                    ExtraSuppliesCast(t=t, player=pid, target_unit_id=int(e.target_unit_id))
                )
        elif name == "ResourceTradeEvent":
            to = getattr(getattr(e, "recipient", None), "pid", None)
            if pid in races and to in races:
                trades.append(
                    ResourceTrade(
                        t=t,
                        from_player=pid,
                        to=to,
                        minerals=int(e.minerals or 0),
                        gas=int(e.vespene or 0),
                        kind="trade",
                    )
                )
        elif name == "ResourceRequestEvent":
            requests.append(
                {
                    "loop": loop,
                    "player": pid,
                    "minerals": int(e.minerals or 0),
                    "gas": int(e.vespene or 0),
                    "open": True,
                }
            )
        elif name == "ResourceRequestCancelEvent":
            req = match_request(requests, int(e.request_id), -1, loop)
            if req is not None and req["player"] == pid:
                req["open"] = False
        elif name == "ResourceRequestFulfillEvent":
            req = match_request(requests, int(e.request_id), pid, loop)
            if req is None or pid not in races or req["player"] not in races:
                unmatched += 1
                continue
            req["open"] = False
            trades.append(
                ResourceTrade(
                    t=t,
                    from_player=pid,
                    to=req["player"],
                    minerals=req["minerals"],
                    gas=req["gas"],
                    kind="request",
                )
            )
    if unmatched:
        warnings.append(
            AnalysisWarning(
                code="unresolved_resource_request",
                message=f"{unmatched} fulfilled resource request(s) could not be matched; "
                "those transfers are missing from resource_trades.",
            )
        )
    return {
        "left_at": left_at,
        "resource_trades": trades,
        "land_commands": lands,
        "extra_supplies": casts,
        "warnings": warnings,
    }


def _rules(
    build: int,
    release: str | None,
    datapack: Any,
    races: dict[int, str],
    snapshots: list[Snapshot],
) -> tuple[GameRules, list[AnalysisWarning]]:
    first: dict[int, Snapshot] = {}
    for s in snapshots:
        first.setdefault(s.player, s)
    players = {
        pid: PlayerRules(
            starting_workers=s.workers,
            starting_supply=s.supply_made,
            supply_table=gamedata.supply_table(races[pid], s.supply_made),
        )
        for pid, s in sorted(first.items())
    }
    starts = {
        pid: (races[pid], r.starting_workers, r.starting_supply) for pid, r in players.items()
    }
    for pid in sorted(set(races) - set(players)):
        # No stats snapshot for this player: assume the replay's observed (or standard) start.
        players[pid] = _fallback_rules(races[pid], starts)
    players = dict(sorted(players.items()))
    pack_id = getattr(datapack, "id", None)
    verified = build <= gamedata.KNOWN_MAX_BUILD
    warnings: list[AnalysisWarning] = []
    if not verified:
        msg = (
            f"Build {build} is newer than the newest verified build "
            f"({gamedata.KNOWN_MAX_BUILD}); using the latest known rules."
        )
        if build > gamedata.SC2READER_MAX_DATAPACK:
            msg += (
                f" sc2reader has no data pack for it (newest {gamedata.SC2READER_MAX_DATAPACK}"
                f", used {pack_id}); unit data (costs, supply, names) may be stale."
            )
        warnings.append(AnalysisWarning(code="unverified_build", message=msg))
    rules = GameRules(
        build=build,
        release=release,
        ruleset_id=ruleset_id(starts),
        sc2reader_datapack=None if pack_id is None else str(pack_id),
        verified_build=verified,
        overrides=gamedata.resolve_overrides(build),
        players=players,
    )
    return rules, warnings


def _fallback_rules(race: str, starts: dict[int, tuple[str, int, float]]) -> PlayerRules:
    overlord = gamedata.SUPPLY_PROVIDED["Overlord"]
    workers = int(_most_common(w for _, w, _ in starts.values())) if starts else 12
    halls = [s for r, _, s in starts.values() if r != "Zerg"]
    zhalls = [s - overlord for r, _, s in starts.values() if r == "Zerg"]
    if race == "Zerg":
        supply = (
            _most_common(zhalls) if zhalls else gamedata.SUPPLY_PROVIDED["Hatchery"]
        ) + overlord
    else:
        supply = _most_common(halls) if halls else gamedata.SUPPLY_PROVIDED["CommandCenter"]
    return PlayerRules(
        starting_workers=workers,
        starting_supply=supply,
        supply_table=gamedata.supply_table(race, supply),
    )


def _drift_warning(
    build: int, drift: dict[str, float | None], races_present: set[str]
) -> AnalysisWarning | None:
    problems = []
    for race in RACES:
        v = drift.get(f"cap_agreement_{race}")
        if race in races_present and v is not None and v < MIN_CAP_AGREEMENT:
            problems.append(f"{race} supply cap agreement {v:.1%}")
    w = drift.get("worker_agreement")
    if w is not None and w < MIN_WORKER_AGREEMENT:
        problems.append(f"worker agreement {w:.1%}")
    if not problems:
        return None
    return AnalysisWarning(
        code="game_data_drift",
        message=f"Build {build}: event data disagrees with the game's snapshots ("
        + ", ".join(problems)
        + "); affected metrics fall back to snapshots.",
    )
