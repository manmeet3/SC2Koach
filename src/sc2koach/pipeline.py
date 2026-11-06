"""End-to-end analysis: replay → ReplayModel → metrics → findings → AnalysisResult."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from . import __version__
from .config import Config, effective_thresholds_dict
from .gametime import fmt_mmss
from .identity import apply_pairs, resolve_focus
from .metrics import compute_all, unresolved_landings
from .models import AnalysisResult, AnalysisWarning, GeneratedWith, ReplayModel
from .moments import detect_all
from .parser import build_replay_model


def _sc2reader_version() -> str | None:
    try:
        return version("sc2reader")
    except PackageNotFoundError:
        return None


def prepare_replay(
    replay: ReplayModel, config: Config, pairs: list[str] | None = None
) -> ReplayModel:
    """Apply perspective settings (focus player, manual pairs) to a parsed replay."""
    warnings = list(replay.warnings)
    players = replay.players
    if pairs:
        players, pair_warnings = apply_pairs(players, replay.teams, pairs)
        warnings += pair_warnings
    focus_id, focus_warnings = resolve_focus(players, config.focus)
    warnings += focus_warnings
    for pid, t in unresolved_landings(replay):
        warnings.append(
            AnalysisWarning(
                code="unresolved_landing",
                message=f"Town hall landing at {fmt_mmss(t)} has no Land command; "
                "not counted as an expansion",
                player=pid,
            )
        )
    return replay.model_copy(
        update={"players": players, "focus_player_id": focus_id, "warnings": warnings}
    )


def analyze_model(replay: ReplayModel, config: Config) -> AnalysisResult:
    th = config.thresholds.for_ruleset(replay.rules.ruleset_id)
    metrics, team_metrics = compute_all(replay, th)
    findings = detect_all(replay, metrics, team_metrics, th)
    return AnalysisResult(
        tool_version=__version__,
        generated_with=GeneratedWith(
            sc2reader=_sc2reader_version(), thresholds=effective_thresholds_dict(th)
        ),
        replay=replay.header(),
        metrics=metrics,
        team_metrics=team_metrics,
        findings=findings,
        warnings=replay.warnings,
    )


def analyze(path: str | Path, config: Config, pairs: list[str] | None = None) -> AnalysisResult:
    replay = prepare_replay(build_replay_model(path), config, pairs)
    return analyze_model(replay, config)
