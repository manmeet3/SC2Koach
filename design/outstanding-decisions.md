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
| Q25 | Does the replay actually contain each player's MMR? (sc2reader exposes a rating field for ladder games, but it may be missing or hidden) | The report will show MMR where available; no MMR means no rating-based bucketing | Verify at M0 with a real replay; if absent, show "n/a" and use a `--league` flag |
| Q27 | How is the focus player matched? Display names aren't unique and can change; one person may have several accounts | Wrong match means wrong "you" and polluted history | Match by Battle.net toon handle when configured, else by name. Config allows a list of aliases per person. No match: warn and write the report in neutral third person |
| Q28 | Are "my teammates" a fixed group (a roster to configure and track history for) or random ladder partners? | A roster enables a real team view and per-teammate history in Phase 3; random partners don't | Optional `roster` list in config; history is stored for all players either way |
| Q29 | What counts as an "early" ally death? | Decides when the early-ally-death finding fires | Any elimination or leave while the player's team keeps playing for ≥ 60s |

### Technical
| ID | Question | Why it matters | Default if undecided |
|---|---|---|---|
| Q6 | How should team games be modeled in `ReplayModel`? (teams → players, team result) | Affects every schema | `teams[]` each with `players[]`; result at team level |
| Q7 | How to define matchup keys for team compositions (e.g. `TP vs ZZ`, 3-race combos, ordering)? | Benchmark keys explode in count | Sort races within a team; key = mode + both compositions |
| Q8 | How to handle early leavers, disconnects, AI, or observers? | Distorts metrics and benchmarks | Flag the player, exclude from team-level aggregates |
| Q9 | Fight attribution in team fights: whose army value lost/killed? | Fights metric (Phase 3) | Team-level first; per-player later |
| Q10 | How precise must supply-block detection be given 10s snapshots? | Rebuild from unit events vs. snapshot approximation | Rebuild from unit events |
| Q11 | sc2reader support for the user's current game build? | Parser may fail on new patches | Test early in M0; fall back to s2protocol |
| Q12 | Front-end stack: FastAPI + React vs. Streamlit/NiceGUI? | Phase 4 effort | Decide at start of Phase 4 |
| Q13 | Discord bot in scope? | Delivery channel | Deferred |
| Q26 | Do ladder replays give a meaningful, stable lobby-slot order? The matchmaker assigns slots, so pairs may be arbitrary rather than matching who fights whom | Counterpart comparisons depend on it | Verify at M0. If slots are missing, fall back to player id order and note it in the report appendix |

### Data / benchmarks
| ID | Question | Why it matters | Default if undecided |
|---|---|---|---|
| Q14 | Benchmark source for team modes? Spawning Tool is mostly 1v1 | Little public data for 2v2/3v3; may need a self-built replay pool | Self-built pool from the user's own and downloaded replays |
| Q15 | Where do replays live, and how many exist? | Sizing the benchmark pool and test fixtures | Point CLI at a directory |
| Q16 | Benchmark by mode × composition × MMR will be sparse; is pooling by mode and race (ignoring partner) acceptable? | Statistical validity | Yes, pool by mode + own race + MMR bucket |
| Q17 | Privacy: may findings JSON go to the LLM API? Replays contain player names | User trust | Send findings only, with names replaced by "Player 1…" |

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
| — | Opposing counterparts are paired by **lobby slot**: the *i*-th player of each team (by slot order) face each other | 2026-10-31 |
| — | Focus player is a configurable parameter (`--focus`, config default `blacksheep`). One report serves the author and teammates; no separate shared version | 2026-10-31 |
| — | Team army value and player elimination / early ally death move into the Phase 1 MVP | 2026-10-31 |
