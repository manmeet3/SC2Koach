# Scope and Phases

## Phase 1 — MVP: Replay → Markdown (no LLM required)
- CLI: `sc2koach analyze <replay.SC2Replay> -o report.md`
- sc2reader parsing, ranked 2v2/3v3 (teams modeled explicitly)
- 5 metrics: workers at 4:00, unspent resources, supply blocks, expansion timings, army value curve
- Moment detection with timestamps
- Comparative view: teammate vs. teammate and player vs. opposing counterpart
- Default perspective player (`blacksheep`) via config; all players analyzed
- Deterministic Markdown report

## Phase 2 — LLM coach
- One prompt consuming findings JSON
- Top 2–3 priorities per player, each with timestamp + drill
- Validate against human-coach judgment

## Phase 3 — Depth
- More metrics: APM/EPM, inject/chrono, control groups, fights, scouting
- Benchmarks by matchup and MMR
- Per-player history/trends stored locally (SQLite)
- Team/joint-activity metrics (attack sync, army and resource disparity, early ally death); race-specific metrics for T, P, then Z

## Phase 4 — GUI / delivery
- Local web app: upload replay, view report, charts, history
- Optional Discord bot
- Team view with shared weaknesses

## Phase 5 — Maybe
- 1v1 / archon support
- pysc2 re-run for full observations
