# Roadmap

| Milestone | Deliverable | Verify |
|---|---|---|
| M0 ✅ | Repo scaffold (`pyproject.toml`, `uv`, ruff, pytest, CI), sc2reader loads fixture replays, [spike checklist](#m0-spike-checklist) answered ([results](m0-spike-results.md)) | `pytest` loads and prints players with lobby slots, toon handles, MMR |
| M1 | `ReplayModel` + snapshots, nominal counterparts, elimination times, focus/roster matching, resource trades, town hall positions | Values match known replay facts; timestamps match the in-game clock within 1s |
| M2 | 5 per-player + 2 team MVP metrics | Unit tests vs. hand-checked values |
| M3 | Moment detection + cost-based ranking + findings JSON | Findings include expected block/bank on fixtures; ranking order sanity-checked by hand |
| M4 | Markdown report via CLI | Report renders for 3+ replays; output is byte-identical across two runs (golden-file test) |
| M5 | LLM coach (one prompt) | Passes [validation plan](validation-plan.md) |
| M6 | Benchmarks + history | Comparison fields populated |
| M7 | More metrics (APM, inject/chrono, fights) | Per-metric tests |
| M8 | GUI | Upload → report in browser |

## M0 spike checklist
Run sc2reader on **3+ current-patch ranked 2v2/3v3 replays** (at least one each with a Terran, a Protoss, a Zerg, a leaver, and a resource trade) and confirm each assumption. Record results in [outstanding-decisions](../outstanding-decisions.md). If one fails, apply the listed fallback before M2.

| # | Assumption | Fallback if wrong |
|---|---|---|
| 1 | sc2reader loads current-build replays at `load_level=4` without errors (Q11) | `s2protocol` per ADR-002 |
| 2 | `init_data["scaled_rating"]` holds MMR for ladder games (Q25) | Show "n/a"; add `--league` flag |
| 3 | `food_used` includes units in production (matches the in-game supply counter) | Step used up at `UnitBornEvent` between snapshots |
| 4 | `*_collection_rate` is per in-game (Faster) minute | Rescale by 1.4 |
| 5 | Event-based worker count at 4:00 matches the in-game worker count; Zerg drones that morph into buildings emit `UnitDiedEvent` | Use the snapshot `workers_active_count` |
| 6 | `minerals/vespene_used_current_army` matches the in-game army value (vs. `used_active_forces`) | Switch field |
| 7 | Overlords and larva units show up as `UnitBornEvent` (for the event-rebuilt cap) | Rely on the snapshot cap only |
| 8 | Unit `(x, y)` from Init/Born is in map coordinates on current builds (no ×4 scaling surprises) | Normalize in parser |
| 9 | `player.sid` gives the lobby slot order; `toon_handle` is populated | Fall back to player id order |
| 10 | `PlayerLeaveEvent` marks mid-game leaves; snapshots continue for leavers | Infer leave from the extra stats event |
| 11 | `ResourceTradeEvent` / `ResourceRequestFulfillEvent` appear for in-game trades | Drop trade adjustment; note in report |
| 12 | CC lift-off/landing appears as `UnitTypeChangeEvent` and the `Land` command target point is available | Skip landed expansions with a warning |
| 13 | Full pipeline runs in < 30s on a 20-min 3v3 | Lower `load_level`; drop unused event types |

Fixture replays from this spike become the M1–M4 test fixtures.

**Status (2026-11-05):** done on 375 replays; all 13 items answered. Items 5 and 10 used their fallbacks, and two surprises were fixed (build 97563 ruleset, Extra Supplies). See [m0-spike-results](m0-spike-results.md). An in-game look at the generated manual sheet is optional confirmation for items 3–6 and 12.
