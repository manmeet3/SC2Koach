"""Team army value, disparity and eliminations (design/DESIGN.md §6)."""

from __future__ import annotations

from bisect import bisect_left

from ..models import Elimination, ReplayModel, Series, TeamMetrics
from ..supply import value_at
from ..thresholds import Thresholds
from .army import event_army
from .common import player_snapshots


def regular_times(replay: ReplayModel) -> list[tuple[int, float]]:
    """(loop, t) of every regular snapshot loop in the replay, sorted."""
    return sorted({s.loop: s.t for s in replay.snapshots if s.regular}.items())


def player_army_at_regular(replay: ReplayModel, pid: int) -> Series:
    """pid's army value at every regular snapshot time, estimated after their snapshots stop:
    last_snapshot_army × event_army(t) / event_army(t_last) (0 if event_army(t_last) is 0)."""
    snaps = player_snapshots(replay, pid, clip=False)
    by_loop = {s.loop: s for s in snaps}
    loops = [s.loop for s in snaps]
    events = None
    out: Series = []
    for loop, t in regular_times(replay):
        s = by_loop.get(loop)
        if s is not None:
            out.append((t, float(s.army_value)))
            continue
        i = bisect_left(loops, loop)
        if i == 0:
            out.append((t, 0.0))
            continue
        last = snaps[i - 1]
        if events is None:
            events = event_army(replay, pid)
        base = value_at(events, last.t)
        est = last.army_value * value_at(events, t) / base if base else 0.0
        out.append((t, float(est)))
    return out


def team_army_series(replay: ReplayModel, team_id: int) -> Series:
    team = next(tm for tm in replay.teams if tm.id == team_id)
    per_player = [player_army_at_regular(replay, pid) for pid in team.players]
    times = [t for _, t in regular_times(replay)]
    return [(t, sum(series[i][1] for series in per_player)) for i, t in enumerate(times)]


def eliminations(replay: ReplayModel, team_id: int, th: Thresholds) -> list[Elimination]:
    team = next(tm for tm in replay.teams if tm.id == team_id)
    game_end = replay.game.duration_s
    out: list[Elimination] = []
    for pid in team.players:
        p = replay.player(pid)
        times = [x for x in (p.left_at, p.eliminated_at) if x is not None]
        if not times:
            continue
        departed = min(times)
        others = [replay.player(o).end_t for o in team.players if o != pid]
        played_on = max(0.0, min(game_end, max(others)) - departed) if others else 0.0
        out.append(
            Elimination(
                player=pid,
                eliminated_at=p.eliminated_at,
                left_at=p.left_at,
                departed_at=departed,
                team_played_on_s=played_on,
                early=played_on >= th.early_ally_death_s,
            )
        )
    out.sort(key=lambda e: (e.departed_at, e.player))
    return out


def team_metrics(replay: ReplayModel, th: Thresholds) -> list[TeamMetrics]:
    """Per-team army value, disparity versus all other teams combined, and eliminations."""
    teams = sorted(replay.teams, key=lambda tm: tm.id)
    army = {tm.id: team_army_series(replay, tm.id) for tm in teams}
    out: list[TeamMetrics] = []
    for tm in teams:
        own = army[tm.id]
        disparity: Series = []
        for i, (t, value) in enumerate(own):
            enemy = sum(army[o.id][i][1] for o in teams if o.id != tm.id)
            disparity.append((t, value - enemy))
        out.append(
            TeamMetrics(
                team=tm.id,
                army_value=own,
                army_disparity=disparity,
                eliminations=eliminations(replay, tm.id, th),
            )
        )
    return out
