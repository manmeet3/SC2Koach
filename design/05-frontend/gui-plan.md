# GUI Plan (Phase 4)

## Principle
The GUI wraps the core library through a thin API. No analysis logic in the front-end.

## Backend
- FastAPI: `POST /replays` (upload → run pipeline), `GET /reports/{id}`, `GET /players/{id}/history`, `GET /team/summary`.
- Jobs run in a background worker; results stored as report JSON + Markdown.

## Views
1. **Upload** — drag/drop replays.
2. **Report** — metrics, timeline of key moments, charts (army value, bank, workers).
3. **History** — per-player trends across games.
4. **Team** — shared weaknesses for a fixed group (e.g., everyone slow to third base). With random teammates, shows the user's results by mode and partner/opponent composition instead.

## Delivery alternatives
- Discord bot: attach replay → bot replies with report summary.

## Open
Front-end framework (React vs. lighter Python UI) — see [outstanding-decisions](../outstanding-decisions.md) Q12.
