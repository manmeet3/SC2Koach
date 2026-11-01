# Tech Stack

| Concern | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | Ecosystem for SC2 tooling |
| Replay parsing | `sc2reader` | See [ADR-002](../07-decisions/adr-002-sc2reader-first.md); `s2protocol` as fallback |
| Models | `pydantic` or dataclasses | JSON validation/serialization |
| CLI | `typer` | Simple, typed |
| Storage (P3) | SQLite | Per-player history |
| LLM (P2) | Anthropic API | Structured JSON in, JSON out |
| Tests | `pytest` | Fixture replays |
| Packaging | `uv` / `pyproject.toml` | |
| GUI (P4) | FastAPI backend + web front-end (TBD) | See [gui-plan](../05-frontend/gui-plan.md) |
| Full-state (P5) | `pysc2` / SC2 API | Needs matching game client build |
