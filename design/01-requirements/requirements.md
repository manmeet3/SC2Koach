# Requirements

## Functional
| ID | Requirement | Phase |
|---|---|---|
| F1 | Parse a `.SC2Replay` file and extract players, map, duration, result | 1 |
| F2 | Compute the MVP metric set per player | 1 |
| F3 | Detect and timestamp notable moments | 1 |
| F4 | Write a Markdown report to a given path | 1 |
| F5 | Emit machine-readable findings JSON alongside the report | 1 |
| F6 | Generate LLM coaching from findings JSON | 2 |
| F7 | Compare against benchmarks (matchup + MMR) | 3 |
| F8 | Persist per-player history and report trends | 3 |
| F9 | Web GUI for upload, report view, history, team view | 4 |
| F10 | Batch analyze a directory of replays | 3 |

## Non-functional
- **Deterministic:** same replay → same metrics and findings.
- **LLM-optional:** the tool is useful with no API key.
- **Separable stages:** each pipeline stage has a JSON contract so the GUI can reuse it.
- **Resilient:** unsupported or corrupt replays fail with a clear message, not a crash.
- **Testable:** metrics have unit tests against fixture replays.
- **Privacy:** replays and reports stay local unless the user opts into an LLM call; only findings JSON (not replays) is sent.
