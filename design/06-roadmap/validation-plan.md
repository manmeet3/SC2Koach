# Validation Plan

## Metrics accuracy
- Compare against in-game stats screens / sc2replaystats for a handful of replays.
- Hand-verify supply blocks and expansion times by watching the replay at those timestamps.

## Coaching quality
1. Pick 10 replays.
2. For each replay, evaluate the focus player and 1 ally (20 evaluated player profiles total, keeping manual evaluation feasible).
3. A human coach (or strong player) writes their top 3 coaching priorities per player without seeing the tool output.
4. Compare against the tool's top 3 priorities.
   - **Overlap definition:** A priority matches if it identifies the same underlying failure mode / finding type (e.g. supply block timing, mineral bank accumulation, late second base, uncoordinated engagement) within ±30s of game time.
   - **Overlap score:** `matched_priorities / 3` per player.
5. **Pass criteria:**
   - Average overlap ≥ 2 out of 3 priorities (≥67%) across evaluated profiles.
   - Zero fabricated facts or hallucinated timings (verified automatically by ensuring every cited finding ID and timestamp exists in the findings JSON).
   - Zero harmful or contradictory advice as judged by the human coach.

## Regression
- Keep fixture replays + expected findings JSON; CI fails if findings change unexpectedly.
- LLM stage: check every cited finding ID and timestamp exists in the input.

## Rule
Do not add new metrics until the current set passes validation.
