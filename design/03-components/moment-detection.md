# Moment Detection

**Responsibility:** turn metrics into timestamped, prioritized `Finding`s.

## Rule shape
Each rule: `detect(metrics, comparisons) -> list[Finding]`. A finding has type, player, time range, severity, evidence numbers, and (later) a benchmark comparison.

## Initial rules
| Rule | Example output |
|---|---|
| Supply block | "Supply blocked ~2:10–2:35 (≈25s) with 150 minerals banked" |
| High bank | "Banked 1,200+ resources for 35s at 6:00 (SQ 48)" |
| Late expansion | "Second base finished 1:10 after teammate's and 0:50 after the enemy team's average" (in-game comparison; benchmarks in Phase 3) |
| Low worker count | "24 workers at 4:00 (team average 31)" |
| Army collapse | "Lost 80% of army value in 20s with resources banked" |
| Early ally death (team) | "Player 2 eliminated at 7:40; team played 3v2 for 6:10" |
| Team army deficit (team) | "Team army value 40% below enemy from 8:00–10:30" |

Team-aware: a finding carries the player and team; team-level findings (e.g. "team army value collapsed") are separate from per-player ones. Findings are phrased neutrally for every player, since any player may be the focus.

## Ranking
Every finding is scored in one common unit: **estimated resource cost**. Ranking is then a single sort, across rule types and players.

| Finding | Estimated cost |
|---|---|
| Supply block | blocked seconds × player's income rate (resources/s) at the time |
| High bank | (bank − threshold) × seconds above threshold × opportunity factor (default 0.05/s) |
| Late expansion | delay seconds × expected income of one saturated base |
| Low worker count | worker deficit × per-worker income × remaining seconds to 8:00 |
| Army collapse | army value lost above a fair trade (lost − killed) |
| Team findings | same formulas summed over the team |

`severity` = cost normalized to 0–1 per replay; `evidence.est_cost` keeps the raw number. These are rough estimates for ordering, not displayed as facts. Weights are config values, tuned during validation. Keep the top N per player for the coach; keep all in the JSON.

## Default thresholds (Gold–Platinum, team games)
Starting values only, tuned against real replays during validation. All live in `[thresholds]` config.

| Threshold | Default |
|---|---|
| Low workers at 4:00 | < 26, or ≥ 6 below the game's team average |
| High bank | > 800 resources for ≥ 30s before 6:00; > 1,200 after 6:00 |
| Late expansion | ≥ 45s after the teammate/enemy average for that base number |
| Army collapse | ≥ 60% of army value lost within 30s |
| Early ally death | team kept playing ≥ 60s afterwards |

## Principles
- Thresholds in a config file, not hard-coded.
- Rules are pure and unit-testable.
