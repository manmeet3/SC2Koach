# sc2Koach

**A coach for StarCraft II team games.** Point it at a ranked **2v2 or 3v3** replay and it tells you, with timestamps, what you and your teammates did that cost resources, army and ultimately the game. Then it helps you turn that into concrete things to practice.

```
$ sc2koach analyze "Sandstorm CE (29).SC2Replay" --focus Alpha
wrote Sandstorm CE (29).md
wrote Sandstorm CE (29).findings.json
```

An excerpt of the report (names made up):

```markdown
### Alpha (Terran, Team 1, MMR 2400)

#### Top priorities

1. 9:10 — You lost 2,100 of 2,800 army value 9:10–9:40 while killing 600 (`f-031`)
2. 5:00 — Your second base finished 5:40 (target 5:00; counterpart finished 4:02) (`f-012`)
3. 2:44 — You were supply blocked at 2:44 for at least 14s (21 supply) with 82 minerals banked (`f-004`)

### Eliminations

- Bravo (Team 1) left at 7:40; the team played on for 6:10
```

No AI guesses: every sentence comes from numbers the game itself recorded in the replay. Everything runs locally; nothing is uploaded.

---

## What it looks at

For **every player** in the game:

| | What | Why it matters (in the author's games) |
|---|---|---|
| 👷 | **Workers at 4:00** | The team with more early workers won 72% of games |
| 💰 | **Spending (SQ)** and unspent resources | The team that spent better relative to its income won 86% |
| 🏠 | **Expansion timings** (2nd and 3rd base, including landed Command Centers) | 45% of losing players never took a third base, against 21% of winners |
| ⛔ | **Supply blocks** | Production you can never get back |
| ⚔️ | **Army collapses**: most of an army lost in 30s without trading | Losing players had 60% more |

And for **the team**:

| | What | Why it matters |
|---|---|---|
| 📉 | **Team army deficit**: your combined army far behind the enemy's for a minute or more | Happened to 77% of losing teams and 15% of winning teams |
| 🚪 | **Early ally death**: a teammate left or died and the rest played a player down | 51% of losing teams vs 29% of winning teams |

Percentages come from 201 decided 2v2/3v3 games in the author's replay folder. See [what wins your games](docs/improvement-playbook.md#what-wins-your-games).

---

## Quick start

**1. Install** (Windows PowerShell; needs Python 3.11+, or let [`uv`](https://docs.astral.sh/uv/) install it):

```powershell
git clone https://github.com/manmeet3/SC2Koach.git
cd SC2Koach
uv sync                  # or: python -m venv .venv; .venv\Scripts\pip install -e .
.venv\Scripts\Activate.ps1
```

**2. Find your replays.** StarCraft II saves them in:

```
Documents\StarCraft II\Accounts\<number>\<region-number>\Replays\Multiplayer
```

**3. Analyze one:**

```powershell
sc2koach analyze "<path>\Some Map LE.SC2Replay" --focus <your in-game name> -o reports\game.md
```

Open `reports\game.md` in any Markdown viewer (VS Code, GitHub, Obsidian…).

**4. Tell it who you are once,** so you can drop `--focus`. Create `sc2koach.toml` in the folder you run it from:

```toml
[focus]
name = "<your in-game name>"
```

**5. Find your recurring problems** across all your games:

```powershell
python scripts/trends.py "<your replay folder>" --player <your name>
```

---

## How to use it to win more

1. **After a session**, analyze your games and open your worst loss.
2. **Read the Team section first**: when did the army gap turn against you? Did someone leave?
3. **Read your Top priorities**, weighing them as explained in [reading your report](docs/reading-your-report.md#how-to-weigh-top-priorities). Fights and army deficits matter most; banking is over-weighted.
4. **Jump to each timestamp in the replay** and find out *why* ([how](docs/reading-your-report.md#checking-a-finding-in-the-replay)).
5. **Write one concrete goal** for the next game, using the "What to do" sections of the [findings guide](docs/findings-guide.md).
6. **Every few weeks**, run `scripts/trends.py` to see whether the gaps between your wins and losses are closing.

Teammates can run the same replay with `--focus <their name>` to get the report from their own point of view. See [reviewing a game as a team](docs/improvement-playbook.md#reviewing-a-game-as-a-team).

---

## Documentation

| Guide | Read it to… |
|---|---|
| [How it works](docs/how-it-works.md) | Understand what's inside a replay, how each number is computed, and what the tool can't see |
| [Reading your report](docs/reading-your-report.md) | Go section by section through a report, and know which findings to act on first |
| [Findings guide](docs/findings-guide.md) | Learn what each of the 7 findings means in the game, how it's detected, and what to do about it (per race) |
| [Improvement playbook](docs/improvement-playbook.md) | Turn reports into practice: your data on what wins games, a post-session routine, team reviews, a 4-week plan |
| [Configuration and reference](docs/configuration.md) | Commands, config file, every threshold, warning and exit codes, troubleshooting |
| [Sample reports](sample-reports/README.md) | Real reports and per-player trends for one 3v3 team |
| [Design](design/DESIGN.md) | The full technical design (for contributors) |

---

## What it can't do (yet)

- See **where** fights happened or who fought whom. It sees army value going up and down, not the battle itself.
- Judge **micro, positioning, unit choices, scouting, build orders, upgrades or APM**. Findings tell you *when* to look in the replay; the replay tells you *why*.
- Analyze **1v1, FFA or archon** games, or games with AI players.
- Write coaching in prose with an LLM (planned for Phase 2), or track history in a database (Phase 3). Use `scripts/trends.py` for now.

Game patches can change starting conditions (e.g. build 97563 starts with 8 workers instead of 12). sc2Koach reads these from each replay rather than assuming them, and warns about builds it hasn't seen ([details](docs/how-it-works.md#game-patches-change-the-rules)).

---

## Development

```powershell
uv sync                                 # or: pip install -e . pytest ruff
ruff check . ; ruff format --check .
pytest                                  # replay-based tests skip when replays/ is empty
python scripts/run_all.py replays       # analyze every local replay: errors, determinism, timing
python scripts/spike_m0.py replays      # re-check game-data assumptions after a new game patch
```

Code layout: `src/sc2koach/` has `parser/` (replay → data model), `metrics/`, `moments/` (findings and ranking), `report/`, `config.py`, `identity.py` (focus player, pairs), `pipeline.py` and `cli.py`. See [DESIGN.md](design/DESIGN.md).

### Privacy
Replays contain other players' names and Battle.net IDs, so they are **never committed** (`replays/` and generated reports are gitignored). Tests that need replays read them from `replays/` or `SC2KOACH_REPLAYS` and are skipped when absent, as in CI.
