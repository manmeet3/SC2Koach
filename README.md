# sc2Koach

Coaching reports for StarCraft II ranked **2v2/3v3** replays: replay → deterministic metrics → timestamped findings → Markdown report. Design docs live in [`design/`](design/README.md).

> Status: **M0** (scaffold + parser spike). The `analyze` command is not implemented yet.

## Setup
Requires Python 3.11+ (pinned to 3.12 in `.python-version`).

```powershell
uv sync                      # or: python -m venv .venv; .venv\Scripts\pip install -e . pytest ruff
```

## Usage
```powershell
sc2koach info <replay.SC2Replay>      # players, teams, lobby slots, MMR
```

## Development
```powershell
ruff check .
pytest
python scripts/spike_m0.py replays     # M0 data-assumption spike
```

### Replays
Replays contain other players' names and battle tags, so they are **never committed** (`replays/` is gitignored). Put them in `replays/` or point `SC2KOACH_REPLAYS` at a folder. Tests that need replays are skipped when none are found (e.g. in CI).
