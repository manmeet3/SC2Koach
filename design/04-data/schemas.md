# Schemas (draft)

## ReplayModel (summary)
```json
{
  "game": {"map": "string", "duration_s": 620.5, "build": 12345, "mode": "3v3"},
  "focus_player_id": 1,
  "teams": [{"id": 1, "result": "Win", "composition": "PTZ", "players": [1, 2, 3]},
            {"id": 2, "result": "Loss", "composition": "PPZ", "players": [4, 5, 6]}],
  "players": [{"id": 1, "team": 1, "name": "string", "race": "Terran", "mmr": 4200,
               "lobby_slot": 0, "counterpart_id": 4, "left_at": null, "eliminated_at": null}],
  "snapshots": [{"t": 10.0, "player": 1, "minerals": 120, "gas": 0, "supply_used": 14,
                 "supply_made": 15, "workers": 13, "army_value": 0}],
  "unit_events": [],
  "command_events": []
}
```

## MetricsBundle
```json
{
  "player": 1,
  "workers_at_4m": 42,
  "unspent": {"mean": 480, "peak": 1900, "series": [[10.0, 120]]},
  "supply_blocks": [{"start": 130.0, "end": 155.0, "supply": 22}],
  "expansions": [{"n": 2, "started": 62.0, "finished": 110.0}],
  "army_value": [[10.0, 0]]
}
```

## TeamMetrics
```json
{
  "team": 1,
  "army_value": [[10.0, 0]],
  "army_disparity": [[10.0, 0]],
  "eliminations": [{"player": 2, "eliminated_at": 460.0, "left_at": null, "early": true}]
}
```

## Finding
```json
{
  "id": "f-001",
  "type": "supply_block",
  "player": 1,
  "start": 130.0,
  "end": 155.0,
  "severity": 0.7,
  "evidence": {"duration_s": 25, "supply": 22},
  "benchmark": null
}
```

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
All times in seconds of game time. Schemas will be formalized as pydantic models in `models.py`.
