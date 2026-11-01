# Validation Plan

## Metrics accuracy
- Compare against in-game stats screens / sc2replaystats for a handful of replays.
- Hand-verify supply blocks and expansion times by watching the replay at those timestamps.

## Coaching quality
1. Pick 10 replays.
2. A human coach (or strong player) writes their top 3 priorities per player.
3. Compare to the tool's top 3: count overlap, and flag any advice the human considers wrong.
4. Target: majority overlap, zero fabricated facts.

## Regression
- Keep fixture replays + expected findings JSON; CI fails if findings change unexpectedly.
- LLM stage: check every cited finding ID and timestamp exists in the input.

## Rule
Do not add new metrics until the current set passes validation.
