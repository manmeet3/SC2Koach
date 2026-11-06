# Configuration and reference

- [Commands](#commands)
- [Config file](#config-file)
- [Focus player and teammates](#focus-player-and-teammates)
- [Thresholds](#thresholds)
- [Warning codes](#warning-codes)
- [Exit codes](#exit-codes)
- [Output files](#output-files)
- [Troubleshooting](#troubleshooting)

---

## Commands

```text
sc2koach analyze REPLAY [-o REPORT.md] [--focus NAME] [--focus-id TOON] [--alias NAME]...
                        [--pair NAME_A:NAME_B]... [--config FILE]
sc2koach info REPLAY      # teams, lobby slots, races, MMR, toon handles
sc2koach version
```

| Option | Meaning |
|---|---|
| `-o, --output` | Report path. Default: `<replay name>.md` in the current folder. The JSON goes next to it as `<name>.findings.json` |
| `--focus NAME` | Whose point of view ("you"). Case-insensitive. Default `blacksheep` |
| `--focus-id TOON` | Battle.net toon handle (e.g. `1-S2-1-1234567`, shown by `sc2koach info`). Survives name changes; checked before the name |
| `--alias NAME` | Other account names of the focus player (repeatable) |
| `--pair A:B` | Pair two opposing players as counterparts instead of the lobby-slot default (repeatable) |
| `--config FILE` | Use this config file instead of the default lookup |

Helper scripts (run from the repo folder):

| Script | Purpose |
|---|---|
| `python scripts/trends.py DIR --player NAME [--last N]` | One player's recurring problems across all replays, wins vs losses ([playbook](improvement-playbook.md#find-your-recurring-problems)) |
| `python scripts/run_all.py DIR` | Analyze every replay; report errors, determinism and timing |
| `python scripts/spike_m0.py DIR` | Check the game-data assumptions; run after a new game patch |

---

## Config file

Settings are merged in this order (later wins):

1. built-in defaults;
2. `~/.config/sc2koach/config.toml` (on Windows `C:\Users\<you>\.config\sc2koach\config.toml`);
3. `sc2koach.toml` in the current folder;
4. command-line flags.

With `--config FILE`, only that file is used (instead of 2 and 3). Unknown keys are an error, so typos are caught.

Example `sc2koach.toml`:

```toml
[focus]
name = "blacksheep"
toon_handle = "1-S2-1-1234567"
aliases = ["blacksheep2"]

[[roster]]                 # optional: your regular teammates
name = "teammate1"

[[roster]]
name = "teammate2"
toon_handle = "1-S2-1-7654321"

[thresholds]
supply_block_min_s = 10

[thresholds.low_workers_at_4m]
Terran = 24                # only Terran changes; Protoss/Zerg keep defaults

[thresholds.rulesets.w8-th13]   # only for replays on the 8-worker ruleset
late_2nd_base_s = { Terran = 320 }

[report]
top_n = 3                  # findings in each player's "Top priorities"
```

---

## Focus player and teammates

- **Matching order:** toon handle → name → aliases. Names are case-insensitive.
- **No match, or more than one:** the report is written in neutral third person, with a warning. sc2Koach never guesses.
- **Every player is always analyzed**; the focus only changes wording ("you") and order.
- **Roster:** optional list of regular teammates, used for history and team views in later phases.

---

## Thresholds

All detection settings, with defaults. Times are seconds of game time. Per-race values are tables with `Terran`, `Protoss` and `Zerg` keys. See the [findings guide](findings-guide.md) for what each rule does.

| Key | Default | Used by |
|---|---|---|
| `supply_block_min_s` | 7 | Shortest supply block reported |
| `trade_grace_s` | 20 | Resources received from an ally don't count as bank for this long |
| `expansion_min_distance` | 15 | Map units a town hall must be from every previous town hall to count as a new base |
| `high_bank_early` / `high_bank_late` | 800 / 1200 | Bank threshold for runs starting before / after `high_bank_cutover_s` |
| `high_bank_cutover_s` | 360 | 6:00 |
| `high_bank_min_s` | 30 | Minimum length of a banking run |
| `low_workers_at_4m` | T 22, P 23, Z 19 | Worker target at 4:00 (for 12 starting workers) |
| `low_workers_start_adjust` | 0.5 | Target lowered by `0.5 × (12 − starting workers)`, rounded |
| `late_2nd_base_s` | T 300, P 270, Z 180 | 2nd base should finish by 5:00 / 4:30 / 3:00 |
| `late_3rd_base_s` | T 600, P 540, Z 480 | 3rd base should finish by 10:00 / 9:00 / 8:00 |
| `army_collapse_frac` | 0.6 | Share of army lost in the window |
| `army_collapse_window_s` | 30 | Window length |
| `army_collapse_min_army` | 1000 | Army value needed at window start |
| `early_ally_death_s` | 60 | Team must keep playing this long after a departure |
| `team_army_deficit_ratio` | 0.6 | Team army at or below this share of the enemy's |
| `team_army_deficit_min_s` | 60 | Minimum deficit duration |
| `team_army_deficit_enemy_min` | 1500 | Enemy army must be at least this big |
| `bank_opportunity_factor` | 0.05 | Ranking weight for `high_bank` cost |
| `base_income_per_s` | 10 | Ranking weight for `late_expansion` cost |
| `worker_income_per_s` | 0.9 | Ranking weight for `low_workers` cost |
| `army_deficit_factor` | 0.01 | Ranking weight for `team_army_deficit` cost |
| `drift_min_cap_agreement` | 0.95 | Below this, warn `game_data_drift` (supply cap) |
| `drift_min_worker_agreement` | 0.99 | Below this, warn `game_data_drift` (workers) |
| `rulesets` | `{}` | Per-ruleset overrides, e.g. `[thresholds.rulesets.w8-th13]` |

The defaults were calibrated on 375 of your replays to flag roughly the slowest quarter of players. Lower the worker and base targets (or raise them) as your group improves.

---

## Warning codes

Shown on screen after `analyze` and in the report's Appendix.

| Code | Meaning | What to do |
|---|---|---|
| `mode_not_targeted` | 4v4: analyzed, but thresholds were tuned for 2v2/3v3 | Read with care |
| `not_ladder` | Custom or unranked game | Read with care |
| `unverified_build` | The game build is newer than any sc2Koach has been checked against | Usually fine; run `scripts/spike_m0.py` on a few new replays (see [DESIGN.md §4](../design/DESIGN.md#4-game-builds-and-rules)) |
| `game_data_drift` | The supply/worker self-check disagreed with the game's stats | Supply-block end times fall back to snapshots; numbers from snapshots are still exact |
| `unresolved_landing` | A Command Center landed but its Land command wasn't found | That base isn't counted as an expansion |
| `unresolved_resource_request` | A resource-request fulfilment couldn't be matched | Trade adjustment skipped for it |
| `focus_not_found` / `focus_ambiguous` | Focus player not in the game / matched several players | Neutral report; check `--focus` or use `--focus-id` |
| `bad_pair` | A `--pair` was invalid (unknown name, same team, malformed) | Fix the flag |

---

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Unexpected error |
| 2 | Unsupported replay: 1v1, FFA, uneven teams, archon, AI players, or under 60 seconds |
| 3 | Replay missing, corrupt or unreadable |
| 4 | Invalid config (unknown key, bad value, TOML syntax error, missing `--config` file) |

---

## Output files

- **`<name>.md`**: the report ([guide](reading-your-report.md)).
- **`<name>.findings.json`**: `schema_version`, tool and sc2reader versions, thresholds used, replay summary (players, teams, game rules), every metric series, every finding with evidence, and warnings. Times are seconds; series are `[time, value]` pairs. Schema: [DESIGN.md §9](../design/DESIGN.md#9-data-schemas).

Both files are byte-identical for the same replay and settings.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Report says "Focus: none" | Your name in that game differs. Run `sc2koach info <replay>` to see names and toon handles, then set `focus.toon_handle` in your config |
| `error: … 1v1 replays are out of scope` | Expected; sc2Koach analyzes team games only |
| Every game shows `unverified_build` after a patch | Run `python scripts/spike_m0.py <dir with new replays>` and follow the patch procedure in [DESIGN.md §4](../design/DESIGN.md#4-game-builds-and-rules) |
| `sc2koach` not found | Activate the virtual environment (`.venv\Scripts\Activate.ps1`) or run `.venv\Scripts\sc2koach` |
| Analysis feels too harsh or too lenient | Adjust [thresholds](#thresholds) in `sc2koach.toml` |
