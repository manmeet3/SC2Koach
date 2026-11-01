# LLM Coach

**Responsibility:** convert structured findings into concise coaching. Optional stage.

## Input
Findings JSON (top N per player), game metadata, short history summary. **Never raw events.**

## Output (JSON, then rendered to Markdown)
For every player (not only the user), plus a team section with 1–2 joint priorities (e.g. synchronizing attacks). Per player: top 2–3 priorities, each with:
- `priority` and short title
- `timestamp(s)` referencing findings
- `why_it_matters`
- `drill` — a concrete practice task

## Prompt rules
- Only use facts present in the findings; no invented timings.
- Cite finding IDs; the report writer verifies the IDs exist.
- Mention progress vs. history where available.
- Tone: direct, supportive, short.

## Guardrails
- Validate output against schema; retry once on failure.
- If the LLM is unavailable, the report falls back to the deterministic findings list.

## Evaluation
See [validation-plan](../06-roadmap/validation-plan.md).
