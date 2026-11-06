"""Pydantic models for every pipeline artifact (design/DESIGN.md §9).

These are the contracts between stages. All times are real seconds (game_loop / 22.4).
Series are lists of [t, value] pairs sorted by t.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = 1

Race = Literal["Terran", "Protoss", "Zerg"]
Series = list[tuple[float, float]]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# --------------------------------------------------------------------------- warnings


class AnalysisWarning(_Model):
    """Codes: unverified_build, game_data_drift, unresolved_landing, unknown_unit_type,
    mode_not_targeted, not_ladder, focus_not_found, focus_ambiguous, bad_pair."""

    code: str
    message: str
    player: int | None = None


# --------------------------------------------------------------------------- game rules (§4)


class PlayerRules(_Model):
    starting_workers: int
    starting_supply: float
    supply_table: dict[str, float]


class GameRules(_Model):
    build: int
    release: str | None = None
    ruleset_id: (
        str  # e.g. "w12-th15", "w8-th13" (workers, town-hall supply of player 1's race family)
    )
    sc2reader_datapack: str | None = None
    verified_build: bool = True
    # Values that can't be observed from a replay; from gamedata.RULESETS.
    # Keys: "extra_supplies" (supply added by Calldown: Extra Supplies).
    overrides: dict[str, float] = Field(default_factory=dict)
    players: dict[int, PlayerRules] = Field(default_factory=dict)
    # Agreement rates from supply.compute_drift; None when not measurable.
    drift: dict[str, float | None] = Field(default_factory=dict)


# --------------------------------------------------------------------------- replay model (§5)


class Point(_Model):
    x: float
    y: float


class GameInfo(_Model):
    map: str
    duration_s: float
    end_loop: int
    build: int
    release: str | None = None
    mode: str  # "2v2" | "3v3" | "4v4"
    is_ladder: bool
    played_at: str | None = None  # ISO 8601 UTC
    replay_sha256: str


class Team(_Model):
    id: int
    result: Literal["Win", "Loss", "Tie", "Unknown"]
    composition: str  # race initials sorted alphabetically, e.g. "PTZ"
    players: list[int]


class Player(_Model):
    id: int
    team: int
    name: str
    race: Race
    mmr: int | None = None
    lobby_slot: int | None = None
    counterpart_id: int | None = None
    counterpart_source: Literal["slot", "player_id", "manual"] | None = None
    toon_handle: str | None = None
    spawn_point: Point | None = None
    left_at: float | None = None
    eliminated_at: float | None = None
    end_t: float


class Snapshot(_Model):
    t: float
    loop: int
    regular: bool  # loop == 1 or loop % 160 == 0; shared by all players
    player: int
    minerals: int
    gas: int
    income_per_min: float  # minerals + vespene collection rate, per real minute
    supply_used: float
    supply_made: float
    workers: int
    army_value: int  # minerals + vespene used_current_army
    army_lost: int  # cumulative minerals + vespene lost_army
    army_killed: int  # cumulative minerals + vespene killed_army


class UnitEvent(_Model):
    """One tracker unit event. `unit_type` is the unit's type at the time of the event
    (for type_change: the new type). Unit attributes are copied onto every event."""

    t: float
    loop: int
    player: int  # owner at the time of the event
    kind: Literal["born", "init", "done", "died", "type_change"]
    unit_id: int
    unit_type: str
    x: float | None = None
    y: float | None = None
    killer: int | None = None  # died only; None = no killer (e.g. morph, cancel)
    minerals: int = 0
    vespene: int = 0
    supply: float = 0  # supply cost
    is_army: bool = False
    is_building: bool = False
    is_worker: bool = False
    hallucinated: bool = False


class ResourceTrade(_Model):
    t: float
    from_player: int = Field(alias="from")
    to: int
    minerals: int
    gas: int
    kind: Literal["trade", "request"]


class LandCommand(_Model):
    t: float
    player: int
    x: float
    y: float


class ExtraSuppliesCast(_Model):
    t: float
    player: int
    target_unit_id: int


class ReplayHeader(_Model):
    """ReplayModel without the bulk event lists (what goes into AnalysisResult)."""

    game: GameInfo
    rules: GameRules
    focus_player_id: int | None = None
    teams: list[Team]
    players: list[Player]


class ReplayModel(ReplayHeader):
    snapshots: list[Snapshot] = Field(default_factory=list)  # sorted by (loop, player)
    unit_events: list[UnitEvent] = Field(default_factory=list)  # sorted by loop, stable
    resource_trades: list[ResourceTrade] = Field(default_factory=list)
    land_commands: list[LandCommand] = Field(default_factory=list)
    extra_supplies: list[ExtraSuppliesCast] = Field(default_factory=list)
    warnings: list[AnalysisWarning] = Field(default_factory=list)

    def player(self, pid: int) -> Player:
        return next(p for p in self.players if p.id == pid)

    def team_of(self, pid: int) -> Team:
        return next(t for t in self.teams if pid in t.players)

    def header(self) -> ReplayHeader:
        return ReplayHeader(
            game=self.game,
            rules=self.rules,
            focus_player_id=self.focus_player_id,
            teams=self.teams,
            players=self.players,
        )


# --------------------------------------------------------------------------- metrics (§6)


class NullableScalar(_Model):
    value: float | None = None
    reason: Literal["game_ended", "player_ended", "no_data"] | None = None


class Unspent(_Model):
    mean: float
    peak: float
    sq: float | None = None
    seconds_above_threshold: float
    series: Series  # trade-adjusted bank per snapshot


class SupplyBlock(_Model):
    start: float
    end: float
    duration_s: float
    supply: float  # supply cap during the block
    minerals: int  # minerals banked at block start


class Expansion(_Model):
    n: int  # base number; main = 1
    started: float | None  # None for the starting base
    finished: float
    x: float
    y: float
    source: Literal["start", "built", "landed"]


class MetricsBundle(_Model):
    player: int
    starting_workers: int
    workers_at_4m: NullableScalar
    workers: Series
    unspent: Unspent
    income: Series  # resources per minute
    supply_blocks: list[SupplyBlock]
    expansions: list[Expansion]
    army_value: Series
    army_lost: Series  # cumulative
    army_killed: Series  # cumulative


class Elimination(_Model):
    player: int
    eliminated_at: float | None
    left_at: float | None
    departed_at: float  # min of the two
    team_played_on_s: float  # seconds the rest of the team kept playing
    early: bool


class TeamMetrics(_Model):
    team: int
    army_value: Series
    army_disparity: Series  # team - enemy team
    eliminations: list[Elimination]


# --------------------------------------------------------------------------- findings (§7)

FindingType = Literal[
    "supply_block",
    "high_bank",
    "low_workers",
    "late_expansion",
    "army_collapse",
    "early_ally_death",
    "team_army_deficit",
]


class Finding(_Model):
    id: str  # "f-001", assigned after sorting
    type: FindingType
    scope: Literal["player", "team"]
    team: int
    player: int | None
    start: float
    end: float
    severity: float  # est_cost / max est_cost in the replay
    evidence: dict[str, float | int | str | None]  # always includes "est_cost" (int)
    benchmark: None = None


# --------------------------------------------------------------------------- coaching (P2)


class Priority(_Model):
    rank: int
    title: str
    finding_ids: list[str]
    why: str
    drill: str


class Coaching(_Model):
    player: int
    priorities: list[Priority]


# --------------------------------------------------------------------------- result


class GeneratedWith(_Model):
    sc2reader: str | None = None
    thresholds: dict = Field(default_factory=dict)


class AnalysisResult(_Model):
    schema_version: int = SCHEMA_VERSION
    tool_version: str
    generated_with: GeneratedWith
    replay: ReplayHeader
    metrics: list[MetricsBundle]
    team_metrics: list[TeamMetrics]
    findings: list[Finding]
    coaching: list[Coaching] | None = None
    warnings: list[AnalysisWarning] = Field(default_factory=list)
