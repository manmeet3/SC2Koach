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

## Supply block rule (initial)
Supply used ≥ supply made − 0 (capped) at consecutive snapshots / reconstructed timeline, ignoring maxed-out 200/200. Snapshot granularity (10s) limits precision, so reconstruct supply from unit events where possible. Min duration threshold (e.g., 3s) to filter noise.

## Testing
- Unit tests per metric with hand-checked values from fixture replays.
