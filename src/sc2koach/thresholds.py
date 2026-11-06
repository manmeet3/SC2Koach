"""Detection thresholds and ranking weights with their defaults (design/DESIGN.md §7, §10).

Times are seconds. Per-race values are dicts keyed by race name. Config loading (config.py)
builds a Thresholds from TOML; `for_ruleset` applies `[thresholds.rulesets.<id>]` overrides.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

RaceInt = dict[str, int]


class Thresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supply_block_min_s: float = 7
    trade_grace_s: float = 20
    expansion_min_distance: float = 15

    # high_bank: run must last >= high_bank_min_s; threshold by run start time
    high_bank_early: int = 800
    high_bank_late: int = 1200
    high_bank_cutover_s: float = 360
    high_bank_min_s: float = 30

    # low_workers: threshold for 12 starting workers; subtract
    # round(low_workers_start_adjust * (12 - starting_workers)) otherwise
    low_workers_at_4m: RaceInt = Field(
        default_factory=lambda: {"Terran": 22, "Protoss": 23, "Zerg": 19}
    )
    low_workers_start_adjust: float = 0.5

    late_2nd_base_s: RaceInt = Field(
        default_factory=lambda: {"Terran": 300, "Protoss": 270, "Zerg": 180}
    )
    late_3rd_base_s: RaceInt = Field(
        default_factory=lambda: {"Terran": 600, "Protoss": 540, "Zerg": 480}
    )

    army_collapse_frac: float = 0.6
    army_collapse_window_s: float = 30
    army_collapse_min_army: int = 1000

    early_ally_death_s: float = 60

    team_army_deficit_ratio: float = 0.6
    team_army_deficit_min_s: float = 60
    team_army_deficit_enemy_min: int = 1500

    # ranking cost weights
    bank_opportunity_factor: float = 0.05
    base_income_per_s: float = 10
    worker_income_per_s: float = 0.9
    army_deficit_factor: float = 0.01

    # drift detection (design §4)
    drift_min_cap_agreement: float = 0.95
    drift_min_worker_agreement: float = 0.99

    # per-ruleset overrides, e.g. {"w8-th13": {"late_2nd_base_s": {"Terran": 320}}}
    rulesets: dict[str, dict[str, Any]] = Field(default_factory=dict)

    def for_ruleset(self, ruleset_id: str) -> Thresholds:
        """Thresholds with any overrides for `ruleset_id` applied (dicts are merged)."""
        overrides = self.rulesets.get(ruleset_id)
        if not overrides:
            return self
        data = self.model_dump()
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(data.get(key), dict):
                data[key] = {**data[key], **value}
            else:
                data[key] = value
        return Thresholds.model_validate(data)

    def low_workers_threshold(self, race: str, starting_workers: int) -> int:
        base = self.low_workers_at_4m[race]
        return base - round(self.low_workers_start_adjust * (12 - starting_workers))


class ReportSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    top_n: int = 3


class CoachSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    top_n: int = 5
