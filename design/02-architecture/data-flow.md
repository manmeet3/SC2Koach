# Data Flow

| Stage | Input | Output | Persisted? |
|---|---|---|---|
| 1. Parse | replay path | `ReplayModel` | optional cache (`.json`) |
| 2. Metrics | `ReplayModel` | `MetricsBundle` (per player), `TeamMetrics` (per team) | with report |
| 3. Benchmark (P3) | `MetricsBundle`, matchup, MMR | `Comparisons` | no — MVP passes `null`; rules use fixed thresholds |
| 4. Moments | `MetricsBundle`, `TeamMetrics`, `Comparisons` | `Findings[]` | in `<name>.findings.json` (`AnalysisResult`) |
| 5. Coach | `Findings[]`, history summary | `Coaching` | with report |
| 6. Report | all of the above | `report.md` | yes |
| 7. History (P3) | `MetricsBundle`, `Findings` | SQLite row | yes |

## Rules
- Stages read only upstream normalized schema artifacts, never raw `sc2reader` objects. Downstream stages (like Coach and Report Writer) may read multiple upstream schema artifacts (e.g., Report reads ReplayModel, MetricsBundle, Findings, and Coaching).
- The LLM sees only `Findings[]`, anonymized game metadata, and short history summary — never raw replay events or real player names.
- Every stage output is JSON-serializable; see [schemas.md](../04-data/schemas.md).
