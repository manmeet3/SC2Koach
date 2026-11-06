# sc2Koach

Coaching reports for StarCraft II ranked **2v2/3v3** replays: replay → deterministic metrics → timestamped findings → Markdown report. The full design is in [`design/DESIGN.md`](design/DESIGN.md).

> Status: **Phase 1 MVP** (deterministic report, no LLM yet).

## Setup
Requires Python 3.11+ (pinned to 3.12 in `.python-version`).

```powershell
uv sync                      # or: python -m venv .venv; .venv\Scripts\pip install -e . pytest ruff
```

## Usage
```powershell
sc2koach analyze <replay.SC2Replay> [-o report.md] [--focus NAME] [--focus-id TOON] [--alias NAME]... [--pair A:B]... [--config FILE]
sc2koach info <replay.SC2Replay>      # players, teams, lobby slots, MMR
```
`analyze` writes `<name>.md` and `<name>.findings.json`. Settings (focus player, roster, thresholds) can live in `sc2koach.toml` in the working directory or `~/.config/sc2koach/config.toml`; see [DESIGN.md §10](design/DESIGN.md#10-configuration). Exit codes: 2 unsupported replay, 3 unreadable replay, 4 bad config.

## Development
```powershell
ruff check .
pytest                                 # records/compares local golden files for fixture replays
python scripts/run_all.py replays      # analyze every local replay: errors, determinism, timing
python scripts/spike_m0.py replays     # data-assumption spike; re-run after every new game build (DESIGN.md §4)
```

### Replays
Replays contain other players' names and battle tags, so they are **never committed** (`replays/` is gitignored). Put them in `replays/` or point `SC2KOACH_REPLAYS` at a folder. Tests that need replays are skipped when none are found (e.g. in CI).
