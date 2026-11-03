# Architecture

```
 .SC2Replay
     │
     ▼
 ┌─────────┐   ReplayModel    ┌────────────────┐   Metrics    ┌──────────────────┐
 │ Parser  │ ───────────────▶ │ Metrics Engine │ ───────────▶ │ Moment Detection │
 └─────────┘                  └────────────────┘              └────────┬─────────┘
                                      ▲                                │ Findings
                              ┌───────┴──────┐                         ▼
                              │  Benchmarks  │                ┌─────────────────┐
                              │  + History   │ ◀──────────────│   LLM Coach     │ (optional)
                              └──────────────┘   context      └────────┬────────┘
                                                                        │ Coaching
                                                                        ▼
                                                               ┌─────────────────┐
                                                               │ Report Writer   │ → report.md
                                                               └─────────────────┘
```

## Layers
1. **Core library** (`sc2koach/`): pure Python, no I/O assumptions beyond file paths. Each stage is a function taking and returning typed objects.
2. **CLI**: thin wrapper over the core.
3. **API/GUI** (later): wraps the same core; never reimplements logic.

## Proposed repo layout
```
sc2Koach/
├── design/                 # this folder
├── src/sc2koach/
│   ├── parser/             # sc2reader → ReplayModel
│   ├── metrics/            # one module per metric
│   ├── moments/            # rules → Findings
│   ├── benchmarks/         # loaders, comparison
│   ├── coach/              # prompt + LLM client
│   ├── report/             # markdown rendering + finding text templates
│   ├── gamedata.py         # static unit tables: town halls, supply provided, workers, Land abilities
│   ├── config.py           # TOML loading, precedence, thresholds
│   ├── models.py           # pydantic models (see schemas.md)
│   └── cli.py
├── tests/
│   └── fixtures/           # small sample replays
└── data/                   # benchmarks, history db (gitignored where needed)
```

## Principles
- Each stage serializable to JSON for debugging and GUI reuse.
- Metrics are independent plug-ins registered in a registry.
- LLM stage is optional and isolated.
