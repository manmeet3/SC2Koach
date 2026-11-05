# Report Format

```
# <Team A players> vs <Team B players> — <Map> (<2v2|3v3>, <compositions>)
Date · Duration · Result (from the focus player's team; otherwise "Team A won") · Player MMRs (n/a if absent; footnote: arranged teams may share a team rating)

Focus: <focus player> (configurable; "you" wording applies to this player only; "none" → neutral report)

## Team
Team army value vs. enemy (table sampled every 30s), eliminations / early ally deaths, team findings (ranked)

## Summary
Table: headline metrics per player (workers@4:00, avg bank, SQ, # supply blocks / total blocked s, 2nd/3rd base time), focus player first, then teammates, then opponents. Counterpart pairs shown side by side, labeled "nominal (lobby slot)" or "manual".

## Players
### <Player> (Race, team, MMR) — focus player first
Top priorities: top 3 findings by estimated cost, each with time, rendered text, and finding ID.
   (If the LLM stage ran, its coaching for this player replaces this list; finding IDs stay visible.)
Metrics: workers@4:00, bank stats + SQ, supply blocks table, expansions table, army value (sampled every 30s).
Context: same scalars for teammates and the nominal counterpart.

## Key Moments
| Time | Player | Type | Detail | ID |   (all findings, chronological)

## Appendix
Thresholds used, warnings, parser/tool versions, schema version, replay SHA-256.
```

- Timestamps formatted `m:ss`.
- A player with no findings gets "No issues detected by the current rules", not an empty section.
- Players who left or were eliminated show their `end_t`; metrics after that are blank.
- Every coaching item links to finding IDs in the Key Moments table.
