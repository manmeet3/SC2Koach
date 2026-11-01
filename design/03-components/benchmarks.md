# Benchmarks and History

## Benchmarks (Phase 3)
- Source options: Spawning Tool build timings, or a self-built pool of ladder replays run through the same parser/metrics.
- Keyed by mode (2v2/3v3), own race, and MMR bucket; team composition is a secondary key if data allows (see Q14, Q16). Public sources are mostly 1v1, so a self-built pool is likely.
- Stored as percentile tables per metric (e.g., third-base finish time p25/p50/p75).
- Comparison output: `{metric, value, benchmark_p50, percentile}`.

## History
- SQLite table of per-game metrics and findings per player.
- Trend summary for the coach: "supply blocks improved over last 5 games; banking unchanged."

## MVP
Skipped. Use fixed hand-chosen thresholds until benchmarks exist.
