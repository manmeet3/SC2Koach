# Moment Detection

**Responsibility:** turn metrics into timestamped, prioritized `Finding`s.

## Rule shape
Each rule: `detect(metrics, comparisons) -> list[Finding]`. A finding has type, player, time range, severity, evidence numbers, and (later) a benchmark comparison.

## Initial rules
| Rule | Example output |
|---|---|
| Supply block | "Supply blocked 2:10–2:35 (25s)" |
| High bank | "Banked 1,500+ minerals for 40s at 6:00" |
| Late expansion | "Third base 40s later than benchmark" (needs benchmarks) |
| Low worker count | "38 workers at 4:00 vs. 44 typical" |
| Army collapse | "Lost 80% of army value in 20s with resources banked" |

Team-aware: a finding carries the player and team; team-level findings (e.g. "team army value collapsed") are separate from per-player ones. Ally findings are reported but not blamed on the user.

## Ranking
Severity = impact estimate (duration × weight, deviation from benchmark). Keep the top N per player for the coach; keep all in the JSON.

## Principles
- Thresholds in a config file, not hard-coded.
- Rules are pure and unit-testable.
