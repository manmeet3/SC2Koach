"""Per-player and team metrics (design/DESIGN.md §6).

Pure, deterministic functions over a ReplayModel. Callers pass thresholds already resolved
for the replay's ruleset (`Thresholds.for_ruleset`).
"""

from __future__ import annotations

from ..models import MetricsBundle, ReplayModel, TeamMetrics
from ..thresholds import Thresholds
from .army import army_killed_series, army_lost_series, army_value_series, event_army
from .common import player_snapshots
from .economy import (
    bank_adjusted,
    income_series,
    seconds_above_threshold,
    spending_quotient,
    unspent,
    workers_at_4m,
    workers_series,
)
from .expansions import expansions, unresolved_landings
from .supply_blocks import supply_blocks, town_hall_steps
from .team import eliminations, player_army_at_regular, team_army_series, team_metrics

__all__ = [
    "army_killed_series",
    "army_lost_series",
    "army_value_series",
    "bank_adjusted",
    "compute_all",
    "compute_player",
    "eliminations",
    "event_army",
    "expansions",
    "income_series",
    "player_army_at_regular",
    "player_snapshots",
    "seconds_above_threshold",
    "spending_quotient",
    "supply_blocks",
    "team_army_series",
    "team_metrics",
    "town_hall_steps",
    "unresolved_landings",
    "unspent",
    "workers_at_4m",
    "workers_series",
]


def compute_player(replay: ReplayModel, pid: int, th: Thresholds) -> MetricsBundle:
    return MetricsBundle(
        player=pid,
        starting_workers=replay.rules.players[pid].starting_workers,
        workers_at_4m=workers_at_4m(replay, pid),
        workers=workers_series(replay, pid),
        unspent=unspent(replay, pid, th),
        income=income_series(replay, pid),
        supply_blocks=supply_blocks(replay, pid, th),
        expansions=expansions(replay, pid, th),
        army_value=army_value_series(replay, pid),
        army_lost=army_lost_series(replay, pid),
        army_killed=army_killed_series(replay, pid),
    )


def compute_all(
    replay: ReplayModel, th: Thresholds
) -> tuple[list[MetricsBundle], list[TeamMetrics]]:
    """All player bundles (by player id) and team metrics (by team id)."""
    bundles = [compute_player(replay, p.id, th) for p in sorted(replay.players, key=lambda p: p.id)]
    return bundles, team_metrics(replay, th)
