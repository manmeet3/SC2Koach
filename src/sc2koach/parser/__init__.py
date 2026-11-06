"""Replay loading and normalization. The only package that imports sc2reader (ADR-002)."""

from .loader import ModeInfo, classify_mode, load_replay
from .model_builder import build_replay_model

__all__ = ["ModeInfo", "build_replay_model", "classify_mode", "load_replay"]
