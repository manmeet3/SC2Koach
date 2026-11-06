"""Load a replay with sc2reader and check it is a supported team game."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import sc2reader

from ..errors import ParseError, UnsupportedReplayError
from ..gametime import loop_to_seconds

SUPPORTED_SIZES = {2, 3}
WARN_SIZES = {4}
MIN_GAME_SECONDS = 60


@dataclass(frozen=True)
class ModeInfo:
    mode: str
    team_size: int
    warnings: list[str] = field(default_factory=list)


def classify_mode(replay: Any) -> ModeInfo:
    """Return the team mode, or raise UnsupportedReplayError (design/DESIGN.md §5)."""
    if getattr(replay, "computers", None):
        raise UnsupportedReplayError("Replays with AI players are not supported.")
    players = [p for p in replay.players if not getattr(p, "is_observer", False)]
    if any(getattr(p, "archon_leader_id", None) is not None for p in players):
        raise UnsupportedReplayError("Archon mode is not supported.")

    teams = [t for t in replay.teams if t.players]
    if len(teams) != 2:
        raise UnsupportedReplayError(
            f"Expected 2 teams, found {len(teams)} (FFA and custom layouts are not supported)."
        )
    sizes = sorted(len(t.players) for t in teams)
    if sizes[0] != sizes[1]:
        raise UnsupportedReplayError(f"Uneven teams ({sizes[0]}v{sizes[1]}) are not supported.")
    size = sizes[0]
    if size == 1:
        raise UnsupportedReplayError("1v1 replays are out of scope; sc2Koach targets 2v2/3v3.")
    frames = getattr(replay, "frames", None)
    if frames is not None and loop_to_seconds(frames) < MIN_GAME_SECONDS:
        raise UnsupportedReplayError(
            f"Game lasted under {MIN_GAME_SECONDS}s (remake or instant leave); nothing to analyze."
        )

    warnings: list[str] = []
    if size not in SUPPORTED_SIZES:
        if size not in WARN_SIZES:
            raise UnsupportedReplayError(f"{size}v{size} is not supported.")
        warnings.append(f"{size}v{size} is outside the 2v2/3v3 target; thresholds may not fit.")
    if not getattr(replay, "is_ladder", False):
        warnings.append("Not a ladder game; results may not reflect ranked play.")
    return ModeInfo(mode=f"{size}v{size}", team_size=size, warnings=warnings)


def load_replay(path: str | Path, load_level: int = 4) -> tuple[Any, ModeInfo]:
    """Load and validate a replay. Returns the raw sc2reader replay and its mode."""
    path = Path(path)
    if not path.is_file():
        raise ParseError(f"Replay not found: {path}")
    try:
        replay = sc2reader.load_replay(str(path), load_level=load_level)
    except Exception as exc:  # sc2reader raises many unrelated exception types
        raise ParseError(f"Could not parse {path.name}: {type(exc).__name__}: {exc}") from exc
    return replay, classify_mode(replay)
