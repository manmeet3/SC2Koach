"""Helpers shared by the metric modules."""

from __future__ import annotations

from ..models import ReplayModel, Snapshot

Step = tuple[float, float]  # (t, value) — value holds from t until the next step


def player_snapshots(replay: ReplayModel, pid: int, *, clip: bool = True) -> list[Snapshot]:
    """The player's snapshots in replay order; with `clip`, only those with t <= end_t."""
    end_t = replay.player(pid).end_t
    return [s for s in replay.snapshots if s.player == pid and (not clip or s.t <= end_t)]


def push_step(steps: list[Step], t: float, value: float) -> None:
    """Append a step, collapsing steps at the same t and dropping unchanged values."""
    if steps and steps[-1][0] == t:
        steps[-1] = (t, value)
        if len(steps) > 1 and steps[-2][1] == value:
            steps.pop()
    elif not steps or steps[-1][1] != value:
        steps.append((t, value))
