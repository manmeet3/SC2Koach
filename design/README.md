# sc2Koach Design

Index of all design artifacts. Read in order for the full picture.

**Target:** ranked 2v2 and 3v3. Open items: [outstanding-decisions.md](outstanding-decisions.md).

| Area | Doc | Purpose |
|---|---|---|
| Overview | [vision.md](00-overview/vision.md) | What we're building and why |
| | [scope-and-phases.md](00-overview/scope-and-phases.md) | MVP vs. later phases |
| Requirements | [requirements.md](01-requirements/requirements.md) | Functional and non-functional requirements |
| | [metrics-catalog.md](01-requirements/metrics-catalog.md) | Every metric: definition, source, phase |
| Architecture | [architecture.md](02-architecture/architecture.md) | Pipeline overview and module layout |
| | [data-flow.md](02-architecture/data-flow.md) | Stage-by-stage data contracts |
| | [tech-stack.md](02-architecture/tech-stack.md) | Languages, libraries, tooling |
| Components | [parser.md](03-components/parser.md) | Replay → normalized model |
| | [metrics-engine.md](03-components/metrics-engine.md) | Normalized model → metrics |
| | [moment-detection.md](03-components/moment-detection.md) | Metrics → timestamped findings |
| | [benchmarks.md](03-components/benchmarks.md) | Comparison baselines and history |
| | [llm-coach.md](03-components/llm-coach.md) | Findings → coaching narrative |
| | [report-writer.md](03-components/report-writer.md) | Markdown report output |
| Data | [schemas.md](04-data/schemas.md) | JSON schemas for metrics and findings |
| | [report-format.md](04-data/report-format.md) | Markdown report layout |
| Frontend | [gui-plan.md](05-frontend/gui-plan.md) | Future web GUI / Discord delivery |
| Roadmap | [roadmap.md](06-roadmap/roadmap.md) | Milestones |
| | [validation-plan.md](06-roadmap/validation-plan.md) | How we check advice quality |
| Decisions | [adr-001-deterministic-first.md](07-decisions/adr-001-deterministic-first.md) | LLM never reads raw replays |
| | [adr-002-sc2reader-first.md](07-decisions/adr-002-sc2reader-first.md) | Parser choice |

## Core principle
**Stats engine → findings → narrator.** Facts are computed deterministically; the LLM only explains them.
