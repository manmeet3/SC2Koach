# Metrics Engine

**Responsibility:** compute per-player metrics from `ReplayModel`.

## Design
- Each metric = one function `compute(replay, player) -> MetricResult`, registered in a registry.
- Output is a time series and/or summary scalars, so both charts and findings can use it.
- Race-specific logic lives in separate functions chosen by player race.

## MVP metrics
| Metric | Output |
|---|---|
| Workers at 4:00 | scalar + worker-count series |
| Unspent resources + SQ | series, mean, peak, time above threshold, SQ; trade-adjusted |
| Supply blocks | list of `{start, end, duration, supply}` |
| Expansion timings | list of `{n, started, finished}` |
| Army value curve | series per player |
| Team army value | series per team + disparity series (team − enemy team) |
| Player elimination | per player `{eliminated_at, left_at}`; flagged as early ally death if the team kept playing ≥ 60s afterwards (threshold configurable) |

Team metrics are computed once per team, outside the per-player registry (`compute_team(replay, team) -> TeamMetricResult`). Per-player metrics stop at the player's `eliminated_at`/`left_at`.

## Counterpart comparison
Team vs. enemy team is the primary comparison. For each player, MVP scalars are also shown next to teammates' values and the **nominal** counterpart's value (see [configuration](../02-architecture/configuration.md)). This is context only: no rule fires just because a player trails an ally or a counterpart.

## Supply block rule
Supply cap and supply used come from different sources:
- **Cap:** rebuilt exactly from events. Supply structures/units and town halls finishing (+cap) or dying (−cap), capped at 200.
- **Used:** taken from snapshots, interpolated between them, and stepped up at each `UnitBornEvent`. Supply is reserved when a unit is *queued*, which tracker events don't show, so "used" is only accurate to roughly the snapshot interval.

A player is **supply blocked** while both of these hold:
1. `used + smallest producible unit's supply > cap`, ignoring 200/200; and
2. the player's bank ≥ that unit's cost. Being broke at full supply isn't a block.

Duration is reported rounded to the snapshot interval (~7s). Minimum duration: one snapshot interval. No sub-snapshot precision is claimed.

## Resource trades
Resources sent to an ally are counted as *spent* by the sender. Resources received are excluded from the receiver's "banked" penalty for a grace window (default 20s), so passing resources to a teammate doesn't show up as poor macro on either side.

## Expansion detection
A town hall counts as an expansion only if it **finishes at a new base location**: more than a configured distance (default 15 game units) from every existing town hall of that player. Excluded:
- Morphs (Orbital, Planetary Fortress, Lair, Hive) via `UnitTypeChangeEvent`.
- Town halls built in an existing base (in-base CCs, macro hatcheries). A CC built in-base and later **landed** at a new location counts when it lands.

## Testing
- Unit tests per metric with hand-checked values from fixture replays.
