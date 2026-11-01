# Metrics Catalog

Source legend: **S** = stats snapshot (`PlayerStatsEvent`, ~every 10s), **E** = unit/upgrade events, **C** = command events.

## MVP (Phase 1)
| Metric | Definition | Source |
|---|---|---|
| Workers at 4:00 | Worker count at the 4:00 mark (nearest snapshot or event reconstruction) | S / E |
| Unspent resources | Minerals + gas banked over time; average and peak, especially above a threshold | S |
| Supply blocks | Intervals where supply used ≈ supply cap while production was possible; start, end, duration | S + E |
| Expansion timings | Time each town hall is started/finished | E |
| Army value curve | Army value over time per player | S |
| Team army value | Sum of allies' army value vs. enemy team over time; disparity series | S |
| Player elimination / early ally death | Time each player is eliminated (all structures destroyed) or leaves, while their team is still playing | E + leave events |

## Phase 3
| Metric | Definition | Source |
|---|---|---|
| Spending quotient | Efficiency of income vs. spending (SQ) | S |
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
