"""Errors and the CLI exit codes they map to (design/DESIGN.md §10)."""


class Sc2KoachError(Exception):
    exit_code = 1


class UnsupportedReplayError(Sc2KoachError):
    """Replay parsed fine but is outside scope (1v1, FFA, archon, AI, uneven teams)."""

    exit_code = 2


class ParseError(Sc2KoachError):
    """Replay is corrupt or the parser failed on it."""

    exit_code = 3


class ConfigError(Sc2KoachError):
    exit_code = 4
