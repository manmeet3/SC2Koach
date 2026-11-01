# Parser

**Responsibility:** turn a `.SC2Replay` into a normalized `ReplayModel`, isolating the rest of the system from sc2reader.

## Input / Output
- In: replay path
- Out: `ReplayModel` — game metadata, players (name, race, MMR if present, result), time-indexed snapshots, unit/upgrade events, command events

## Details
- Load with `sc2reader.load_replay(path, load_level=4)` (full events needed for commands and unit events).
- Convert game loops to seconds using the replay's speed factor; store all times as seconds (float) of game time.
- Snapshots come from `PlayerStatsEvent` (~every 10s): minerals/gas, income, supply used/made, workers active, army value, etc.
- Unit events: `UnitBornEvent`, `UnitInitEvent`, `UnitDoneEvent`, `UnitDiedEvent`, `UpgradeCompleteEvent`.
- Command events: selection, control-group, ability commands (for APM, injects, chrono).

## Errors
- Unsupported build / corrupt file → `ParseError` with message; CLI exits non-zero.
- Supported: 2v2 and 3v3 (any team size ≥2 per side parses; modes outside 2v2/3v3 warn). 1v1 is out of scope.
- Teams come from `replay.teams`; record team result, leavers, and observers/AI (see Q8).
- **Lobby slot:** record each player's lobby slot. Within each team, order players by slot. The *i*-th player of one team is the counterpart of the *i*-th player of the other team (`counterpart_id`). Verify at M0 that ladder replays give a stable slot order (Q26).
- **Elimination:** record `left_at` (leave event) and `eliminated_at` (last structure destroyed) per player.

## Focus player
- The parser does not filter by focus. It resolves the focus name (`--focus` or config default) to a player id and records it as `focus_player_id`, or `null` if that name isn't in the replay (see Q27).

## Testing
- Fixture replays covering each race matchup; assert player count, duration, known snapshot values.
