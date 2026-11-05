# Parser

**Responsibility:** turn a `.SC2Replay` into a normalized `ReplayModel`, isolating the rest of the system from sc2reader.

## Input / Output
- In: replay path
- Out: `ReplayModel` — game metadata, players (name, race, MMR if present, result), time-indexed snapshots, unit/upgrade events, command events

## Details
- Load with `sc2reader.load_replay(path, load_level=4)` (full events needed for commands and unit events).
- **Time:** store all times as **real seconds matching the in-game clock**: `t = game_loop / 22.4` (Faster speed). Don't use sc2reader's `event.second`; it counts Normal-speed seconds (`loop / 16`) and is 1.4× off from the in-game timer.
- Snapshots come from `PlayerStatsEvent`, every 160 game loops (**~7.14 real seconds**), plus usually one extra event when a player leaves (77% in M0) and one at game end. **Snapshots do not reliably continue after a player leaves** (only 61% in M0, despite the sc2reader docstring); see [metrics-engine](metrics-engine.md#team-army-value-and-leavers). Fields kept: `minerals_current`, `vespene_current`, `minerals/vespene_collection_rate` (per real minute), `workers_active_count`, `food_used` (includes queued units), `food_made`, `minerals/vespene_used_current_army` (army value), and cumulative `minerals/vespene_lost_army` and `minerals/vespene_killed_army` (used for army collapse). The first snapshot also gives `starting_workers` (12 normally, 8 on build 97563).
- Unit events: `UnitBornEvent`, `UnitInitEvent`, `UnitDoneEvent`, `UnitDiedEvent`, `UnitTypeChangeEvent`, `UpgradeCompleteEvent`. Only Born/Init/Died carry `(x, y)`. **Done and TypeChange carry no position**, so a unit's position is the one from its Born/Init event. Use the event's `control_pid` for ownership. **Game events** report `pid` as a *user* id; map to players via `event.player.pid`. A Zerg drone that morphs into a building gets its `UnitDiedEvent` (no killer) when the building **finishes**, not when it starts.
- **Landed town halls:** a CC/Orbital that lifts and lands only emits `UnitTypeChangeEvent` (`*Flying` → `CommandCenter`/`OrbitalCommand`, no position). The landing point is the target of that player's latest `LandCommandCenter`/`LandOrbitalCommand` (`TargetPointCommandEvent`) before the type change. Commands don't carry the unit id, and the lag is flight time (p50 17s, p90 40s). If no command is found (3/506 in M0), the landing isn't counted as an expansion and a parser warning is recorded.
- **Extra Supplies:** `ExtraSupplies` `TargetUnitCommandEvent`s (Orbital Command calldown, +8 supply on the target depot) are kept as `{t, player, target_unit_id}` for the supply cap rebuild.
- Resource trades: `ResourceTradeEvent` (direct ally → ally transfer) **and** `ResourceRequestFulfillEvent` (filling an ally's request; amounts taken from the matching `ResourceRequestEvent`). sc2reader doesn't emit a trade event for fulfilled requests. Both go into `resource_trades[]` with `kind: "trade" | "request"`. M0 found 121 direct trades and no requests, so the request path has no fixture coverage.
- Command events (MVP): only what the MVP needs, i.e. `PlayerLeaveEvent`, Land commands, and `ExtraSupplies`. Full selection/control-group/ability capture for APM, injects, and chrono comes in Phase 3, which keeps the cached `ReplayModel` small.
- Static game data (town hall types, supply provided per unit type, worker types, Land ability names) lives in `sc2koach/gamedata.py`. sc2reader gives unit cost and supply *cost*, but not supply *provided*. **Town hall supply varies by patch**, so `gamedata.supply_table(race, first_food_made)` calibrates it per player from the first snapshot.

## Errors
- Unsupported build / corrupt file → `ParseError` with message; CLI exits with code 3 (see [configuration](../02-architecture/configuration.md#exit-codes)).
- Supported: 2v2 and 3v3. 4v4 and unranked/custom team games with ≥2 players per side parse with a warning. 1v1, FFA, uneven teams, archon mode, replays with AI players, and games **under 60s** (remakes) raise `UnsupportedReplayError` (exit code 2) with a clear message. Observers are dropped. Implemented in `parser/loader.py`.
- Teams come from `replay.teams`; record team result, leavers, and observers/AI (see Q8).
- **Counterparts (nominal):** record each player's lobby slot. Within each team, order players by slot (fall back to player id if slots are missing). The *i*-th player of one team is the nominal counterpart of the *i*-th player of the other (`counterpart_id`, `counterpart_source`: `slot` | `player_id` | `manual`). `--pair` overrides. Nothing in a replay reliably shows who fought whom, so pairing is a convention, not a fact.
- **Elimination:** record `left_at` (`PlayerLeaveEvent`; ignore leaves at the final game loop, since every player "leaves" when the game ends) and `eliminated_at` (`UnitDiedEvent` of the player's last structure, using sc2reader's `is_building`) per player.
- **Identity:** `lobby_slot` = sc2reader `player.sid` (contiguous per team in M0); `toon_handle` = `player.toon_handle`; `mmr` = `init_data["scaled_rating"]`, stored as `null` when missing or ≤ 0 (3% in M0). Arranged teams appear to report a shared team rating, so the report labels MMR as possibly a team rating.
- **Replay hash:** SHA-256 of the replay file, stored in `game.replay_sha256` for caching and the report appendix.
- **Spawn point:** record each player's starting spawn point `(x, y)` from initial base coordinates (used for distance-based expansion checks and map context).

## Focus player
- The parser does not filter by focus. It resolves the focus identity (toon handle → name → aliases; see [configuration](../02-architecture/configuration.md)) to `focus_player_id`, or `null` if there's no unique match.

## Testing
- Fixture replays (`tests/fixtures/replays.json`: three replays covering every race, a leaver, a trade, a CC landing and the 8-worker ruleset); assert player count, duration, known snapshot values. Replays are local only and the tests skip without them.
- Time check: a known event (e.g. first expansion finished) matches the in-game timer to within 1s.
- Data assumptions were verified on 375 replays: see [M0 spike results](../06-roadmap/m0-spike-results.md). Re-run `scripts/spike_m0.py` after a new game patch.
