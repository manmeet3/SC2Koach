# Report Format

```
# <Team A players> vs <Team B players> — <Map> (<2v2|3v3>, <compositions>)
Date · Duration · Result · Player MMRs (if present in the replay)

## Summary
Table: headline metrics per player (workers@4:00, avg bank, # supply blocks, 2nd/3rd base time)

## Coaching            (only if LLM stage ran)
### <Player A>
1. Priority — timestamp — why — drill
...

## Key Moments
| Time | Player | Type | Detail |

## Metrics
### Macro (unspent resources, supply blocks)
### Build (expansion timings)
### Army (value curve table, sampled every 30s)

## Appendix
Thresholds used, parser/tool versions, replay hash.
```

- Timestamps formatted `m:ss`.
- Every coaching item links to finding IDs in the Key Moments table.
