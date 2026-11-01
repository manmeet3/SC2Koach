# Roadmap

| Milestone | Deliverable | Verify |
|---|---|---|
| M0 | Repo scaffold, sc2reader loads a fixture replay | `pytest` loads and prints players with lobby slots and toon handles |
| M1 | `ReplayModel` + snapshots, nominal counterparts, elimination times, focus/roster matching | Values match known replay facts |
| M2 | 5 per-player + 2 team MVP metrics | Unit tests vs. hand-checked values |
| M3 | Moment detection + findings JSON | Findings include expected block/bank on fixtures |
| M4 | Markdown report via CLI | Report renders for 3+ replays |
| M5 | LLM coach (one prompt) | Passes [validation plan](validation-plan.md) |
| M6 | Benchmarks + history | Comparison fields populated |
| M7 | More metrics (APM, inject/chrono, fights) | Per-metric tests |
| M8 | GUI | Upload → report in browser |
