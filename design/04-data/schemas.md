# Schemas (draft)

All times are **real seconds matching the in-game clock** (`game_loop / 22.4`). Schemas are implemented as pydantic v2 models in `models.py`; the JSON below is illustrative.

## AnalysisResult (`<name>.findings.json`)
The single top-level artifact the CLI writes, the report renders from, and the GUI/LLM stages read. `schema_version` is bumped on any breaking change.
```json
{
  "schema_version": 1,
  "tool_version": "0.1.0",
  "generated_with": {"sc2reader": "1.9.0", "thresholds": {}},
  "replay": {"...": "ReplayModel without snapshots/events"},
  "metrics": [{"...": "MetricsBundle"}],
  "team_metrics": [{"...": "TeamMetrics"}],
  "findings": [{"...": "Finding"}],
  "coaching": null,
  "warnings": ["Player 'x' landing at 6:12 has no Land command; not counted as an expansion"]
}
```
`thresholds` holds the effective values used for this run, so results stay reproducible.

## ReplayModel (summary)
```json
{
  "game": {"map": "string", "duration_s": 620.5, "build": 12345, "mode": "3v3",
           "played_at": "2026-10-31T20:15:00Z", "replay_sha256": "hex"},
  "focus_player_id": 1,
  "teams": [{"id": 1, "result": "Win", "composition": "PTZ", "players": [1, 2, 3]},
            {"id": 2, "result": "Loss", "composition": "PPZ", "players": [4, 5, 6]}],
  "players": [{"id": 1, "team": 1, "name": "string", "race": "Terran", "mmr": 4200,
               "lobby_slot": 0, "counterpart_id": 4, "counterpart_source": "slot",
               "toon_handle": "1-S2-1-1234567", "spawn_point": {"x": 128.5, "y": 42.0},
               "starting_workers": 12, "left_at": null, "eliminated_at": null, "end_t": 620.5}],
  "snapshots": [{"t": 7.14, "player": 1, "minerals": 120, "gas": 0, "income_per_min": 600,
                 "supply_used": 14, "supply_made": 15, "workers": 13, "army_value": 0,
                 "army_lost": 0, "army_killed": 0}],
  "unit_events": [{"t": 62.0, "player": 1, "kind": "init", "unit_id": 123, "unit_type": "CommandCenter",
                   "x": 120.0, "y": 60.0}],
  "resource_trades": [{"t": 312.5, "from": 1, "to": 2, "minerals": 200, "gas": 0, "kind": "trade"}],
  "land_commands": [{"t": 300.0, "player": 1, "x": 140.0, "y": 70.0}],
  "extra_supplies": [{"t": 410.0, "player": 1, "target_unit_id": 143917057}]
}
```
`mmr` is `null` when missing (it may be a shared team rating for arranged teams). Composition = races sorted alphabetically by initial. `kind` for unit events: `born | init | done | died | type_change`. Land commands carry no unit id; landings are matched to the player's latest command (see [parser](../03-components/parser.md)).

## MetricsBundle
A nullable scalar is `{"value": null, "reason": "game_ended"}` when it can't be computed (see [metrics-engine](../03-components/metrics-engine.md)).
```json
{
  "player": 1,
  "workers_at_4m": {"value": 42, "reason": null},
  "workers": [[7.14, 12]],
  "unspent": {"mean": 480, "peak": 1900, "sq": 62, "seconds_above_threshold": 35.7,
              "series": [[7.14, 120]]},
  "income": [[7.14, 600]],
  "supply_blocks": [{"start": 130.0, "end": 155.0, "duration_s": 25.0, "supply": 22}],
  "expansions": [{"n": 2, "started": 62.0, "finished": 133.0, "x": 120.0, "y": 60.0, "source": "built"}],
  "army_value": [[7.14, 0]]
}
```

## TeamMetrics
```json
{
  "team": 1,
  "army_value": [[7.14, 0]],
  "army_disparity": [[7.14, 0]],
  "eliminations": [{"player": 2, "eliminated_at": 460.0, "left_at": null, "early": true}]
}
```

## Finding
```json
{
  "id": "f-001",
  "type": "supply_block",
  "scope": "player",
  "team": 1,
  "player": 1,
  "start": 130.0,
  "end": 155.0,
  "severity": 0.7,
  "evidence": {"est_cost": 375, "duration_s": 25, "supply": 22, "minerals": 150},
  "benchmark": null
}
```
Team-scoped findings set `scope: "team"`. `player` is the player concerned (e.g. who left) or `null`.

## Coaching
```json
{
  "player": 1,
  "priorities": [{
    "rank": 1,
    "title": "string",
    "finding_ids": ["f-001"],
    "why": "string",
    "drill": "string"
  }]
}
```
