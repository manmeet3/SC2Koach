# Outstanding Decisions and Questions

Single log of unresolved items. When resolved, move to **Resolved** with the date and update the affected docs (or write an ADR in `07-decisions/`).

## Assumptions in force
| # | Assumption | Revisit if |
|---|---|---|
| A1 | Python 3.11+ | — |
| A2 | **Ranked 2v2 and 3v3** are the target modes (1v1 out of scope) | User also wants 1v1 or 4v4/FFA |
| A3 | Phase 1 delivery is a local CLI writing Markdown | — |
| A4 | LLM = Claude API, Phase 2 | — |
| A5 | History in SQLite, Phase 3 | — |
| A6 | Every player in the replay is analyzed and coached, with comparative analytics. The **focus player** (who "you" refers to, whose history is primary) is a configurable parameter: `--focus <name>`, default from config (`blacksheep`) | — |
| A7 | Skill range is Gold–Platinum; benchmarks bucketed accordingly | Range widens |
| A8 | There is one report per replay (no separate "shared" version). The author and teammates each run it with themselves as focus | — |

## Open

### Product / scope
| ID | Question | Why it matters | Default if undecided |
|---|---|---|---|
| Q22 | Some metrics only make sense for one race (Terran: MULE/scan usage; Protoss: chrono boost; Zerg: injects/larva). Do we build those for all three races, and in what order? | Teammates may play any race, but each race-specific metric is extra work | Generic metrics first (work for every race); then Terran + Protoss specifics; then Zerg |
| Q30 | 4v4 is 9% of the author's replays (33/375). Promote it from warn-only to supported? | Thresholds and team metrics were designed for 2v2/3v3 | Keep warn-only for MVP; revisit after validation |

### Technical
| ID | Question | Why it matters | Default if undecided |
|---|---|---|---|
| Q7 | How to define matchup keys for team compositions (e.g. `TP vs ZZ`, 3-race combos, ordering)? | Benchmark keys explode in count | Sort races within a team; key = mode + both compositions |
| Q9 | Fight attribution in team fights: whose army value lost/killed? | Fights metric (Phase 3) | Team-level first; per-player later. MVP `army_collapse` uses the player's own lost/killed and shows team killed as context |
| Q12 | Front-end stack: FastAPI + React vs. Streamlit/NiceGUI? | Phase 4 effort | Decide at start of Phase 4 |
| Q13 | Discord bot in scope? | Delivery channel | Deferred |

### Data / benchmarks
| ID | Question | Why it matters | Default if undecided |
|---|---|---|---|
| Q14 | Benchmark source for team modes? Spawning Tool is mostly 1v1 | Little public data for 2v2/3v3; may need a self-built replay pool | Self-built pool from the user's own and downloaded replays (375 local replays already exist; see Q15) |
| Q16 | Benchmark by mode × composition × MMR will be sparse; is pooling by mode and race (ignoring partner) acceptable? | Statistical validity | Yes, pool by mode + own race + MMR bucket |

### Coaching quality
| ID | Question | Why it matters | Default if undecided |
|---|---|---|---|
| Q18 | Who is the human reference coach for validation? | The validation plan needs a baseline | User self-review at first |
| Q19 | How should cross-player causes be attributed (e.g. an ally died early so the other lost map control)? | Avoids misattributed blame now that team play is in scope | Report the facts side by side; the LLM may note the interaction only when a team-level finding links the players |

## Resolved
| ID | Decision | Date |
|---|---|---|
| — | Deterministic analysis first; LLM narrates findings ([ADR-001](07-decisions/adr-001-deterministic-first.md)) | 2026-10-31 |
| — | Target modes: ranked 2v2 and 3v3 (user-confirmed) | 2026-10-31 |
| Q1 | League range Gold–Platinum | 2026-10-31 |
| Q2 | User plays Terran/Protoss; analytics wanted for all races | 2026-10-31 |
| Q3, Q4 | Analyze and coach all players in a replay. User's name `blacksheep` is saved as the default perspective (history, "you" wording), not as a filter (refined below: focus player is configurable) | 2026-10-31 |
| Q5 | Team/joint activities are in scope | 2026-10-31 |
| Q20 | Comparisons are bounded to the current game: teammate vs. teammate and player vs. opposing counterpart. Benchmark and history comparisons come later (Phase 3) | 2026-10-31 |
| Q21 | First joint activities: attack timing sync, army/resource disparity between allies, early ally death | 2026-10-31 |
| Q23 | One report: team section first, then a section per player | 2026-10-31 |
| Q24 | Include each player's MMR in the report (availability tracked in Q25) | 2026-10-31 |
| — | Opposing counterparts are paired by **lobby slot**: the *i*-th player of each team (by slot order) face each other (refined in Q26: nominal pairing) | 2026-10-31 |
| — | Focus player is a configurable parameter (`--focus`, config default `blacksheep`). One report serves the author and teammates; no separate shared version | 2026-10-31 |
| — | Team army value and player elimination / early ally death move into the Phase 1 MVP | 2026-10-31 |
| Q26 | Replays can't reliably show who fought whom. Counterparts are **nominal**: lobby-slot order, falling back to player id; `--pair` overrides. Labeled as nominal in the report; team vs. team is the primary comparison; counterpart gaps never trigger findings alone | 2026-10-31 |
| Q27 | Focus identity: `--focus` (name), `--focus-id` (toon handle), `--alias` (repeatable), or the same keys in config. Match order: toon handle → name → aliases. No unique match: warn, neutral third-person report | 2026-10-31 |
| Q28 | Roster is optional. No roster = random partners (history for all players, team view by composition). With a roster, history and team views group by member. See [configuration](02-architecture/configuration.md) | 2026-10-31 |
| Q29 | Early ally death = elimination or leave while the team keeps playing ≥ 60s (configurable) | 2026-10-31 |
| — | Time unit: real seconds matching the in-game clock (`game_loop / 22.4`). Snapshots are every ~7.14s, not 10s | 2026-10-31 |
| Q10 | Supply blocks: cap rebuilt from events, used interpolated from snapshots + births. Block = next unit doesn't fit **and** is affordable. Precision is roughly the snapshot interval; no sub-snapshot claims | 2026-10-31 |
| — | Resource trades (`ResourceTradeEvent`) are modeled; sender counts them as spent, receiver gets a grace window before bank penalties | 2026-10-31 |
| — | Findings ranked by one common unit: estimated resource cost | 2026-10-31 |
| — | Gold–Plat default thresholds; spending quotient moves into MVP alongside unspent resources; late expansion uses in-game comparison until benchmarks exist | 2026-10-31 |
| — | Expansion = town hall finished (or landed) at a new base location; morphs, in-base town halls and macro hatcheries excluded | 2026-10-31 |
| — | ADR-002 Accepted: Start with `sc2reader`, wrap in `ReplayModel`, fall back to `s2protocol` if patch compatibility breaks during M0 | 2026-10-31 |
| Q17 | Findings anonymize names with role aliases before LLM API; Report Writer de-anonymizes them back to real player names; LLM output cached deterministically | 2026-10-31 |
| Q6 | Team modeling: `teams[]` each with `players[]`, result at team level (see [schemas](04-data/schemas.md)) | 2026-11-02 |
| Q8 | Leavers: per-player metrics stop at `end_t`; their snapshots still count toward team army value (units stay under ally control). Observers dropped. AI, 1v1, FFA, archon → `UnsupportedReplayError` (exit 2) | 2026-11-02 |
| — | MVP review: supply blocks are detected from snapshots (`food_used` already includes queued units); events only refine the block end. Duration is a lower bound | 2026-11-02 |
| — | MVP review: landed CCs get their position from the `Land` command (tracker type-change events have no position); unresolved landings aren't counted, with a warning | 2026-11-02 |
| — | MVP review: trade adjustment also covers `ResourceRequestFulfillEvent` (sc2reader emits no trade event for fulfilled requests) | 2026-11-02 |
| — | MVP review: `low_workers` and `late_expansion` fire on race-specific absolute thresholds; in-game averages are evidence only (avoids flagging T/P next to Zerg) | 2026-11-02 |
| — | MVP review: every rule has a defined threshold and cost (adds team army deficit, early ally death, minimum army for collapse). Players and team are ranked in separate lists | 2026-11-02 |
| — | MVP review: findings carry no prose; report templates render text per focus. IDs are deterministic (sorted by time). One versioned `AnalysisResult` JSON | 2026-11-02 |
| — | MVP review: report gets per-player sections with deterministic top-3 priorities (useful without an LLM), matching Q23 | 2026-11-02 |
| — | MVP review: expansions count distinct base locations; rebuilds at a previously held base don't increment `n`. Late-expansion rule covers bases 2 and 3 only | 2026-11-02 |
| — | MVP review: stack pinned to pydantic v2, typer, ruff, pytest, GitHub Actions CI, `uv`-managed Python 3.11+ | 2026-11-02 |
| Q11 | sc2reader 1.9.0 loads all 375 replays (builds 94137–98310) at `load_level=4`, ≤ 0.86s each. No s2protocol fallback needed ([M0 results](06-roadmap/m0-spike-results.md)) | 2026-11-05 |
| Q15 | 375 ranked replays (300 3v3, 42 2v2, 33 4v4) in a local `replays/` folder. The repo is public and replays contain other players' names and battle tags, so they are **never committed**; tests use a SHA-256 manifest and skip without the files | 2026-11-05 |
| Q25 | MMR (`scaled_rating`) is present for 97% of players; missing → "n/a". Arranged teams appear to share a team rating, which the report footnotes. No `--league` flag needed | 2026-11-05 |
| — | M0: workers at 4:00 come from the snapshot (3:56), not events. Zerg drone deaths arrive when the building finishes | 2026-11-05 |
| — | M0: town hall supply is calibrated per player from the first snapshot (build 97563 ruleset: 8 workers, CC/Nexus 13, Hatchery 4). Extra Supplies casts are applied to the supply cap | 2026-11-05 |
| — | M0: a leaver's army after their snapshots stop = last snapshot × event-based alive-army ratio | 2026-11-05 |
| — | M0: thresholds recalibrated on the replay pool: workers T22/P23/Z19 (−2 with 8 starting workers); 2nd base T 5:00 / P 4:30 / Z 3:00; 3rd base T 10:00 / P 9:00 / Z 8:00 | 2026-11-05 |
| — | M0: games under 60s are rejected as unsupported (exit 2) | 2026-11-05 |
