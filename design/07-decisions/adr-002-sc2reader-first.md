# ADR-002: Start with sc2reader

**Status:** Proposed

## Context
Options: `sc2reader`, Blizzard `s2protocol`, or pysc2 replay re-run.

## Decision
Use `sc2reader` for the MVP (high-level events, stats snapshots). Wrap it behind our `ReplayModel` so it can be swapped.

## Consequences
+ Fast to build; enough for the 5 MVP metrics.
− May lag on new game builds; fall back to `s2protocol` if needed.
− pysc2 deferred: needs a matching game client build.
