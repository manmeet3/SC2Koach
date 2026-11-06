"""Key-moment detection: rules -> findings with est_cost, severity and IDs (design §7)."""

from __future__ import annotations

from sc2koach.models import Finding, MetricsBundle, ReplayModel, TeamMetrics
from sc2koach.moments.ranking import finalize, rank_for_player, rank_team
from sc2koach.moments.rules import RULES
from sc2koach.thresholds import Thresholds

__all__ = ["detect_all", "rank_for_player", "rank_team"]


def detect_all(
    replay: ReplayModel,
    metrics: list[MetricsBundle],
    team_metrics: list[TeamMetrics],
    th: Thresholds,
) -> list[Finding]:
    """All findings, in deterministic ID order. `th` must already be resolved for the ruleset."""
    end_t = {p.id: p.end_t for p in replay.players}
    findings: list[Finding] = []
    for rule in RULES:
        for f in rule(replay, metrics, team_metrics, th):
            # No player finding may start after that player left the game.
            if f.scope == "player" and f.player is not None and f.start > end_t[f.player]:
                continue
            findings.append(f)
    return finalize(findings)
