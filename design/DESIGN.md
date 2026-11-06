# sc2Koach Design

Single source of truth for the sc2Koach design. **Status:** Phase 1 MVP implemented (M0–M4): `sc2koach analyze` runs on all 365 supported replays in the author's pool with no errors. Claims about replay data are backed by measurements in [Appendix A](#appendix-a-m0-spike-results).

**Core principle:** stats engine → findings → narrator. Facts are computed deterministically from the replay; an LLM only explains them.

## Contents
1. [Vision and scope](#1-vision-and-scope)
2. [Requirements](#2-requirements)
3. [Architecture](#3-architecture)
4. [Game builds and rules](#4-game-builds-and-rules)
5. [Parser](#5-parser)
6. [Metrics](#6-metrics)
7. [Findings: detection, ranking, thresholds](#7-findings-detection-ranking-thresholds)
8. [Report output](#8-report-output)
9. [Data schemas](#9-data-schemas)
10. [Configuration](#10-configuration)
11. [LLM coach (Phase 2)](#11-llm-coach-phase-2)
12. [Benchmarks and history (Phase 3)](#12-benchmarks-and-history-phase-3)
13. [GUI and delivery (Phase 4)](#13-gui-and-delivery-phase-4)
14. [Testing and validation](#14-testing-and-validation)
15. [Roadmap](#15-roadmap)
16. [Decisions](#16-decisions)
- [Appendix A: M0 spike results](#appendix-a-m0-spike-results)

---

## 1. Vision and scope

### Problem
Players and teams improve faster with specific, timestamped feedback, but human coaching is scarce and watching replays is slow.

### Solution
sc2Koach reads a StarCraft II replay and writes a coaching report. It does **not** have an LLM watch the replay. Replays are command logs plus periodic state snapshots, so we:
1. extract data deterministically;
2. compute metrics and flag key moments (findings);
3. optionally give the findings to an LLM that writes the coaching.

### Users
- **Now:** the author (`blacksheep`, Gold–Platinum, plays Terran/Protoss) and teammates, analyzing ranked **2v2/3v3** replays locally, output as Markdown. Every player and the team as a whole are analyzed. The **focus player** (who "you" refers to) is configurable, so anyone can run the same replay from their own point of view.
- **Later:** a GUI with history across games; a team view if a fixed group forms.

### Success criteria
- A report for a 2v2/3v3 replay is generated in under 30s locally, without an LLM.
- Metrics match the in-game stats panels within tolerance (see [§14](#14-testing-and-validation)).
- LLM coaching is judged "what a human coach would say" per the validation plan.

### Non-goals (for now)
Live-game overlay; full game-state re-simulation via the SC2 API (pysc2); cheating detection.

### Phases
| Phase | Scope |
|---|---|
| **1 — MVP** | CLI `sc2koach analyze <replay> -o report.md`. Ranked 2v2/3v3. 5 per-player metrics (workers at 4:00, unspent resources + spending quotient, supply blocks, expansion timings, army value) and 2 team metrics (team army value vs. enemy, elimination / early ally death). Findings ranked by estimated resource cost. Teammate and nominal-counterpart comparison. Configurable focus player. Deterministic Markdown report with per-player "Top priorities" (useful without an LLM) + versioned findings JSON |
| **2 — LLM coach** | One prompt over findings JSON → top 2–3 priorities per player with timestamps and drills; validated against human judgment |
| **3 — Depth** | APM/EPM, inject/chrono, control groups, fights, scouting, idle production, build order; benchmarks by mode/race/MMR; per-player history (SQLite); more team metrics (attack sync, contribution share); race-specific metrics (T, P, then Z); batch analysis |
| **4 — GUI / delivery** | Local web app (upload, report, charts, history, team view); optional Discord bot |
| **5 — Maybe** | 1v1/archon; pysc2 re-run for full observations |

---

## 2. Requirements

### Functional
| ID | Requirement | Phase |
|---|---|---|
| F1 | Parse a `.SC2Replay` and extract players, teams, map, build, duration, result | 1 |
| F2 | Compute the MVP metric set per player | 1 |
| F3 | Detect and timestamp notable moments (findings) | 1 |
| F4 | Write a Markdown report to a given path | 1 |
| F5 | Emit machine-readable findings JSON alongside the report | 1 |
| F11 | Accept a configurable focus player (`--focus`, `--focus-id`, `--alias`, or config) | 1 |
| F12 | Pair each player with a nominal opposing counterpart (lobby slot; `--pair` override) | 1 |
| F13 | Compute team metrics (team army value, elimination) | 1 |
| F14 | Without an LLM, list each player's top 3 findings by estimated cost as "Top priorities" | 1 |
| F15 | Resolve game rules per replay and warn when the build is unverified or game data looks out of date ([§4](#4-game-builds-and-rules)) | 1 |
| F6 | Generate LLM coaching from findings JSON | 2 |
| F7 | Compare against benchmarks (mode + race + MMR, per ruleset era) | 3 |
| F8 | Persist per-player history and report trends | 3 |
| F10 | Batch-analyze a directory of replays | 3 |
| F9 | Web GUI for upload, report view, history, team view | 4 |

### Non-functional
- **Deterministic:** same replay + same config → byte-identical metrics, findings and report.
- **LLM-optional:** useful with no API key.
- **Patch-tolerant:** a new game build never crashes analysis; values the game can change are read from the replay or flagged ([§4](#4-game-builds-and-rules)).
- **Separable stages:** each stage has a JSON contract so the GUI can reuse it.
- **Resilient:** unsupported or corrupt replays fail with a clear message and exit code, not a crash.
- **Testable:** metrics have unit tests on synthetic data and fixture replays.
- **Privacy:** replays and reports stay local. Replays are never committed to the (public) repo, since they contain other players' names and battle tags. Only anonymized findings JSON is sent to an LLM, and only on opt-in.

---

## 3. Architecture

```
 .SC2Replay
     │
     ▼
 ┌─────────┐ ReplayModel  ┌────────────────┐ Metrics  ┌──────────────────┐
 │ Parser  │ ───────────▶ │ Metrics Engine │ ───────▶ │ Moment Detection │
 └────┬────┘ + GameRules  └────────────────┘          └────────┬─────────┘
      │                           ▲                            │ Findings
      ▼                   ┌───────┴──────┐                     ▼
 gamedata rulesets        │ Benchmarks + │            ┌─────────────────┐
 (patch-specific values)  │ History (P3) │ ◀──────────│ LLM Coach (P2)  │
                          └──────────────┘  context   └────────┬────────┘
                                                               ▼
                                                      ┌─────────────────┐
                                                      │ Report Writer   │ → report.md + findings.json
                                                      └─────────────────┘
```

### Layers
1. **Core library** (`src/sc2koach/`): pure Python; each stage is a function taking and returning typed objects.
2. **CLI**: thin wrapper over the core.
3. **API/GUI** (Phase 4): wraps the same core; never reimplements logic.

### Pipeline stages
| Stage | Input | Output | Persisted |
|---|---|---|---|
| 1. Parse | replay path | `ReplayModel` (incl. `GameRules`) | optional cache |
| 2. Metrics | `ReplayModel` | `MetricsBundle` per player, `TeamMetrics` per team | in findings JSON |
| 3. Benchmark (P3) | metrics, mode, race, MMR, ruleset | `Comparisons` | no; MVP passes `null` |
| 4. Moments | metrics, team metrics, comparisons, thresholds | `Finding[]` | in findings JSON |
| 5. Coach (P2) | anonymized findings, history summary | `Coaching` | in findings JSON |
| 6. Report | all of the above | `report.md` | yes |
| 7. History (P3) | metrics, findings | SQLite rows | yes |

Rules:
- Only the parser imports sc2reader. Later stages read normalized artifacts, never sc2reader objects.
- Downstream code never reads patch-dependent constants directly; it uses the `GameRules` resolved for the replay ([§4](#4-game-builds-and-rules)).
- Every stage output is JSON-serializable ([§9](#9-data-schemas)).
- The LLM sees only findings, anonymized metadata and a short history summary; never raw events or real names.

### Repo layout
```
sc2Koach/
├── design/DESIGN.md        # this document
├── docs/                   # user documentation: how it works, reading reports, findings guide, playbook, config
├── scripts/                # spike_m0.py (patch drift check), run_all.py (full-pool run), trends.py (per-player trends)
├── src/sc2koach/
│   ├── parser/             # sc2reader → ReplayModel (loader.py exists: load + mode checks)
│   ├── metrics/            # one module per metric (registry)
│   ├── moments/            # rules → Findings, ranking
│   ├── report/             # Markdown rendering + finding text templates
│   ├── coach/              # (P2) prompt + LLM client
│   ├── benchmarks/         # (P3)
│   ├── gamedata.py         # rulesets + static tables (see §4)
│   ├── gametime.py         # loop ↔ seconds, m:ss
│   ├── errors.py           # error types → exit codes
│   ├── config.py           # TOML loading, precedence, thresholds
│   ├── models.py           # pydantic models (§9)
│   └── cli.py
├── tests/
│   └── fixtures/replays.json   # fixture manifest (file, SHA-256, build); replays stay local
└── replays/                # local only, gitignored
```

### Tech stack
| Concern | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ (pinned 3.12) | `tomllib`; `uv` installs the interpreter |
| Replay parsing | `sc2reader` ≥ 1.9 | ADR-002; `s2protocol` as fallback |
| Models | pydantic v2 | |
| CLI | typer | |
| Config | TOML | |
| Tests / lint | pytest / ruff (check + format) | |
| CI | GitHub Actions: ruff + pytest | No replays in CI; replay tests skip there ([§14](#14-testing-and-validation)) |
| Packaging | `pyproject.toml` (hatchling), console script `sc2koach` | `uv sync`, or venv + pip where `uv` downloads are blocked |
| LLM (P2) | Anthropic API | |
| Storage (P3) | SQLite | |
| GUI (P4) | FastAPI + web front-end (Q12) | |

---

## 4. Game builds and rules

### Why this matters
StarCraft II is patched several times a year, and each build can change the game's variables:
- **starting conditions:** starting workers, starting supply, starting units;
- **economy and supply:** unit costs, supply cost, supply provided by town halls/depots/pylons/overlords, build times, ability effects (e.g. Calldown: Extra Supplies);
- **content:** units and abilities added, removed or renamed; map pool and base layouts;
- **the replay format:** new or changed events and fields.

This has already happened in the author's replays. **Build 97563** (96 of 375 replays) starts players with **8 workers**, and its town halls give **13 supply (CC/Nexus) and 4 (Hatchery)**. The builds before and after it use 12 workers, 15 and 6. A hard-coded supply table matched 0% of that build's snapshots.

Tooling can lag behind the game too. sc2reader bundles per-build data packs (unit costs, supply cost, ability names), currently up to build 97364, and **silently applies the newest pack to any later build**. Unit data for builds 97563 and 98310 therefore comes from 97364 and could be stale.

### Principles
1. **Read, don't assume.** Prefer values the game itself reports in the replay over static tables.

   | Quantity | Source | Can a patch make it wrong? |
   |---|---|---|
   | Supply used/cap, workers, bank, income, army value, army lost/killed | Stats snapshots (computed by the game) | No |
   | Starting workers, starting supply | First stats snapshot per player | No |
   | Town hall supply provided | Derived per player from the first snapshot (`supply_table`) | No |
   | Depot/pylon/overlord supply provided, Extra Supplies amount | `gamedata` ruleset table | Yes — checked by the drift detector |
   | Unit cost, supply cost, unit/ability names | sc2reader data pack | Yes — data pack may lag; checked |
   | Base distances | Unit positions; `expansion_min_distance` config | New maps could need tuning |
   | Game speed (22.4 loops/s), stats cadence (160 loops) | Engine constants | Unlikely; checked by the spike |

2. **Resolve `GameRules` per replay.** The parser builds one `GameRules` object per replay and stores it in the `ReplayModel`:
   - `build`, `release` (e.g. `5.0.15.95248`), and `sc2reader_datapack` (the pack sc2reader actually used);
   - per player: `starting_workers`, `starting_supply`, and the calibrated `supply_table`;
   - `ruleset_id`: a signature of the observed starting conditions, e.g. `w12-th15` or `w8-th13`, so replays with the same rules group together whatever the build number;
   - `overrides` from `gamedata.RULESETS`: a table keyed by build range for values that can't be observed (depot/pylon/overlord supply, Extra Supplies amount, Land ability names). Builds not listed use the latest entry.

   Metrics and rules take every patch-dependent value from `GameRules`, never from module constants.
3. **Unknown builds still run, with a warning.** If the build is newer than the newest `RULESETS` entry or sc2reader's newest data pack, analysis proceeds with the latest known values. An `unverified_build` warning goes into the findings JSON and the report appendix.
4. **Self-check every replay (drift detection).** Two cheap agreement checks run on every replay (`supply.compute_drift`). They count only events strictly *before* each snapshot, because the game records a snapshot before applying the events at the same game loop:
   - event-rebuilt supply cap vs. snapshot `food_made` (expected ≥ 95%; on the 365-replay pool: Terran 99.7%, Protoss 99.9%, Zerg 99.9%);
   - Terran/Protoss event-based worker count vs. snapshot workers (expected ≥ 99%; pool: ≈ 100%).

   3 of 365 replays fall below threshold and get the warning.

   Below threshold, a `game_data_drift` warning names the build, and the affected metric falls back to snapshot-only data (e.g. a supply block ends at the next unblocked snapshot). Unknown unit types count as providing 0 supply and raise a warning; they never crash the run.
5. **Thresholds follow the rules.** Thresholds that depend on starting conditions are expressed relative to them (worker thresholds adjust for starting workers). Any threshold can be overridden per ruleset with `[thresholds.rulesets.<ruleset_id>]`.
6. **Don't mix eras silently.** History and benchmarks (Phase 3) store `build` and `ruleset_id`; benchmarks are bucketed by ruleset; trends that span a ruleset change are labeled.
7. **Patch procedure (manual, because CI has no replays).** When replays from a new build appear:
   1. run `python scripts/spike_m0.py replays` (≈ 25s for 375 replays) and read the drift numbers for the new build;
   2. if anything drifted, add a `RULESETS` entry and/or a calibration fix, and recalibrate thresholds if starting conditions changed;
   3. add one replay from the new build to `tests/fixtures/replays.json`;
   4. upgrade sc2reader if a release ships a newer data pack (or the build fails to load: ADR-002 fallback);
   5. record the change in the decision log ([§16](#16-decisions)).

### Rulesets observed so far
| `ruleset_id` | Builds seen | Starting workers | CC/Nexus supply | Hatchery supply | Replays |
|---|---|---|---|---|---|
| `w12-th15` | 94137, 95248, 95299, 95841, 96592, 96826, 96883, 98310 | 12 | 15 | 6 | 279 |
| `w8-th13` | 97563 | 8 | 13 | 4 | 96 |

Depot/pylon/overlord supply (8) and Extra Supplies (+8) were consistent across all builds seen.

---

## 5. Parser

**Responsibility:** turn a `.SC2Replay` into a normalized `ReplayModel` (with `GameRules`), isolating the rest of the system from sc2reader.

### Loading and validation
- `sc2reader.load_replay(path, load_level=4)`. M0: all 375 replays load, ≤ 0.86s each.
- **Supported:** 2v2 and 3v3. 4v4 and non-ladder team games parse with a warning (Q30). 1v1, FFA, uneven teams, archon, AI players, and games under 60s (remakes) raise `UnsupportedReplayError` (exit 2). Observers are dropped. Corrupt or unreadable files raise `ParseError` (exit 3). Implemented in `parser/loader.py`.

### Time
All times are **real seconds matching the in-game clock**: `t = game_loop / 22.4`. Don't use sc2reader's `event.second`; it counts Normal-speed seconds and is 1.4× off.

### Stats snapshots (`PlayerStatsEvent`)
- Every 160 loops (**~7.14s**, "regular" snapshots), plus usually one extra at a player's leave loop (77%) and one at game end.
- **Snapshots do not reliably continue after a player leaves** (61% in M0, contrary to the sc2reader docstring); see [team army value](#team-army-value-and-leavers).
- Fields kept: `minerals_current`, `vespene_current`, `minerals/vespene_collection_rate` (per real minute), `workers_active_count`, `food_used` (includes units in production), `food_made`, `minerals/vespene_used_current_army` (army value), cumulative `minerals/vespene_lost_army` and `minerals/vespene_killed_army`.
- The first snapshot gives `starting_workers` and `starting_supply` for `GameRules`.

### Unit events (tracker)
- `UnitBornEvent`, `UnitInitEvent`, `UnitDoneEvent`, `UnitDiedEvent`, `UnitTypeChangeEvent`, `UpgradeCompleteEvent`. Use the event's `control_pid` for ownership.
- Only Born/Init/Died carry `(x, y)` (map units; max 234 seen). Done and TypeChange carry no position, so a unit's position comes from its Born/Init event.
- Unit attributes (cost, supply, `is_army`, `is_building`, `is_worker`) are taken from sc2reader's data for the unit's type *at that event*. The sc2reader unit object only knows its final type, so copying from it would be wrong after a morph.
- **MULEs are not workers.** sc2reader flags them as workers, but the game's worker count excludes them.
- A Zerg drone that morphs into a building gets its `UnitDiedEvent` (no killer) when the building **finishes**, not when it starts.

### Game events
- Game events report `pid` as a *user* id; map to players with `event.player.pid`.
- **Leaves:** `PlayerLeaveEvent` → `left_at`. Leaves at the final loop are ignored (everyone "leaves" when the game ends).
- **Landed town halls:** a lifted CC/Orbital landing emits only `UnitTypeChangeEvent` (`*Flying` → grounded type), with no position. The landing point is the target of that player's latest `LandCommandCenter`/`LandOrbitalCommand` (`TargetPointCommandEvent`) before the type change. Commands carry no unit id, and the lag is flight time (p50 17s, p90 40s). If no command is found (3/506 in M0), the landing isn't counted and a warning is recorded.
- **Extra Supplies:** `ExtraSupplies` casts are kept as `{t, player, target_unit_id}` for the supply cap rebuild. They come from `TargetUnitCommandEvent`s and from shift-queued `UpdateTargetUnitCommandEvent`s. The update events repeat the previous command's ability name, which can be stale, so only casts targeting a supply depot are kept. This took Terran cap agreement from 96% to 99.7%.
- **Resource trades:** `ResourceTradeEvent` (direct transfer) and `ResourceRequestFulfillEvent` → `resource_trades[]` with `kind: trade | request`. sc2reader emits no trade event for fulfilled requests and doesn't number requests, so each fulfill is matched to an open `ResourceRequestEvent` by a guessed request id; unmatched fulfills raise `unresolved_resource_request`. M0 found 121 direct trades and no requests, so this path is untested on real data.
- Only the commands the MVP needs are kept (leaves, Land, Extra Supplies). Full command capture for APM/injects/chrono comes in Phase 3.

### Players, teams, identity
- Teams from `replay.teams`, with the result recorded at team level.
- `lobby_slot` = `player.sid` (contiguous per team); `toon_handle` = `player.toon_handle` (always present in M0); `mmr` = `init_data["scaled_rating"]`, `null` when missing or ≤ 0 (3%). Arranged teams appear to report a shared team rating (319/750 teams), which the report footnotes.
- **Nominal counterparts:** within each team, order players by slot (falling back to player id); the *i*-th player of one team is the counterpart of the *i*-th of the other (`counterpart_source`: `slot` | `player_id` | `manual`; `--pair` overrides). Replays don't show who fought whom, so pairing is a convention, not a fact.
- `eliminated_at` = death of the player's last structure (`is_building`; creep tumors excluded). `end_t = min(left_at, eliminated_at, game end)`. Leaves within 1s of the final loop are ignored.
- `spawn_point` = position of the starting town hall.
- `replay_sha256` for caching, fixtures and the report appendix.
- **Focus player:** the parser doesn't filter. It resolves the focus identity ([§10](#10-configuration)) to `focus_player_id`, or `null`.

---

## 6. Metrics

Per-player metrics are functions `compute(replay, player) -> MetricResult` in a registry; team metrics are `compute_team(replay, team)`. Outputs are time series and/or scalars.

### Common definitions
- **Player window:** per-player metrics cover `[0, end_t]`.
- **Undefined values:** if a metric can't be computed (e.g. the game ended before 4:00), it is `null` with a reason (`game_ended`, `player_ended`, `no_data`). Rules skip nulls; nothing is extrapolated.
- **Income rate** = `(minerals_collection_rate + vespene_collection_rate) / 60` resources/s, from the latest snapshot at or before `t`.
- **Team series** use only regular snapshots (loop % 160 == 0), which all players share.

### MVP metrics
| Metric | Definition | Output |
|---|---|---|
| Workers at 4:00 | Snapshot `workers_active_count` at the last regular snapshot ≤ 240s (3:56). Event counts overcount Zerg, so they aren't used | scalar + worker series |
| Unspent resources + SQ | Bank = minerals + gas per snapshot, trade-adjusted; spending quotient | series, mean, peak, seconds above threshold, SQ |
| Supply blocks | See below | `{start, end, duration_s, supply}` list |
| Expansion timings | See below | `{n, started, finished, x, y, source}` list |
| Army value | `minerals_used_current_army + vespene_used_current_army` | series |
| Team army value | Sum of members' army value, including leavers (below) | series per team + disparity (team − enemy) |
| Elimination | `{eliminated_at, left_at}` per player; `early` if the team kept playing ≥ 60s afterwards | list |

### Supply blocks
`food_used` already includes units in production, so snapshots are the source of truth for *used*. Events only refine when a block ended.
1. At each snapshot (t ≤ `end_t`), the player is **blocked** if `food_made < 200`, `food_made − food_used < 1` (a worker doesn't fit), the player has a living town hall, and `minerals_current ≥ 50` (a worker is affordable; being broke isn't a block).
2. Consecutive blocked snapshots merge. `start` = first blocked snapshot, so the duration is a **lower bound**.
3. `end` = the earlier of: the first time the event-rebuilt cap gives `cap − food_used ≥ 1`, and the next unblocked snapshot.
4. **Event-rebuilt cap:** supply providers add `GameRules.supply_table` values when they finish and remove them when they die, capped at 200. Extra Supplies adds its ruleset amount to the target depot from the cast time. The cap resets to `food_made` at every snapshot, so drift can't build up. If the drift detector fires, step 3 uses the next unblocked snapshot only.
5. Blocks shorter than `supply_block_min_s` (7s) are dropped.

### Unspent resources and spending quotient
- **Trades:** a sender's bank already drops, so sending needs no adjustment. For the receiver, `bank_adj(t) = max(0, bank(t) − received in (t − trade_grace_s, t])`, with a 20s grace window.
- **SQ** (Kasting): `SQ = 35 × (0.00137 × I − ln U) + 240`, where `I` = mean income per minute and `U` = mean `bank_adj` (floored at 1), over `[0, end_t]`. SQ is for comparison only; it doesn't trigger findings.

### Expansion detection
- **Candidates:** town hall `UnitDoneEvent` (CC/Nexus/Hatchery) at its Init position; and CC/Orbital **landings** at the resolved Land command target.
- A candidate counts only if it is more than `expansion_min_distance` (15) from **every location where the player ever had a finished town hall**, start location included. This excludes morphs (Orbital, PF, Lair, Hive), in-base town halls, macro hatcheries, and rebuilds at a previously held base. M0: start → natural distance p10 21, p50 26.
- `n` = order of distinct base locations (main = 1). `started` = Init time; `finished` = done or landing time; `source` = `built` | `landed`.

### Team army value and leavers
Snapshots stop for 39% of leavers. At each regular snapshot after `left_at`:
- if the leaver has a snapshot, use it;
- otherwise use `last_snapshot_army × event_army(t) / event_army(t_last)`, where `event_army` = summed cost of the leaver's finished, living, non-hallucinated army units. The ratio cancels the event-based Zerg overcount (event/snapshot army ≈ 1.00 T/P, 1.46 Z). Use 0 if `event_army(t_last)` is 0.

### Counterpart comparison
Team vs. enemy team is the primary comparison. Each player's scalars are also shown next to teammates' values and the nominal counterpart's value as context; no rule fires because a player trails an ally, a counterpart, or the game average.

### Later metrics
| Phase | Metric | Source |
|---|---|---|
| 3 | Idle production, build order, APM/EPM, inject/chrono consistency, control groups, fight outcomes, scouting | events + commands |
| 3+ | Contribution share, attack synchronization, team fight outcomes | snapshots + events |

---

## 7. Findings: detection, ranking, thresholds

Each rule is a pure function `detect(replay, metrics, team_metrics, thresholds) -> list[Finding]`. A finding has a type, scope (`player` | `team`), player, team, time range, evidence, estimated cost and severity. **Findings contain no prose**; the report renders text from per-type templates, so one findings JSON serves any focus player and the LLM.

### MVP rules
| Rule | Scope | Fires when | Example render |
|---|---|---|---|
| `supply_block` | player | each supply block (≥ 7s) | "Supply blocked from 2:10 for at least 25s (22/22) with 150 minerals banked" |
| `high_bank` | player | `bank_adj` above threshold for ≥ 30s straight | "Banked 1,200+ for 35s from 6:00 (peak 1,640)" |
| `low_workers` | player | workers at 4:00 below the race threshold (adjusted for starting workers) | "20 workers at 4:00 (game average 24)" |
| `late_expansion` | player | base 2 or 3 finished after the race threshold, or never taken while the player was still in | "Second base finished 5:40 (target 5:00)" |
| `army_collapse` | player | within 30s: lost ≥ 60% of army value at window start, that value ≥ 1,000, and lost > killed | "Lost 2,100 of 2,800 army value 9:10–9:40 while killing 600" |
| `early_ally_death` | team | a player eliminated or left while the team kept playing ≥ 60s | "Player 2 left at 7:40; team played a player down for 6:10" |
| `team_army_deficit` | team | team army ≤ 60% of enemy's for ≥ 60s, while enemy army ≥ 1,500 | "Team army value 40%+ below the enemy's 8:00–10:30" |

**Race-fair triggers:** Zerg naturally has more workers and expands earlier, so `low_workers` and `late_expansion` use race-specific absolute thresholds. Game, team and counterpart averages are evidence only.

No finding fires after a player's `end_t`, except team findings describing that departure.

### Ranking
All findings are scored in one unit, **estimated resource cost** (`evidence.est_cost`, an integer). Costs order the findings; they are never shown as facts.

| Finding | Estimated cost |
|---|---|
| `supply_block` | blocked seconds × income rate at block start |
| `high_bank` | Σ (bank_adj − threshold) × seconds × `bank_opportunity_factor` (0.05/s) |
| `late_expansion` | delay seconds × `base_income_per_s` (10/s); a missing base's delay runs to `end_t` |
| `low_workers` | deficit × `worker_income_per_s` (0.9/s) × (min(`end_t`, 480) − 240)s |
| `army_collapse` | lost − killed in the window |
| `early_ally_death` | departed player's mean income over the 60s before departure × seconds the team kept playing |
| `team_army_deficit` | Σ (enemy − team army) × seconds × `army_deficit_factor` (0.01/s) |

- Per player: findings sorted by cost; the top `report.top_n` (3) become "Top priorities", the top `coach.top_n` (5) go to the LLM. Team findings form a separate list.
- `severity` = cost / max cost in the replay (0–1). The JSON keeps all findings.
- **Deterministic IDs:** sort by (`start`, team, player, type), then number `f-001`, `f-002`, … Tests and the LLM cache rely on this.

### Default thresholds
Calibrated on the author's 375-replay pool to flag roughly the slowest quarter ([Appendix A](#threshold-calibration)), then tuned during validation. All are in `[thresholds]` config and can be overridden per ruleset.

| Threshold | Default |
|---|---|
| `supply_block_min_s` | 7s |
| High bank | > 800 for ≥ 30s starting before 6:00 (≈ p85); > 1,200 for ≥ 30s after 6:00 |
| Low workers at 4:00 (3:56 snapshot) | < 22 T, < 23 P, < 19 Z with 12 starting workers; subtract `round(0.5 × (12 − starting_workers))` otherwise (−2 for `w8-th13`) |
| Late 2nd base (finished by) | 5:00 T, 4:30 P, 3:00 Z |
| Late 3rd base (finished by) | 10:00 T, 9:00 P, 8:00 Z |
| Army collapse | ≥ 60% lost within 30s; ≥ 1,000 army at window start; lost > killed |
| Early ally death | team kept playing ≥ 60s |
| Team army deficit | ≤ 60% of enemy for ≥ 60s; enemy ≥ 1,500 |
| `trade_grace_s` | 20s |
| `expansion_min_distance` | 15 |

---

## 8. Report output

The report writer is pure templating with no analysis. It writes `<name>.md` and `<name>.findings.json` (the `AnalysisResult`) side by side; `<name>` defaults to the replay file stem, and `-o` overrides it. Output is byte-stable (sorted keys, fixed number formatting). One template per finding type is filled from `evidence`; "you" is used only for the focus player, third person for everyone else. Charts are text tables in Phase 1.

```
# <Team A players> vs <Team B players> — <Map> (<2v2|3v3>, <compositions>)
Date · Duration · Result (focus player's team, else "Team A won") · MMRs (n/a if absent; footnote: may be a shared team rating)
Focus: <player> ("none" → neutral report)

## Team
Team army value vs. enemy (every 30s), eliminations / early ally deaths, team findings (ranked)

## Summary
Per-player table: workers@4:00, avg bank, SQ, # supply blocks / total blocked s, 2nd/3rd base times.
Focus player first, then teammates, then opponents. Counterpart pairs side by side, labeled "nominal (lobby slot)" or "manual".

## Players
### <Player> (race, team, MMR) — focus player first
Top priorities: top 3 findings by cost (time, text, finding ID). Replaced by LLM coaching when present; IDs stay visible.
Metrics: workers@4:00, bank + SQ, supply blocks, expansions, army value (every 30s).
Context: same scalars for teammates and the nominal counterpart.

## Key Moments
| Time | Player | Type | Detail | ID |   (all findings, chronological)

## Appendix
Thresholds used, game build + ruleset_id, warnings (incl. unverified_build / game_data_drift), tool/sc2reader versions, schema version, replay SHA-256.
```
- Timestamps `m:ss`. A player with no findings gets "No issues detected by the current rules". Players who left show their `end_t`; metrics after it are blank.

---

## 9. Data schemas

Implemented as pydantic v2 models in `models.py`; the JSON below is illustrative. All times are real seconds.

### AnalysisResult (`<name>.findings.json`)
The single artifact the CLI writes, the report renders from, and the GUI/LLM stages read. `schema_version` is bumped on any breaking change.
```json
{
  "schema_version": 1,
  "tool_version": "0.1.0",
  "generated_with": {"sc2reader": "1.9.0", "thresholds": {}},
  "replay": {"...": "ReplayModel without snapshots/events"},
  "metrics": [{"...": "MetricsBundle"}],
  "team_metrics": [{"...": "TeamMetrics"}],
  "findings": [{"...": "Finding"}],
  "coaching": null,
  "warnings": [{"code": "unverified_build", "message": "Build 99001 is newer than known rules"}]
}
```
`thresholds` holds the effective values used for this run. Warning codes include `unverified_build`, `game_data_drift`, `unresolved_landing`, `mode_not_targeted`, `not_ladder`.

### ReplayModel
```json
{
  "game": {"map": "string", "duration_s": 620.5, "build": 98310, "release": "5.0.16.98310",
           "mode": "3v3", "is_ladder": true, "played_at": "2026-10-31T20:15:00Z", "replay_sha256": "hex"},
  "rules": {"ruleset_id": "w12-th15", "sc2reader_datapack": "97364", "verified_build": true,
            "overrides": {"supply_depot": 8, "extra_supplies": 8},
            "players": {"1": {"starting_workers": 12, "starting_supply": 15,
                              "supply_table": {"CommandCenter": 15, "SupplyDepot": 8}}},
            "drift": {"cap_agreement": 1.0, "worker_agreement": 1.0}},
  "focus_player_id": 1,
  "teams": [{"id": 1, "result": "Win", "composition": "PTZ", "players": [1, 2, 3]},
            {"id": 2, "result": "Loss", "composition": "PPZ", "players": [4, 5, 6]}],
  "players": [{"id": 1, "team": 1, "name": "string", "race": "Terran", "mmr": 4200,
               "lobby_slot": 0, "counterpart_id": 4, "counterpart_source": "slot",
               "toon_handle": "1-S2-1-1234567", "spawn_point": {"x": 128.5, "y": 42.0},
               "left_at": null, "eliminated_at": null, "end_t": 620.5}],
  "snapshots": [{"t": 7.14, "player": 1, "minerals": 120, "gas": 0, "income_per_min": 600,
                 "supply_used": 14, "supply_made": 15, "workers": 13, "army_value": 0,
                 "army_lost": 0, "army_killed": 0}],
  "unit_events": [{"t": 62.0, "player": 1, "kind": "init", "unit_id": 123, "unit_type": "CommandCenter",
                   "x": 120.0, "y": 60.0}],
  "resource_trades": [{"t": 312.5, "from": 1, "to": 2, "minerals": 200, "gas": 0, "kind": "trade"}],
  "land_commands": [{"t": 300.0, "player": 1, "x": 140.0, "y": 70.0}],
  "extra_supplies": [{"t": 410.0, "player": 1, "target_unit_id": 143917057}]
}
```
Composition = races sorted alphabetically by initial. Unit event `kind`: `born | init | done | died | type_change`.

### MetricsBundle
A nullable scalar is `{"value": null, "reason": "game_ended"}`.
```json
{
  "player": 1,
  "workers_at_4m": {"value": 24, "reason": null},
  "workers": [[7.14, 12]],
  "unspent": {"mean": 480, "peak": 1900, "sq": 62, "seconds_above_threshold": 35.7, "series": [[7.14, 120]]},
  "income": [[7.14, 600]],
  "supply_blocks": [{"start": 130.0, "end": 155.0, "duration_s": 25.0, "supply": 22}],
  "expansions": [{"n": 2, "started": 162.0, "finished": 233.0, "x": 120.0, "y": 60.0, "source": "built"}],
  "army_value": [[7.14, 0]]
}
```

### TeamMetrics
```json
{"team": 1, "army_value": [[7.14, 0]], "army_disparity": [[7.14, 0]],
 "eliminations": [{"player": 2, "eliminated_at": 460.0, "left_at": null, "early": true}]}
```

### Finding
```json
{"id": "f-001", "type": "supply_block", "scope": "player", "team": 1, "player": 1,
 "start": 130.0, "end": 155.0, "severity": 0.7,
 "evidence": {"est_cost": 375, "duration_s": 25, "supply": 22, "minerals": 150}, "benchmark": null}
```
Team findings set `scope: "team"`; `player` is the player concerned or `null`.

### Coaching (Phase 2)
```json
{"player": 1, "priorities": [{"rank": 1, "title": "string", "finding_ids": ["f-001"], "why": "string", "drill": "string"}]}
```

---

## 10. Configuration

Every player is always analyzed. Configuration decides only **perspective** (focus player), **identity matching**, optional **roster**, **pairing**, and **thresholds**.

**Precedence:** CLI flags > `sc2koach.toml` in the working directory > `~/.config/sc2koach/config.toml` > built-in defaults.

### Focus player
| CLI | Config | Meaning |
|---|---|---|
| `--focus <name>` | `focus.name` | Display name (default `blacksheep`) |
| `--focus-id <handle>` | `focus.toon_handle` | Battle.net toon handle; stable across name changes |
| `--alias <name>` (repeatable) | `focus.aliases` | Other names of the same person |

Matching order: toon handle → name → aliases (case-insensitive). If no player matches, or several do, the CLI warns, sets `focus_player_id = null`, and writes a neutral third-person report. It never guesses.

### Roster (optional)
```toml
[[roster]]
name = "blacksheep"
toon_handle = "1-S2-1-1234567"
aliases = ["blacksheep2"]
```
Without a roster, teammates are treated as random partners; history is still stored for every player. With a roster, Phase 3/4 history and team views group by member.

### Pairing
`--pair <nameA>:<nameB>` (repeatable) overrides the nominal lobby-slot pairing for one run.

### Thresholds
```toml
[thresholds]
supply_block_min_s = 7
trade_grace_s = 20

[thresholds.low_workers_at_4m]
Terran = 22
Protoss = 23
Zerg = 19

[thresholds.rulesets.w8-th13]          # optional per-ruleset overrides (§4)
late_2nd_base_s = { Terran = 300, Protoss = 270, Zerg = 180 }

[report]
top_n = 3
```
Unknown keys are an error. Effective values are written to the findings JSON and the report appendix.

### Exit codes
`0` success · `1` unexpected error · `2` unsupported replay (1v1, FFA, uneven, archon, AI, < 60s) · `3` corrupt replay or parser failure · `4` invalid config.

---

## 11. LLM coach (Phase 2)

Optional stage that turns findings into concise coaching.
- **Input:** top findings per player, anonymized game metadata, a short history summary. Never raw events.
- **Output (JSON → Markdown):** per player, the top 2–3 priorities, each with a title, finding IDs, why it matters, and a concrete drill; plus 1–2 team priorities.
- **Prompt rules:** use only facts in the findings; cite finding IDs; mention progress vs. history where available; direct, supportive, short; "you" only for the focus player.
- **Guardrails:** validate against the schema and retry once; fall back to deterministic Top priorities if the LLM fails or is unavailable; verify every cited ID and timestamp exists.
- **Anonymization:** names and toon handles are replaced with role aliases (`Player 1 (Focus)`, `Player 2 (Teammate)`, …) before the API call and mapped back by the report writer.
- **Caching:** responses are cached by `hash(findings_json + prompt_version + model_id)`.

---

## 12. Benchmarks and history (Phase 3)

- **Benchmarks:** self-built from local ladder replays run through the same pipeline (public sources are mostly 1v1). Keyed by mode, own race, MMR bucket and **ruleset era** ([§4](#4-game-builds-and-rules)); team composition is a secondary key if data allows. Stored as percentile tables per metric; comparison output `{metric, value, benchmark_p50, percentile}`. The MVP uses fixed thresholds instead.
- **History:** SQLite rows of per-game metrics and findings for every player (so any teammate can see their trends), including `build` and `ruleset_id`. Trend summaries for the coach ("supply blocks improved over the last 5 games") label any ruleset change inside the window.

---

## 13. GUI and delivery (Phase 4)

- The GUI wraps the core library through a thin API, with no analysis logic in the front-end.
- **Backend:** FastAPI with `POST /replays` (upload → pipeline in a background worker), `GET /reports/{id}`, `GET /players/{id}/history`, `GET /team/summary`.
- **Views:** upload; report (metrics, key-moment timeline, charts); per-player history; team view (shared weaknesses for a fixed group, or results by mode and composition for random partners), with a focus-player selector that switches perspective without re-running analysis.
- **Alternatives:** Discord bot (attach replay → summary). Front-end framework decided at the start of Phase 4 (Q12).

---

## 14. Testing and validation

### Automated tests
- **Synthetic (run in CI):** pure-function tests on hand-built snapshot/event lists for every metric and rule. Edge cases: blocks at 200, broke at cap, receiver grace window, rebuild at a lost base, CC landing, metrics after `end_t`, Extra Supplies, the 8-worker ruleset, a leaver without snapshots, an unknown build, an unknown unit type, drift fallback.
- **Fixture replays (local only):** `tests/fixtures/replays.json` lists each fixture's file name, SHA-256 and build. Tests check the hash, then assert known values. They skip when replays are absent, as in CI.
- **Golden files (local only):** `tests/golden/` (gitignored) holds the expected Markdown and findings JSON for each fixture. `tests/test_pipeline.py` records them on first run and then compares byte-for-byte; set `SC2KOACH_UPDATE_GOLDEN=1` to re-record after an intended change. Run before every merge and release, since CI can't.
- **Full-pool run:** `python scripts/run_all.py replays` analyzes every local replay and reports errors, determinism and timing. Current: 365/365, ≈ 0.5s per analysis.
- **Determinism:** two runs produce byte-identical output.

### Metric accuracy
- Compare against the in-game stats panels for the fixtures (`out/spike/manual-check.md` lists values at 4:00/6:00/8:00).
- Hand-verify supply blocks and expansion times by watching the replay at those timestamps.

### Patch drift
After each new game build, follow the patch procedure in [§4](#4-game-builds-and-rules).

### Coaching quality (Phase 2)
1. Pick 10 replays; evaluate the focus player and one ally in each (20 profiles).
2. A human coach (Q18) writes their top 3 priorities per player without seeing the tool's output.
3. A priority matches if it names the same failure mode within ±30s. Overlap score = matched / 3.
4. **Pass:** average overlap ≥ 2/3; zero fabricated facts or timings (checked automatically against the findings JSON); zero harmful or contradictory advice.

**Rule:** don't add new metrics until the current set passes validation.

---

## 15. Roadmap

| Milestone | Deliverable | Verify |
|---|---|---|
| **M0 ✅** | Scaffold (pyproject, ruff, pytest, CI), loader with mode validation, `sc2koach info`, data spike on 375 replays, fixture manifest | [Appendix A](#appendix-a-m0-spike-results) |
| **M1 ✅** | `ReplayModel` + `GameRules` (rulesets, calibration, drift checks), snapshots, unit events, trades, Land/Extra Supplies commands, counterparts, elimination, focus/roster matching | 365/365 supported replays parse; drift ≥ 99.7% per race; ≤ 1.04s per replay |
| **M2 ✅** | 5 per-player + 2 team metrics | Synthetic tests (edge cases in §14) |
| **M3 ✅** | Findings, cost ranking, deterministic IDs, findings JSON | Synthetic tests per rule and boundary |
| **M4 ✅** | Markdown report via `sc2koach analyze` | Fixture golden files (local); determinism over all 365 replays; 195 tests |
| M5 | LLM coach | Passes coaching validation |
| M6 | Benchmarks + history | Comparison fields populated, bucketed by ruleset |
| M7 | More metrics (APM, inject/chrono, fights) | Per-metric tests |
| M8 | GUI | Upload → report in browser |

---

## 16. Decisions

### Architecture decisions
- **ADR-001: deterministic analysis first; the LLM narrates.** LLMs can't reliably "watch" replays and may hallucinate, so all facts are computed deterministically and the LLM only receives findings. + Reproducible, testable, useful without an LLM; citations constrain hallucination. − Coaching is bounded by which findings we detect.
- **ADR-002: sc2reader first, behind `ReplayModel`.** Fast to build and enough for MVP and team analytics. Fallback to Blizzard's `s2protocol` if sc2reader fails on a current build. M0: no fallback needed. − May lag new builds (its data packs already lag; see [§4](#4-game-builds-and-rules)). pysc2 is deferred because it needs a matching game client.

### Assumptions in force
| # | Assumption | Revisit if |
|---|---|---|
| A1 | Python 3.11+ | — |
| A2 | Ranked 2v2 and 3v3 are the targets; 1v1 out of scope; 4v4 warn-only | User wants 1v1, or Q30 |
| A3 | Phase 1 delivery is a local CLI writing Markdown | — |
| A4 | LLM = Claude API, Phase 2 | — |
| A5 | History in SQLite, Phase 3 | — |
| A6 | Every player is analyzed; the focus player is a configurable perspective (default `blacksheep`) | — |
| A7 | Skill range Gold–Platinum; thresholds calibrated on the author's own lobbies | Range widens |
| A8 | One report per replay; each person runs it with themselves as focus | — |
| A9 | Game rules can change with any build; patch-dependent values come from `GameRules`, not constants | — |

### Open questions
| ID | Question | Default if undecided |
|---|---|---|
| Q7 | Matchup keys for team compositions (benchmarks) | Sort races within a team; key = mode + both compositions |
| Q9 | Fight attribution in team fights | Team-level first; MVP `army_collapse` uses the player's own lost/killed |
| Q12 | Front-end stack (FastAPI + React vs. Streamlit/NiceGUI) | Decide at the start of Phase 4 |
| Q13 | Discord bot in scope? | Deferred |
| Q14 | Benchmark source for team modes | Self-built pool from local replays (375 exist) |
| Q16 | Benchmark pooling | Mode + own race + MMR bucket + ruleset era |
| Q18 | Human reference coach for validation | User self-review at first |
| Q19 | Attributing cross-player causes (e.g. an ally died early) | Report facts side by side; LLM links players only via a team finding |
| Q22 | Race-specific metrics (MULE, chrono, injects): which races, which order? | Generic first; then Terran + Protoss; then Zerg |
| Q30 | 4v4 is 9% of the author's replays: promote from warn-only? | Warn-only for MVP; revisit after validation |
| Q31 | Why does build 97563 use 8 workers and lower town hall supply (patch, event, or test ruleset)? | Irrelevant to correctness, since rules are observed per replay; worth knowing for benchmark eras |
| Q32 | Ranking bias: `high_bank` is the #1 Top priority for 75% of players, but on 201 decided games banking doesn't predict losses (lower-bank team won 43%), while SQ (86%), team army deficit (77% of losses vs 15% of wins), army collapses, missing third base and workers at 4:00 do. Re-weight costs (e.g. scale bank cost by SQ or cap it) toward what predicts losses? | Documented as a caveat in docs/reading-your-report.md until decided |

### Decision log
| ID | Decision | Date |
|---|---|---|
| — | Deterministic analysis first (ADR-001); sc2reader behind `ReplayModel` (ADR-002) | 2026-10-31 |
| Q1–Q5 | Target ranked 2v2/3v3, Gold–Platinum; all players and all races analyzed; team/joint activities in scope | 2026-10-31 |
| Q20, Q21, Q23, Q24 | In-game comparisons (teammate, nominal counterpart) in MVP; one report with team section then per-player sections; MMR shown | 2026-10-31 |
| Q26–Q29 | Nominal lobby-slot counterparts (`--pair` override); focus identity by toon handle → name → alias; optional roster; early ally death = team kept playing ≥ 60s | 2026-10-31 |
| Q17 | LLM sees anonymized findings only; output cached | 2026-10-31 |
| — | Time unit: real seconds (`loop / 22.4`); snapshots every ~7.14s | 2026-10-31 |
| — | Findings ranked by estimated resource cost; separate player and team lists; deterministic IDs; prose-free findings; one versioned `AnalysisResult` | 2026-11-02 |
| Q6, Q8 | Teams with players and team-level result; unsupported modes → exit 2; per-player metrics stop at `end_t` | 2026-11-02 |
| Q10 | Supply blocks detected from snapshots (`food_used` includes queued units); events only refine the end; duration is a lower bound | 2026-11-02 |
| — | Expansion = new base location (built or landed); landings located by Land command; rebuilds don't count | 2026-11-02 |
| — | Trades include fulfilled requests; receiver gets a 20s grace window | 2026-11-02 |
| — | `low_workers` and `late_expansion` use race-specific absolute thresholds | 2026-11-02 |
| Q11 | sc2reader 1.9.0 loads all 375 replays (builds 94137–98310) | 2026-11-05 |
| Q15 | 375 local replays; never committed (public repo, other players' names); fixtures via SHA-256 manifest | 2026-11-05 |
| Q25 | MMR present for 97%; may be a shared team rating; no `--league` flag | 2026-11-05 |
| — | Workers at 4:00 from the snapshot; leaver army estimated from events when snapshots stop; games < 60s rejected | 2026-11-05 |
| — | Thresholds recalibrated on the replay pool ([§7](#default-thresholds)) | 2026-11-05 |
| — | Game rules resolved per replay (`GameRules`: observed starting conditions, calibrated supply, ruleset overrides, drift checks, unverified-build warning); patch procedure defined ([§4](#4-game-builds-and-rules)) | 2026-11-05 |
| — | Design consolidated into this single document | 2026-11-05 |
| — | MVP implemented (M1–M4). Drift checks count events strictly before each snapshot; MULEs excluded from workers; unit attributes taken per event type; Extra Supplies also read from queued casts | 2026-11-05 |

---

## Appendix A: M0 spike results

`python scripts/spike_m0.py replays` on **375 ranked replays** (the author's local pool, never committed), sc2reader 1.9.0, Python 3.12, about 24s with 8 processes. Builds 94137–98310. Pool: 300 × 3v3, 42 × 2v2, 33 × 4v4, all ladder; no 1v1, AI or archon; 10 games under 60s. All numbers are aggregates; per-replay output stays in the gitignored `out/spike/`.

### Checklist
| # | Assumption | Result | Decision |
|---|---|---|---|
| 1 | sc2reader loads current builds | ✅ 375/375; load p50 0.32s, max 0.86s | Keep sc2reader |
| 2 | `scaled_rating` holds MMR | ✅ 97% of players. ⚠️ In 319/750 teams all members share one value (team rating) | Show MMR with a footnote; missing → n/a |
| 3 | `food_used` includes units in production | ✅ ≥ finished living supply + 1 in 73% of snapshots (median +2, p90 +14) | Snapshots are the source of truth for *used* |
| 4 | Collection rates are per real minute | ✅ collected ÷ (rate × real minutes) = 0.97 median (p10 0.87, p90 1.04), 1,548 T/P players, 2:00–6:00 | No rescale |
| 5 | Event worker count = in-game count | ⚠️ T/P 100% exact over 105k snapshots. Zerg overcounts (median +1, p90 +2): drone death fires when the building finishes (only 60/8,757 starts match) | Use snapshot workers |
| 6 | `used_current_army` is the army value | ✅ equals `used_active_forces` in 93% of non-zero snapshots | Keep `used_current_army` (in-game check pending) |
| 7 | Overlords are `UnitBornEvent`s; cap can be rebuilt | ✅ 500/516 Zerg players (the rest are short games). After calibration and Extra Supplies: P 100%, Z 100%, T 96% | Per-replay calibration; reset at each snapshot |
| 8 | Positions in map units | ✅ max 234; start → natural p10/p50/p90 = 21/26/45 | `expansion_min_distance` 15 |
| 9 | `sid` = lobby slot; toon handles present | ✅ 375/375; slots contiguous per team | As designed |
| 10 | Leaves marked; snapshots continue after | ⚠️ 689 mid-game leaves in 236 games; extra snapshot at leave 77%; snapshots continue only 61% | Leaver army estimate (§6) |
| 11 | Trade events appear | ✅ 121 direct trades in 55 games; no request/fulfill events | Keep both paths; request path untested |
| 12 | CC landings locatable | ✅ 503/506 matched to a Land command; lag p50 17s, p90 40s; 336 landings > 15 from earlier town halls | Match the latest Land command |
| 13 | < 30s per replay | ✅ load ≤ 0.86s; longest 3v3 (2h 41m) 0.46s | — |

### Surprises
1. **Build 97563 ruleset** (`w8-th13`): 8 starting workers, CC/Nexus 13 supply, Hatchery 4, in all 96 replays of that build. A static table matched 0% of its snapshots. This led to [§4](#4-game-builds-and-rules).
2. **Calldown: Extra Supplies** is used and is not a tracker event. Applying it took Terran cap agreement from 88% to 96%. The remaining 4% is likely drop delay or failed casts; harmless because the cap resets each snapshot.
3. **sc2reader data packs lag:** its newest pack is 97364 and is applied to 97563 and 98310.
4. **4v4 is 9%** of the pool (Q30).

### Threshold calibration
Distributions across all players in the pool (the author's lobbies).

| Metric | Terran | Protoss | Zerg |
|---|---|---|---|
| Workers at 3:56, p25/p50, `w12-th15` | 22 / 24 | 23 / 27 | 19 / 24 |
| Workers at 3:56, p25/p50, `w8-th13` | 19 / 21 | 21 / 23 | 18 / 22 |
| 2nd base finished, p50/p75 | 4:08 / 5:44 | 3:49 / 4:47 | 2:31 / 2:53 |
| 3rd base finished, p50/p75 | 9:26 / 11:43 | 8:22 / 9:47 | 6:50 / 9:08 |
| Bank (min + gas) before 6:00, p75/p90 | 581 / 934 | 603 / 917 | 594 / 944 |

The draft defaults (< 26 workers; 2nd base by 3:30) would have flagged more than half of Terran players.

### Fixtures
| Fixture | Build | Mode | Covers |
|---|---|---|---|
| Sandstorm CE (29) | 98310 | 3v3 PPT vs PTZ | all races, mid-game leaver, trade, CC landing, latest build |
| Canyon of Tribulation (13) | 98310 | 3v3 TTZ vs PTZ | clean game (no leaver), trade, CC landing |
| New Bed of Chaos LE (5) | 97563 | 2v2 PT vs PZ | `w8-th13` ruleset, leaver, trade |

### Still manual
Compare `out/spike/manual-check.md` (local only; it contains player names) with the in-game panels for items 3–6, and confirm one CC landing position (item 12).
