"""Expansion timings (design/DESIGN.md §6 "Expansion detection")."""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass
from typing import Literal

from ..gamedata import FLYING_TOWN_HALLS, TOWN_HALL_BUILD_TYPES, TOWN_HALL_TYPES
from ..models import Expansion, LandCommand, ReplayModel
from ..thresholds import Thresholds


@dataclass(frozen=True)
class _Candidate:
    t: float
    started: float | None
    x: float
    y: float
    source: Literal["built", "landed"]


def _land_commands(replay: ReplayModel, pid: int) -> list[LandCommand]:
    return sorted((c for c in replay.land_commands if c.player == pid), key=lambda c: c.t)


def _resolve_landing(cmds: list[LandCommand], t: float) -> LandCommand | None:
    """Latest Land command at or before t."""
    i = bisect_right([c.t for c in cmds], t)
    return cmds[i - 1] if i else None


def _is_landing(prev_type: str | None, new_type: str) -> bool:
    return prev_type in FLYING_TOWN_HALLS and new_type in FLYING_TOWN_HALLS.values()


def unresolved_landings(replay: ReplayModel) -> list[tuple[int, float]]:
    """(player, t) of town hall landings with no preceding Land command (not counted)."""
    cmds = {p.id: _land_commands(replay, p.id) for p in replay.players}
    types: dict[int, str] = {}
    out: list[tuple[int, float]] = []
    for e in replay.unit_events:
        prev = types.get(e.unit_id)
        types[e.unit_id] = e.unit_type
        if e.kind == "type_change" and _is_landing(prev, e.unit_type):
            if _resolve_landing(cmds.get(e.player, []), e.t) is None:
                out.append((e.player, e.t))
    return out


def _start_base(replay: ReplayModel, pid: int) -> tuple[float, float] | None:
    for e in replay.unit_events:
        if e.loop > 0:
            break
        if (
            e.kind == "born"
            and e.player == pid
            and e.unit_type in TOWN_HALL_TYPES
            and e.x is not None
            and e.y is not None
        ):
            return e.x, e.y
    sp = replay.player(pid).spawn_point
    return (sp.x, sp.y) if sp else None


def _candidates(replay: ReplayModel, pid: int) -> list[_Candidate]:
    """Finished town halls (at their Init position) and resolved landings, in time order."""
    cmds = _land_commands(replay, pid)
    inits: dict[int, tuple[float, float | None, float | None]] = {}
    types: dict[int, str] = {}
    out: list[_Candidate] = []
    for e in replay.unit_events:
        prev = types.get(e.unit_id)
        types[e.unit_id] = e.unit_type
        if e.player != pid:
            continue
        if e.kind == "init":
            inits[e.unit_id] = (e.t, e.x, e.y)
        elif e.kind == "done" and e.unit_type in TOWN_HALL_BUILD_TYPES:
            init = inits.get(e.unit_id)
            if init and init[1] is not None and init[2] is not None:
                out.append(_Candidate(e.t, init[0], init[1], init[2], "built"))
        elif e.kind == "type_change" and _is_landing(prev, e.unit_type):
            cmd = _resolve_landing(cmds, e.t)
            if cmd is not None:
                init = inits.get(e.unit_id)
                out.append(_Candidate(e.t, init[0] if init else None, cmd.x, cmd.y, "landed"))
    return out


def expansions(replay: ReplayModel, pid: int, th: Thresholds) -> list[Expansion]:
    """Distinct base locations in [0, end_t]. A finished town hall or landing counts only if
    it is farther than expansion_min_distance from every place the player ever had one."""
    end_t = replay.player(pid).end_t
    out: list[Expansion] = []
    known: list[tuple[float, float]] = []
    start = _start_base(replay, pid)
    if start is not None:
        known.append(start)
        out.append(
            Expansion(n=1, started=None, finished=0.0, x=start[0], y=start[1], source="start")
        )
    for c in _candidates(replay, pid):
        if c.t > end_t:
            break
        if all(math.hypot(c.x - x, c.y - y) > th.expansion_min_distance for x, y in known):
            out.append(
                Expansion(
                    n=len(out) + 1,
                    started=c.started,
                    finished=c.t,
                    x=c.x,
                    y=c.y,
                    source=c.source,
                )
            )
        known.append((c.x, c.y))
    return out
