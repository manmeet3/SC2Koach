# ADR-002: Start with sc2reader

**Status:** Accepted

## Context
Options: `sc2reader`, Blizzard `s2protocol`, or pysc2 replay re-run.

## Decision
Use `sc2reader` for the MVP (high-level events, stats snapshots). Wrap it behind our `ReplayModel` so it can be swapped.

## Fallback criterion
If `sc2reader` fails on current ladder patch replays during M0 spike tests (e.g. unhandled game events, missing tracker events, or crash on load), fall back to Blizzard's official `s2protocol` library to populate `ReplayModel`.

## Consequences
+ Fast to build; enough for the MVP metrics and team analytics.
− May lag on new game builds; `s2protocol` fallback path defined.
− pysc2 deferred: needs a matching game client build.
