# Scope and Phases

## Phase 1 — MVP: Replay → Markdown (no LLM required)
- CLI: `sc2koach analyze <replay.SC2Replay> -o report.md`
- sc2reader parsing, ranked 2v2/3v3 (teams modeled explicitly)
- 5 per-player metrics: workers at 4:00, unspent resources, supply blocks, expansion timings, army value curve
- 2 team metrics: team army value over time (vs. enemy team), player elimination / early ally death
- Moment detection with timestamps
- Comparative view: teammate vs. teammate and player vs. opposing counterpart (paired by lobby slot)
- Focus player is a configurable parameter (`--focus <name>`, default from config, initially `blacksheep`); all players are always analyzed
- Deterministic Markdown report

## Phase 2 — LLM coach
- One prompt consuming findings JSON
- Top 2–3 priorities per player, each with timestamp + drill
- Validate against human-coach judgment

## Phase 3 — Depth
- More metrics: APM/EPM, inject/chrono, control groups, fights, scouting
- Benchmarks by matchup and MMR
- Per-player history/trends stored locally (SQLite)
- Further team/joint-activity metrics (attack sync, resource disparity, contribution share); race-specific metrics for T, P, then Z

## Phase 4 — GUI / delivery
- Local web app: upload replay, view report, charts, history
- Optional Discord bot
- Team view with shared weaknesses

## Phase 5 — Maybe
- 1v1 / archon support
- pysc2 re-run for full observations
