# Vision

## Problem
Players (and teams) improve faster with specific, timestamped feedback, but human coaching is scarce and watching replays is slow.

## Solution
sc2Koach ingests a StarCraft II replay and produces a coaching report. It does **not** have an LLM watch the replay. Replays are command logs plus periodic state snapshots, so we:

1. Extract data deterministically.
2. Compute metrics and flag key moments.
3. Give structured findings to an LLM that writes the coaching.

## Users
- **Now:** the author (`blacksheep`, Gold–Platinum, plays Terran/Protoss), analyzing ranked 2v2/3v3 replays locally, output as `.md`. The report covers every player and the team as a whole, so teammates (any race) can use it too.
- **Later:** GUI with history across games; optional team/clan view if a fixed group forms.

## Success criteria
- A report for a 2v2/3v3 replay is generated in under ~30s locally, without LLM.
- Metrics match a trusted reference (e.g., in-game stats, sc2replaystats) within tolerance.
- Coaching advice is judged "what a human coach would say" in most validation cases (see [validation-plan](../06-roadmap/validation-plan.md)).

## Non-goals (for now)
- Real-time / live-game overlay.
- Full game-state replay via the SC2 API (pysc2) — only if snapshot data proves insufficient.
- Cheating/ban detection.
