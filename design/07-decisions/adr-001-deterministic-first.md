# ADR-001: Deterministic analysis first, LLM as narrator

**Status:** Accepted

## Context
Replays are command logs and snapshots; LLMs cannot reliably "watch" them and may hallucinate.

## Decision
Compute all facts deterministically. The LLM receives structured findings only and writes the coaching.

## Consequences
+ Reproducible, testable, cheap to run without an LLM.
+ Hallucinations constrained (citations to finding IDs).
− Coaching quality is bounded by which findings we detect.
