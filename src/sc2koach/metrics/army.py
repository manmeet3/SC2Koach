"""Army value series and event-based army value (design/DESIGN.md §6)."""

from __future__ import annotations

from ..models import ReplayModel, Series
from .common import Step, player_snapshots, push_step


def army_value_series(replay: ReplayModel, pid: int) -> Series:
    return [(s.t, float(s.army_value)) for s in player_snapshots(replay, pid)]


def army_lost_series(replay: ReplayModel, pid: int) -> Series:
    return [(s.t, float(s.army_lost)) for s in player_snapshots(replay, pid)]


def army_killed_series(replay: ReplayModel, pid: int) -> Series:
    return [(s.t, float(s.army_killed)) for s in player_snapshots(replay, pid)]


def event_army(replay: ReplayModel, pid: int) -> list[Step]:
    """Summed minerals + vespene of pid's finished, living, non-hallucinated army units.

    Units count from `born`, or from `done` after `init`. A type change re-prices a counted
    unit with the new type's cost (or drops it if the new type isn't army).
    """
    pending: set[int] = set()
    alive: dict[int, int] = {}
    total = 0
    steps: list[Step] = []
    for e in replay.unit_events:
        cost = e.minerals + e.vespene
        counts = e.is_army and not e.hallucinated
        if e.kind == "died":
            pending.discard(e.unit_id)
            if e.unit_id not in alive:
                continue
            total -= alive.pop(e.unit_id)
        elif e.player != pid:
            continue
        elif e.kind == "init":
            if counts:
                pending.add(e.unit_id)
            continue
        elif e.kind in ("born", "done"):
            if not counts or e.unit_id in alive or (e.kind == "done" and e.unit_id not in pending):
                continue
            pending.discard(e.unit_id)
            alive[e.unit_id] = cost
            total += cost
        elif e.kind == "type_change" and e.unit_id in alive:
            total -= alive.pop(e.unit_id)
            if counts:
                alive[e.unit_id] = cost
                total += cost
        else:
            continue
        push_step(steps, e.t, total)
    return steps
