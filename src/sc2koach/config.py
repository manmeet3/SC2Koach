"""Configuration loading (design/DESIGN.md §10).

Precedence: CLI flags > `sc2koach.toml` in the working directory >
`~/.config/sc2koach/config.toml` > built-in defaults. Layers are deep-merged: nested tables
merge key by key, everything else (including lists) is replaced by the later layer.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from sc2koach.errors import ConfigError
from sc2koach.thresholds import CoachSettings, ReportSettings, Thresholds

CWD_CONFIG_NAME = "sc2koach.toml"
HOME_CONFIG_PATH = Path(".config") / "sc2koach" / "config.toml"
RACES = frozenset({"Terran", "Protoss", "Zerg"})
CLI_SOURCE = "command-line flags"


class FocusConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = "blacksheep"
    toon_handle: str | None = None
    aliases: list[str] = Field(default_factory=list)


class RosterMember(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    toon_handle: str | None = None
    aliases: list[str] = Field(default_factory=list)


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")

    focus: FocusConfig = Field(default_factory=FocusConfig)
    roster: list[RosterMember] = Field(default_factory=list)
    thresholds: Thresholds = Field(default_factory=Thresholds)
    report: ReportSettings = Field(default_factory=ReportSettings)
    coach: CoachSettings = Field(default_factory=CoachSettings)


def load_config(
    cli: dict | None = None,
    cwd: Path | None = None,
    home: Path | None = None,
    explicit_path: Path | None = None,
) -> Config:
    """Build the effective Config from defaults, config files and CLI flags.

    With `explicit_path`, that file replaces the cwd/home files (it must exist).
    `None` values in `cli` are ignored, as are empty lists (unset repeatable flags).
    """
    layers: list[tuple[str, dict[str, Any]]] = []
    if explicit_path is not None:
        explicit_path = Path(explicit_path)
        if not explicit_path.is_file():
            raise ConfigError(f"config file not found: {explicit_path}")
        layers.append((str(explicit_path), _read_toml(explicit_path)))
    else:
        home_file = (home if home is not None else Path.home()) / HOME_CONFIG_PATH
        cwd_file = (cwd if cwd is not None else Path.cwd()) / CWD_CONFIG_NAME
        for path in (home_file, cwd_file):
            if path.is_file():
                layers.append((str(path), _read_toml(path)))
    if cli:
        layers.append((CLI_SOURCE, _prune_cli(cli)))

    merged = Config().model_dump()
    config = Config()
    for source, layer in layers:
        merged = _deep_merge(merged, layer)
        config = _validate(merged, source)
    return config


def effective_thresholds_dict(th: Thresholds) -> dict:
    """JSON-friendly dump of the effective thresholds (for findings JSON / report)."""
    return th.model_dump(mode="json")


# --------------------------------------------------------------------------- helpers


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: TOML syntax error: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"{path}: cannot read config file: {exc}") from exc


def _prune_cli(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if item is None or (isinstance(item, list | tuple) and len(item) == 0):
                continue
            pruned = _prune_cli(item)
            if isinstance(pruned, dict) and not pruned:
                continue
            out[key] = pruned
        return out
    if isinstance(value, tuple):
        return list(value)
    return value


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _config_error(source: str, exc: ValidationError, prefix: str = "") -> ConfigError:
    problems = []
    for err in exc.errors():
        key = prefix + ".".join(str(part) for part in err["loc"])
        if err["type"] == "extra_forbidden":
            problems.append(f"unknown key '{key}'")
        else:
            problems.append(f"invalid value for '{key}': {err['msg']}")
    return ConfigError(f"{source}: " + "; ".join(problems))


def _validate(data: dict[str, Any], source: str) -> Config:
    try:
        config = Config.model_validate(data)
    except ValidationError as exc:
        raise _config_error(source, exc) from None

    th = config.thresholds
    _check_race_keys(th.model_dump(), "thresholds", source)
    for ruleset_id, overrides in th.rulesets.items():
        where = f"thresholds.rulesets.{ruleset_id}"
        _check_race_keys(overrides, where, source)
        try:
            th.for_ruleset(ruleset_id)
        except ValidationError as exc:
            raise _config_error(source, exc, prefix=f"{where}.") from None
    return config


def _check_race_keys(values: dict[str, Any], where: str, source: str) -> None:
    """Per-race threshold tables may only use race names as keys."""
    defaults = Thresholds().model_dump()
    for key, value in values.items():
        if key == "rulesets" or not isinstance(defaults.get(key), dict):
            continue
        if not isinstance(value, dict):
            continue
        unknown = sorted(set(value) - RACES)
        if unknown:
            raise ConfigError(
                f"{source}: unknown key '{where}.{key}.{unknown[0]}' "
                f"(expected one of {', '.join(sorted(RACES))})"
            )
