# Metrics Catalog

Source legend: **S** = stats snapshot (`PlayerStatsEvent`, every ~7.14 real seconds), **E** = unit/upgrade events, **C** = command events, **T** = resource trade/request events. All times are real seconds (in-game clock).

## MVP (Phase 1)
| Metric | Definition | Source |
|---|---|---|
| Workers at 4:00 | Worker count from the last stats snapshot ≤ 4:00 (3:56); event counts overcount Zerg (see [M0](../06-roadmap/m0-spike-results.md)) | S |
| Unspent resources + spending quotient | Minerals + gas banked over time (mean, peak, time above threshold), **adjusted for resources received from allies** (trades and fulfilled requests). SQ (Kasting formula) normalizes bank by income so early and late game are comparable | S + T |
| Supply blocks | Snapshot intervals where a worker doesn't fit under the supply cap (< 200) **and** the player could afford one; end refined by supply-provider events and Extra Supplies casts (see [metrics-engine](../03-components/metrics-engine.md)) | S + E + C |
| Expansion timings | Time each town hall is started/finished (or landed) **at a new base location**; morphs, in-base town halls, macro hatcheries and rebuilds excluded | E + C (Land) |
| Army value curve | Army value (`used_current_army`, minerals + gas) over time per player | S |
| Team army value | Sum of allies' army value vs. enemy team over time; disparity series | S |
| Player elimination / early ally death | Time each player is eliminated (all structures destroyed) or leaves, while their team is still playing | E + leave events |

## Phase 3
| Metric | Definition | Source |
|---|---|---|
| Idle production time | Time production structures sat idle | E |
| Build order | Ordered list of structures/tech/upgrades with timestamps | E |
| APM / EPM | Actions (effective actions) per minute | C |
| Inject / chrono consistency | Gap between casts vs. ideal cadence | C |
| Control group usage | Which groups are used, how often | C |
| Fight outcomes | Army value lost vs. killed per engagement | E |
| Scouting frequency | Scout commands/units near enemy territory over time | C / E |

## Team-mode metrics (Phase 3+)
Team army value and player elimination moved to MVP (see above).

| Metric | Definition | Source |
|---|---|---|
| Contribution share | Player's share of team income/army value | S |
| Attack synchronization | Spread between allies' army movements into a fight | C / E |
| Team fight outcomes | Team army value lost vs. killed per engagement | E |

## Notes
- Metrics that depend on race get race-specific implementations (see [metrics-engine](../03-components/metrics-engine.md)).
- Each metric defines its validation reference in [validation-plan](../06-roadmap/validation-plan.md).
