"""Supply blocks (design/DESIGN.md §6 "Supply blocks")."""

from __future__ import annotations

from bisect import bisect_right

from ..gamedata import SUPPLY_CAP, TOWN_HALL_TYPES
from ..models import ReplayModel, Snapshot, SupplyBlock
from ..supply import rebuild_cap, value_at
from ..thresholds import Thresholds
from .common import Step, player_snapshots, push_step

WORKER_COST = 50


def town_hall_steps(replay: ReplayModel, pid: int) -> list[Step]:
    """Number of finished, living town halls owned by pid over time."""
    alive: set[int] = set()
    steps: list[Step] = []
    for e in replay.unit_events:
        if e.kind in ("born", "done") and e.player == pid and e.unit_type in TOWN_HALL_TYPES:
            alive.add(e.unit_id)
        elif e.kind == "died" and e.unit_id in alive:
            alive.discard(e.unit_id)
        else:
            continue
        push_step(steps, e.t, len(alive))
    return steps


def cap_events_trusted(replay: ReplayModel, pid: int, th: Thresholds) -> bool:
    """False when the drift detector says the event-rebuilt cap is unreliable for this race."""
    agreement = replay.rules.drift.get(f"cap_agreement_{replay.player(pid).race}")
    return agreement is None or agreement >= th.drift_min_cap_agreement


def is_blocked(s: Snapshot, halls: list[Step]) -> bool:
    return (
        s.supply_made < SUPPLY_CAP
        and s.supply_made - s.supply_used < 1
        and value_at(halls, s.t) > 0
        and s.minerals >= WORKER_COST
    )


def _event_end(cap: list[Step], snaps: list[Snapshot], k: int, j: int, until: float):
    """First cap step in (snaps[k].t, until) where the cap, reset to the latest snapshot's
    supply_made, leaves room for a worker. Returns (t, index of that latest snapshot)."""
    i = bisect_right(cap, (snaps[k].t, float("inf")))
    m = k
    while i < len(cap) and cap[i][0] < until:
        t = cap[i][0]
        while m < j and snaps[m + 1].t <= t:
            m += 1
        s = snaps[m]
        est = min(SUPPLY_CAP, s.supply_made + value_at(cap, t) - value_at(cap, s.t))
        if est - s.supply_used >= 1:
            return t, m
        i += 1
    return None


def supply_blocks(replay: ReplayModel, pid: int, th: Thresholds) -> list[SupplyBlock]:
    """Merged runs of blocked snapshots in [0, end_t], ended by the event-rebuilt cap or the
    next unblocked snapshot, whichever is first. Blocks under supply_block_min_s are dropped."""
    end_t = replay.player(pid).end_t
    snaps = player_snapshots(replay, pid)
    halls = town_hall_steps(replay, pid)
    cap = rebuild_cap(replay, pid) if cap_events_trusted(replay, pid, th) else []
    blocked = [is_blocked(s, halls) for s in snaps]
    out: list[SupplyBlock] = []
    i = 0
    while i < len(snaps):
        if not blocked[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(snaps) and blocked[j + 1]:
            j += 1
        until = snaps[j + 1].t if j + 1 < len(snaps) else end_t
        k = i
        while k <= j:
            start = snaps[k]
            end, nxt = until, j + 1
            hit = _event_end(cap, snaps, k, j, until) if cap else None
            if hit is not None:
                end, nxt = hit[0], hit[1] + 1
            if end - start.t >= th.supply_block_min_s:
                out.append(
                    SupplyBlock(
                        start=start.t,
                        end=end,
                        duration_s=end - start.t,
                        supply=start.supply_made,
                        minerals=start.minerals,
                    )
                )
            k = nxt
        i = j + 1
    return out
