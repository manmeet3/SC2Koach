# Tech Stack

| Concern | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | `tomllib` for config. `uv` installs the interpreter if the system Python is older |
| Replay parsing | `sc2reader` (≥ 1.9, maintained) | See [ADR-002](../07-decisions/adr-002-sc2reader-first.md); `s2protocol` as fallback |
| Models | `pydantic` v2 | JSON validation/serialization of every stage artifact |
| CLI | `typer` | Simple, typed |
| Config | TOML (`tomllib`) | See [configuration](configuration.md) |
| Storage (P3) | SQLite | Per-player history |
| LLM (P2) | Anthropic API | Structured JSON in, JSON out |
| Tests | `pytest` | Fixture replays + synthetic event/snapshot tests |
| Lint/format | `ruff` | |
| CI | GitHub Actions: `ruff check` + `pytest` on push/PR | Fixture replays are small (< 200 KB each) and committed |
| Packaging | `uv` / `pyproject.toml` (src layout, `sc2koach` console script) | |
| GUI (P4) | FastAPI backend + web front-end (TBD) | See [gui-plan](../05-frontend/gui-plan.md) |
| Full-state (P5) | `pysc2` / SC2 API | Needs matching game client build |
