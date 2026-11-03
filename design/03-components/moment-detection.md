# Moment Detection

**Responsibility:** turn metrics into timestamped, prioritized `Finding`s.

## Rule shape
Each rule: `detect(replay, metrics, team_metrics, thresholds) -> list[Finding]`. A finding has type, scope (`player` | `team`), player and team, time range, evidence numbers, estimated cost, severity, and (later) a benchmark comparison. Rules are pure functions.

Findings contain **no prose**. The [report writer](report-writer.md) renders text from per-type templates using `evidence`, so the same findings JSON works for any focus player ("you" vs. third person) and for the LLM.

## MVP rules
| Rule | Scope | Fires when | Example render |
|---|---|---|---|
| `supply_block` | player | Each block from the metric (≥ `supply_block_min_s`) | "Supply blocked from 2:10 for at least 25s (22/22) with 150 minerals banked" |
| `high_bank` | player | `bank_adj` above the bank threshold for ≥ 30s straight (one finding per run) | "Banked 1,200+ for 35s from 6:00 (peak 1,640)" |
| `low_workers` | player | Workers at 4:00 below the race threshold | "24 workers at 4:00 (game average 29)" |
| `late_expansion` | player | Base *n* (2 or 3) finished after the race threshold, or not taken at all while the player was still in the game at that time | "Second base finished 4:20 (target 3:30)" |
| `army_collapse` | player | Within a 30s window: army lost ≥ 60% of the army value at window start, that army value ≥ 1,000, **and** lost > killed | "Lost 2,100 of 2,800 army value 9:10–9:40 while killing 600" |
| `early_ally_death` | team | A player eliminated or left while their team kept playing ≥ 60s | "Player 2 left at 7:40; team played a player down for 6:10" |
| `team_army_deficit` | team | Team army value ≤ 60% of the enemy's for ≥ 60s, counting only time when the enemy's army ≥ 1,500 | "Team army value 40%+ below the enemy's 8:00–10:30" |

**Race-fair triggers.** Zerg naturally has more workers and expands earlier. In-game averages would therefore flag a Terran or Protoss in a lobby with Zergs. So `low_workers` and `late_expansion` fire on **race-specific absolute thresholds**. The game average, team average, and nominal counterpart value go into `evidence` as context only.

## Ranking
Every finding is scored in one common unit: **estimated resource cost** (`evidence.est_cost`, rounded to an integer). Costs are rough estimates used to order findings; they are never shown as facts.

| Finding | Estimated cost |
|---|---|
| `supply_block` | blocked seconds × player's income rate at block start (resources/s) |
| `high_bank` | Σ over the run of (bank_adj − threshold) × seconds × `bank_opportunity_factor` (0.05/s) |
| `late_expansion` | delay seconds × `base_income_per_s` (10/s); for a missing base, delay = min(`end_t`, game end) − threshold |
| `low_workers` | worker deficit vs. threshold × `worker_income_per_s` (0.9/s) × (min(`end_t`, 480) − 240) s |
| `army_collapse` | lost − killed in the window |
| `early_ally_death` | departed player's mean income over the 60s before departure × seconds the team kept playing |
| `team_army_deficit` | Σ over the window of (enemy − team army value) × seconds × `army_deficit_factor` (0.01/s) |

- **Per-player list:** that player's findings sorted by `est_cost` desc. The top `report.top_n` (3) go into the player's "Top priorities" in the report; the top `coach.top_n` (5) go to the LLM.
- **Team list:** team findings sorted the same way, shown in the Team section.
- `severity` = `est_cost / max est_cost in the replay` (0–1). The JSON keeps every finding.
- **Deterministic IDs:** after all rules run, findings are sorted by (`start`, team, player, type) and numbered `f-001`, `f-002`, … Same replay + same thresholds → same IDs. Regression tests and the LLM cache rely on this.

## Default thresholds (Gold–Platinum, team games)
Starting values only, tuned against real replays during validation. All live in `[thresholds]` config.

| Threshold | Default |
|---|---|
| `supply_block_min_s` | 7s |
| High bank | > 800 for ≥ 30s with the run starting before 6:00; > 1,200 for ≥ 30s after 6:00 |
| Low workers at 4:00 | < 26 Terran/Protoss; < 30 Zerg |
| Late 2nd base (finished by) | 3:30 Terran/Protoss; 2:45 Zerg |
| Late 3rd base (finished by) | 6:00 Terran/Protoss; 4:30 Zerg |
| Army collapse | ≥ 60% of army value lost within 30s; army value ≥ 1,000 at window start; lost > killed |
| Early ally death | team kept playing ≥ 60s afterwards |
| Team army deficit | team ≤ 60% of enemy for ≥ 60s; enemy army ≥ 1,500 |
| `trade_grace_s` | 20s |
| `expansion_min_distance` | 15 game units |

## Principles
- Thresholds and cost weights live in config, not hard-coded.
- Rules are pure and unit-testable on synthetic metrics.
- No finding fires after a player's `end_t`, except team findings that describe that departure.
