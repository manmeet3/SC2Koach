# LLM Coach

**Responsibility:** convert structured findings into concise coaching. Optional stage.

## Input
Findings JSON (top N per player), game metadata, short history summary. **Never raw events.**

## Output (JSON, then rendered to Markdown)
For every player (not only the focus player), plus a team section with 1–2 joint priorities (e.g. synchronizing attacks). Per player: top 2–3 priorities, each with:
- `priority` and short title
- `timestamp(s)` referencing findings
- `why_it_matters`
- `drill` — a concrete practice task

## Prompt rules
- Only use facts present in the findings; no invented timings.
- Cite finding IDs; the report writer verifies the IDs exist.
- Mention progress vs. history where available.
- Tone: direct, supportive, short.
- Address the focus player as "you"; every other player in the third person, with the same neutral tone (any of them may be the focus in another run).

## Guardrails
- Validate output against schema; retry once on failure.
- If the LLM is unavailable, the report falls back to the deterministic findings list.
- **Anonymization:** real player names and toon handles are replaced with role aliases (`Player 1 (Focus)`, `Player 2 (Teammate)`, `Player 3 (Counterpart)`, etc.) before sending findings to the LLM API. The Report Writer maps aliases back to display names using an alias table.
- **Deterministic caching:** LLM responses are cached locally by `hash(findings_json + prompt_template_version + model_id)`. Rerunning on identical findings returns the cached coaching output, saving API costs and preventing regression flakiness.

## Evaluation
See [validation-plan](../06-roadmap/validation-plan.md).
