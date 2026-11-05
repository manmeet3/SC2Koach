# M0 Spike Results

Run: `python scripts/spike_m0.py replays` on **375 ranked replays** (the author's local pool, never committed), sc2reader 1.9.0, Python 3.12. Wall time 24s with 8 processes. Builds 94137–98310. All numbers are aggregates; per-replay output stays in the gitignored `out/spike/`.

Pool: 300 × 3v3, 42 × 2v2, 33 × 4v4, all ladder; no 1v1, AI or archon. 10 games under 60s (remakes).

## Checklist answers
| # | Assumption | Result | Action |
|---|---|---|---|
| 1 | sc2reader loads current builds (Q11) | ✅ 375/375 at `load_level=4`; load p50 0.32s, max 0.86s | Keep sc2reader. No s2protocol fallback needed |
| 2 | `scaled_rating` holds MMR (Q25) | ✅ 2164/2232 players (97%). ⚠️ In 319/750 teams every member has the same value, which suggests arranged teams report a **team** MMR | Show as "MMR"; footnote that teammates may share a team rating. Missing → "n/a" |
| 3 | `food_used` includes units in production | ✅ `food_used` ≥ supply of finished living units + 1 in 73% of snapshots (median +2, p90 +14) | Snapshots are the source of truth for *used*; no stepping at births |
| 4 | `*_collection_rate` is per real minute | ✅ Minerals actually collected ÷ (rate × real minutes) = 0.97 median (p10 0.87, p90 1.04), over 1,548 T/P players from 2:00 to 6:00 | No rescale |
| 5 | Event worker count matches the in-game count | ⚠️ Terran/Protoss: events = snapshot in **100%** of 105k snapshots. Zerg: events overcount (median +1, p90 +2). A morphing drone's `UnitDiedEvent` fires when the **building finishes** (at its location), not when it starts; only 60/8,757 Zerg building starts have a drone death at the same loop | Use snapshot `workers_active_count`. "Workers at 4:00" = last regular snapshot ≤ 240s (3:56) |
| 6 | `used_current_army` is the in-game army value | ✅ Equals `used_active_forces` in 93% of non-zero snapshots (p90 difference 0). In-game confirmation pending (manual sheet) | Keep `used_current_army` |
| 7 | Overlords appear as `UnitBornEvent`; event-rebuilt cap works | ✅ Overlord births for 500/516 Zerg players (the rest are short games). Cap rebuilt from events = snapshot `food_made`: **Protoss 100%, Zerg 100%, Terran 96%**, after two fixes (below) | Calibrate town hall supply per replay; apply Extra Supplies; cap still resets at every snapshot |
| 8 | Unit `(x, y)` is in map units | ✅ Max coordinate 234; start → natural distance p10/p50/p90 = 21/26/45 | 15-unit expansion distance is fine |
| 9 | `sid` = lobby slot; toon handle present | ✅ Toon handles 375/375. Slots are contiguous per team: `[0,1,2] / [3,4,5]` | As designed |
| 10 | Leaves are marked; snapshots continue after | ⚠️ 689 mid-game leaves (> 10s before the end) in 236 games. Extra snapshot at the leave loop for 77%. Snapshots continue afterwards for only **61%**; in a sample, 102/249 leavers who still had buildings got none. The sc2reader docstring is wrong here | Team army value for a leaver without snapshots: see [metrics-engine](../03-components/metrics-engine.md#team-army-value-and-leavers) |
| 11 | Trade events appear | ✅ 121 `ResourceTradeEvent`s in 55 games. **No** request/fulfill events in the pool | Keep both paths; the request path has no fixture |
| 12 | CC landings are detectable with a position | ✅ 506 landings; 503 have a preceding `LandCommandCenter`/`LandOrbitalCommand` from the same player. Command → landing lag p50 17s, p90 40s (flight time). 336 landings are > 15 units from every earlier town hall, so expansion by landing is common | Match each landing to that player's latest Land command before it |
| 13 | < 30s per replay | ✅ Load ≤ 0.86s; the longest 3v3 (2h 41m) loads in 0.46s | — |

## Surprises
1. **Build 97563 uses a different ruleset:** 8 starting workers; CC and Nexus provide 13 supply, Hatchery 4 (vs. 12 / 15 / 6). This applies to all 96 replays from that build. A static supply table matched 0% of their snapshots. Fix: `gamedata.supply_table()` derives town hall supply from each player's first snapshot. Worker thresholds also depend on starting workers (below).
2. **Calldown: Extra Supplies** (Orbital ability, game event `ExtraSupplies`, +8 on the target depot) is in use. It isn't a tracker event, so the cap rebuild must read it from game events. This took Terran agreement from 88% to 96%. The remaining 4% is unexplained, probably the delay before the drop lands or casts that fail. It's harmless because the cap resets at every snapshot.
3. **4v4 is 9% of the pool.** It stays warn-only (Q30).

## Threshold calibration
Distributions across all players in this pool (the author's own lobbies). Defaults are set to flag roughly the slowest quarter. They are still starting values.

| Metric | Terran | Protoss | Zerg |
|---|---|---|---|
| Workers at 3:56 p25/p50, 12-worker start | 22 / 24 | 23 / 27 | 19 / 24 |
| Workers at 3:56 p25/p50, 8-worker start (b97563) | 19 / 21 | 21 / 23 | 18 / 22 |
| 2nd base finished p50/p75 | 4:08 / 5:44 | 3:49 / 4:47 | 2:31 / 2:53 |
| 3rd base finished p50/p75 | 9:26 / 11:43 | 8:22 / 9:47 | 6:50 / 9:08 |
| Bank (min + gas) before 6:00, p75/p90 | 581 / 934 | 603 / 917 | 594 / 944 |

The draft defaults (< 26 workers, 2nd base by 3:30) would have flagged more than half of Terran players. New defaults are in [moment-detection](../03-components/moment-detection.md#default-thresholds-goldplatinum-team-games).

## Fixtures
`tests/fixtures/replays.json` lists three replays by file name, SHA-256 and build (no player names). The files stay local; tests skip when they're absent.

| Fixture | Build | Mode | Covers |
|---|---|---|---|
| Sandstorm CE (29) | 98310 | 3v3 PPT vs PTZ | all races, mid-game leaver, trade, CC landing, latest build |
| Canyon of Tribulation (13) | 98310 | 3v3 TTZ vs PTZ | clean game (no leaver), trade, CC landing |
| New Bed of Chaos LE (5) | 97563 | 2v2 PT vs PZ | 8-worker ruleset, leaver, trade |

## Still manual
`out/spike/manual-check.md` lists supply, workers, income and army values at 4:00, 6:00 and 8:00 for each fixture. Open each replay and compare with the in-game panels. This confirms items 3–6 against the UI; the automated evidence above is already strong. Also confirm one CC landing position (item 12).
