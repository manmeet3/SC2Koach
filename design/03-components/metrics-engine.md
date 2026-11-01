# Metrics Engine

**Responsibility:** compute per-player metrics from `ReplayModel`.

## Design
- Each metric = one function `compute(replay, player) -> MetricResult`, registered in a registry.
- Output is a time series and/or summary scalars, so both charts and findings can use it.
- Race-specific logic lives in separate functions chosen by player race.

## MVP metrics
| Metric | Output |
|---|---|
| Workers at 4:00 | scalar + worker-count series |
| Unspent resources | series, mean, peak, time above threshold |
| Supply blocks | list of `{start, end, duration, supply}` |
| Expansion timings | list of `{n, started, finished}` |
| Army value curve | series per player |
| Team army value | series per team + disparity series (team − enemy team) |
| Player elimination | per player `{eliminated_at, left_at}`; flagged as early ally death if the team kept playing ≥ 60s afterwards (threshold configurable) |

Team metrics are computed once per team, outside the per-player registry (`compute_team(replay, team) -> TeamMetricResult`). Per-player metrics stop at the player's `eliminated_at`/`left_at`.

## Counterpart comparison
Team vs. enemy team is the primary comparison. For each player, MVP scalars are also shown next to teammates' values and the **nominal** counterpart's value (see [configuration](../02-architecture/configuration.md)). This is context only: no rule fires just because a player trails an ally or a counterpart.

## Supply block rule (initial)
Supply used ≥ supply made − 0 (capped) at consecutive snapshots / reconstructed timeline, ignoring maxed-out 200/200. Snapshot granularity (10s) limits precision, so reconstruct supply from unit events where possible. Min duration threshold (e.g., 3s) to filter noise.

## Testing
- Unit tests per metric with hand-checked values from fixture replays.
