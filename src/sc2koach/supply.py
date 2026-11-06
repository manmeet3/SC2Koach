"""Supply cap rebuilt from unit events, and per-replay drift checks (design/DESIGN.md §4, §6).

Pure functions over ReplayModel; shared by the parser (drift) and metrics (supply blocks).
"""

from __future__ import annotations

from bisect import bisect_right

from .gamedata import SUPPLY_CAP
from .models import ReplayModel

Step = tuple[float, float]  # (t, value) — value holds from t until the next step


def rebuild_cap(replay: ReplayModel, pid: int) -> list[Step]:
    """Event-rebuilt supply cap for one player as a step series, capped at SUPPLY_CAP.

    Providers add `rules.players[pid].supply_table[type]` when born finished or done, and
    remove it when they die. Type changes keep the value. Extra Supplies casts add
    `rules.overrides["extra_supplies"]` to a living provider owned by the caster.
    Events at loop L are applied before a snapshot at loop L is compared (see value_at).
    """
    table = replay.rules.players[pid].supply_table
    extra = replay.rules.overrides.get("extra_supplies", 0)
    provided: dict[int, float] = {}
    raw = 0.0
    steps: list[Step] = []
    casts = sorted((c for c in replay.extra_supplies if c.player == pid), key=lambda c: c.t)
    ci = 0

    def push(t: float) -> None:
        val = min(SUPPLY_CAP, raw)
        if steps and steps[-1][0] == t:
            steps[-1] = (t, val)
        elif not steps or steps[-1][1] != val:
            steps.append((t, val))

    for e in replay.unit_events:
        while ci < len(casts) and casts[ci].t <= e.t:
            c = casts[ci]
            if c.target_unit_id in provided and extra:
                provided[c.target_unit_id] += extra
                raw += extra
                push(c.t)
            ci += 1
        if e.player != pid and e.unit_id not in provided:
            continue
        if e.kind in ("born", "done") and e.unit_id not in provided:
            value = table.get(e.unit_type)
            if value and e.player == pid:
                provided[e.unit_id] = value
                raw += value
                push(e.t)
        elif e.kind == "died" and e.unit_id in provided:
            raw -= provided.pop(e.unit_id)
            push(e.t)
    while ci < len(casts):
        c = casts[ci]
        if c.target_unit_id in provided and extra:
            provided[c.target_unit_id] += extra
            raw += extra
            push(c.t)
        ci += 1
    return steps


def value_at(steps: list[Step], t: float, default: float = 0.0) -> float:
    """Value of a step series at time t (steps at exactly t are included)."""
    i = bisect_right(steps, (t, float("inf")))
    return steps[i - 1][1] if i else default


def event_workers(replay: ReplayModel, pid: int) -> list[Step]:
    """Living worker units owned by pid, from unit events (overcounts Zerg; see §6)."""
    alive: set[int] = set()
    steps: list[Step] = []
    for e in replay.unit_events:
        if e.player != pid or not e.is_worker:
            continue
        if e.kind in ("born", "init", "done"):
            alive.add(e.unit_id)
        elif e.kind == "died":
            alive.discard(e.unit_id)
        else:
            continue
        if steps and steps[-1][0] == e.t:
            steps[-1] = (e.t, len(alive))
        else:
            steps.append((e.t, len(alive)))
    return steps


def compute_drift(replay: ReplayModel) -> dict[str, float | None]:
    """Agreement of event-derived values with the game's own snapshots.

    Keys: cap_agreement, cap_agreement_<Race>, worker_agreement (Terran/Protoss only,
    snapshots up to 8:00). None when there is nothing to compare.
    """
    race = {p.id: p.race for p in replay.players}
    caps = {pid: rebuild_cap(replay, pid) for pid in race}
    workers = {pid: event_workers(replay, pid) for pid in race if race[pid] != "Zerg"}
    cap_hits: dict[str, list[bool]] = {}
    worker_hits: list[bool] = []
    for s in replay.snapshots:
        if not s.regular or s.player not in race:
            continue
        p = replay.player(s.player)
        if s.t > p.end_t:
            continue
        cap = value_at(caps[s.player], s.t)
        ok = abs(min(SUPPLY_CAP, s.supply_made) - cap) < 0.01
        cap_hits.setdefault(race[s.player], []).append(ok)
        if s.player in workers and s.t <= 480:
            worker_hits.append(value_at(workers[s.player], s.t) == s.workers)

    def frac(xs: list[bool]) -> float | None:
        return round(sum(xs) / len(xs), 4) if xs else None

    out: dict[str, float | None] = {
        "cap_agreement": frac([x for v in cap_hits.values() for x in v])
    }
    for r in ("Terran", "Protoss", "Zerg"):
        out[f"cap_agreement_{r}"] = frac(cap_hits.get(r, []))
    out["worker_agreement"] = frac(worker_hits)
    return out
