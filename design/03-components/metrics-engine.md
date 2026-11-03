# Metrics Engine

**Responsibility:** compute per-player and per-team metrics from `ReplayModel`.

## Design
- Each per-player metric is one function `compute(replay, player) -> MetricResult`, registered in a registry.
- Output is a time series and/or summary scalars, so both charts and findings can use it.
- Race-specific logic lives in separate functions chosen by player race.
- **Player window:** per-player metrics cover `[0, end_t]` with `end_t = min(left_at, eliminated_at, game end)`.
- **Undefined values:** a metric that can't be computed (e.g. workers at 4:00 when the game or player ended earlier) is `null` with a `reason` (`game_ended`, `player_ended`, `no_data`). Rules skip `null` metrics. Nothing is extrapolated.
- **Income rate** (used by several metrics and by ranking costs) = `(minerals_collection_rate + vespene_collection_rate) / 60` resources per second, read from the latest snapshot at or before `t`.

## MVP metrics
| Metric | Definition | Output |
|---|---|---|
| Workers at 4:00 | Event-based count of the player's living worker units (`is_worker`) at t = 240s: born minus died. Snapshot `workers_active_count` is kept as a series and used as a cross-check | scalar + snapshot worker series |
| Unspent resources + SQ | Bank = `minerals_current + vespene_current` per snapshot, trade-adjusted (below). SQ formula below | series, mean, peak, seconds above threshold, SQ |
| Supply blocks | See supply block rule | list of `{start, end, duration_s, supply}` |
| Expansion timings | See expansion detection | list of `{n, started, finished, x, y, source}` |
| Army value curve | `minerals_used_current_army + vespene_used_current_army` per snapshot | series |
| Team army value | Sum of the team members' army value per snapshot time, including members who have left (their units stay on the field under ally control) | series per team + disparity series (team − enemy team) |
| Player elimination | Per player `{eliminated_at, left_at}`; flagged as early ally death if the team kept playing ≥ 60s afterwards (threshold configurable) | list |

Team metrics are computed once per team, outside the per-player registry (`compute_team(replay, team) -> TeamMetricResult`). Team series use only the regular snapshots (game loops that are multiples of 160), which every player shares; the extra leave and game-end snapshots are used only for per-player values.

## Counterpart comparison
Team vs. enemy team is the primary comparison. For each player, MVP scalars are also shown next to teammates' values and the **nominal** counterpart's value (see [configuration](../02-architecture/configuration.md)). This is context only: no rule fires just because a player trails an ally, a counterpart, or the game average.

## Supply block rule
The snapshot `food_used` already includes units in production, since supply is reserved when a unit is queued, as on the in-game counter. So snapshots are the source of truth for *used*. Events only refine *when the block ended*.

1. At each snapshot (t ≤ `end_t`), the player is **blocked** if all of these hold:
   - `food_made < 200`;
   - `food_made − food_used < 1`: a worker, the one unit that's always producible, doesn't fit;
   - the player has a living town hall; and
   - `minerals_current ≥ 50`, so a worker is affordable. Being broke at full supply isn't a block.
2. Consecutive blocked snapshots merge into one block. `start` = first blocked snapshot. The true start lies somewhere in the previous snapshot interval, so the reported duration is a **lower bound**.
3. `end` = the earlier of (a) the first time the event-rebuilt cap gives `cap − food_used ≥ 1`, using `food_used` from the last snapshot, and (b) the next unblocked snapshot.
4. **Event-rebuilt cap:** supply providers (depot, pylon, overlord, town halls) add their supply when they finish and remove it when they die; capped at 200. The cap is reset to the snapshot `food_made` at every snapshot, so drift can't build up.
5. Blocks shorter than `thresholds.supply_block_min_s` (default 7s, one snapshot interval) are dropped. No sub-snapshot precision is claimed for `start`.

## Unspent resources and spending quotient
- **Trades:** a sender's bank already drops when it sends, so sending needs no adjustment. For the receiver, `bank_adj(t) = max(0, bank(t) − received in (t − 20s, t])` (grace window `thresholds.trade_grace_s`). This keeps passed resources from counting as poor macro on either side.
- **Spending quotient** (Kasting's formula): `SQ = 35 × (0.00137 × I − ln(U)) + 240`, where `I` = mean income in resources/minute and `U` = mean `bank_adj` (floored at 1), both over the player's snapshots in `[0, end_t]`. SQ is shown for comparison between players in this tool; it doesn't trigger findings.

## Expansion detection
- **Candidates:** town hall `UnitDoneEvent` (CC, Nexus, Hatchery), at the position from its `UnitInitEvent`; and **landings** of a flying CC/Orbital, at the position of its last `Land` command (see [parser](parser.md)).
- **New base location:** a candidate counts only if it is more than `thresholds.expansion_min_distance` (default 15 game units) from **every location where this player has ever had a finished town hall**, including the start location. Excluded as a result:
  - morphs (Orbital, Planetary Fortress, Lair, Hive), which are `UnitTypeChangeEvent`s and not new town halls;
  - town halls in an existing base (in-base CCs, macro hatcheries);
  - **rebuilds** at a base the player held before. Re-taking a lost base doesn't create a new base number.
- `n` = order of distinct base locations (the main is `n = 1`). `started` = the town hall's `UnitInitEvent` time (for a landing, the time the CC was originally started); `finished` = done or landing time; `source` = `built` | `landed`.

## Testing
- Unit tests per metric with hand-checked values from fixture replays.
- Pure-function tests on synthetic snapshot/event lists for edge cases: blocks at 200, broke at cap, receiver grace window, rebuild at a lost base, CC landing, metrics after `end_t`.
