import json
from collections import Counter
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from sc2koach import gamedata
from sc2koach.models import Player, ReplayModel, Snapshot, Team
from sc2koach.parser import build_replay_model
from sc2koach.parser.model_builder import (
    _fallback_rules,
    _rules,
    assign_counterparts,
    composition,
    is_regular,
    iso_utc,
    match_request,
    ruleset_id,
    team_result,
)

MANIFEST = Path(__file__).parent / "fixtures" / "replays.json"
FIXTURES = json.loads(MANIFEST.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- pure helpers


def test_is_regular():
    assert is_regular(1)
    assert is_regular(160)
    assert is_regular(3200)
    assert not is_regular(0 + 161)
    assert not is_regular(23683)


def test_composition_and_result():
    assert composition(["Zerg", "Protoss", "Terran"]) == "PTZ"
    assert composition(["Terran", "Protoss", "Protoss"]) == "PPT"
    assert team_result("Win") == "Win"
    assert team_result(None) == "Unknown"
    assert team_result("Undecided") == "Unknown"


def test_iso_utc():
    assert iso_utc(None) is None
    assert iso_utc(datetime(2026, 10, 31, 20, 15, tzinfo=UTC)) == "2026-10-31T20:15:00Z"
    pst = timezone(timedelta(hours=-8))
    assert iso_utc(datetime(2026, 10, 31, 12, 15, tzinfo=pst)) == "2026-10-31T20:15:00Z"
    assert iso_utc(datetime(2026, 10, 31, 20, 15)) == "2026-10-31T20:15:00Z"


@pytest.mark.parametrize(
    "starts,expected",
    [
        ({1: ("Terran", 12, 15), 2: ("Zerg", 12, 14), 3: ("Protoss", 12, 15)}, "w12-th15"),
        ({1: ("Protoss", 8, 13), 2: ("Zerg", 8, 12)}, "w8-th13"),
        ({1: ("Zerg", 12, 14), 2: ("Zerg", 12, 14)}, "w12-zh6"),
        ({1: ("Zerg", 8, 12), 2: ("Zerg", 8, 12)}, "w8-zh4"),
        ({}, "unknown"),
    ],
)
def test_ruleset_id(starts, expected):
    assert ruleset_id(starts) == expected


def test_resolve_overrides_picks_latest_applicable(monkeypatch):
    assert gamedata.resolve_overrides(98310)["extra_supplies"] == 8
    monkeypatch.setattr(
        gamedata,
        "RULESETS",
        [
            {"min_build": 0, "overrides": {"extra_supplies": 8}},
            {"min_build": 99000, "overrides": {"extra_supplies": 16}},
        ],
    )
    assert gamedata.resolve_overrides(98310) == {"extra_supplies": 8}
    assert gamedata.resolve_overrides(99000) == {"extra_supplies": 16}
    assert gamedata.resolve_overrides(120000) == {"extra_supplies": 16}


def test_fallback_rules_use_observed_start():
    starts = {1: ("Protoss", 8, 13), 2: ("Zerg", 8, 12)}
    terran = _fallback_rules("Terran", starts)
    assert (terran.starting_workers, terran.starting_supply) == (8, 13)
    assert terran.supply_table["CommandCenter"] == 13
    zerg = _fallback_rules("Zerg", starts)
    assert zerg.starting_supply == 12
    assert zerg.supply_table["Hatchery"] == 4
    assert _fallback_rules("Zerg", {}).starting_supply == 14


def _player(pid, team, slot):
    return Player(id=pid, team=team, name=f"p{pid}", race="Terran", lobby_slot=slot, end_t=1)


def test_assign_counterparts_by_slot():
    players = [_player(1, 1, 2), _player(2, 1, 0), _player(3, 2, 4), _player(4, 2, 3)]
    teams = [
        Team(id=1, result="Win", composition="TT", players=[1, 2]),
        Team(id=2, result="Loss", composition="TT", players=[3, 4]),
    ]
    out = {p.id: p for p in assign_counterparts(players, teams)}
    assert out[2].counterpart_id == 4 and out[4].counterpart_id == 2
    assert out[1].counterpart_id == 3 and out[3].counterpart_id == 1
    assert {p.counterpart_source for p in out.values()} == {"slot"}


def test_assign_counterparts_falls_back_to_player_id():
    players = [_player(1, 1, None), _player(2, 1, 0), _player(3, 2, 2), _player(4, 2, 3)]
    teams = [
        Team(id=1, result="Win", composition="TT", players=[1, 2]),
        Team(id=2, result="Loss", composition="TT", players=[3, 4]),
    ]
    out = {p.id: p for p in assign_counterparts(players, teams)}
    assert out[1].counterpart_id == 3 and out[2].counterpart_id == 4
    assert {p.counterpart_source for p in out.values()} == {"player_id"}


def test_match_request():
    requests = [
        {"loop": 10, "player": 1, "minerals": 100, "gas": 0, "open": True},
        {"loop": 20, "player": 2, "minerals": 0, "gas": 50, "open": True},
    ]
    assert match_request(requests, 1, 2, 30) is requests[0]
    assert match_request(requests, 2, 1, 30) is requests[1]
    # requester can't fulfill their own request; falls through to the 0-based reading
    assert match_request(requests, 1, 1, 30) is requests[1]
    assert match_request(requests, 2, 1, 15) is None
    requests[0]["open"] = False
    assert match_request(requests, 1, 2, 30) is None


# --------------------------------------------------------------------------- real replays


@pytest.fixture(scope="module")
def fixture_models(replay_paths) -> dict[str, tuple[dict, ReplayModel, Path]]:
    by_name = {p.name: p for p in replay_paths}
    missing = [fx["file"] for fx in FIXTURES if fx["file"] not in by_name]
    if missing:
        pytest.skip(f"fixture replays missing: {missing}")
    return {
        fx["file"]: (fx, build_replay_model(by_name[fx["file"]]), by_name[fx["file"]])
        for fx in FIXTURES
    }


@pytest.mark.parametrize("name", [fx["file"] for fx in FIXTURES])
def test_fixture_structure(fixture_models, name):
    fx, m, _ = fixture_models[name]
    size = int(fx["mode"][0])
    assert m.game.mode == fx["mode"]
    assert m.game.build == fx["build"]
    assert m.game.replay_sha256 == fx["sha256"]
    assert m.game.duration_s == pytest.approx(fx["duration_s"], abs=0.1)
    assert m.game.end_loop == round(m.game.duration_s * 22.4)
    assert m.game.played_at and m.game.played_at.endswith("Z")
    assert m.game.release and m.game.release.endswith(str(fx["build"]))
    assert m.focus_player_id is None

    assert len(m.players) == 2 * size
    assert len(m.teams) == 2
    assert " vs ".join(t.composition for t in m.teams) == fx["composition"]
    for team in m.teams:
        assert len(team.players) == size
        assert all(m.player(pid).team == team.id for pid in team.players)
    for p in m.players:
        assert p.counterpart_id is not None and p.counterpart_source == "slot"
        assert m.player(p.counterpart_id).counterpart_id == p.id
        assert m.player(p.counterpart_id).team != p.team
        assert p.spawn_point is not None
        assert p.toon_handle
        assert 0 < p.end_t <= m.game.duration_s
        ends = [x for x in (p.left_at, p.eliminated_at) if x is not None]
        assert p.end_t == pytest.approx(min(ends + [m.game.duration_s]))
    if "mid_game_leaver" in fx["tags"]:
        assert any(p.left_at is not None and p.left_at < m.game.duration_s - 10 for p in m.players)


@pytest.mark.parametrize("name", [fx["file"] for fx in FIXTURES])
def test_fixture_snapshots_and_events(fixture_models, name):
    fx, m, _ = fixture_models[name]
    pids = {p.id for p in m.players}
    assert m.snapshots == sorted(m.snapshots, key=lambda s: (s.loop, s.player))
    first_loop = m.snapshots[0].loop
    assert first_loop == 1
    regular_loops = sorted({s.loop for s in m.snapshots if s.regular})
    assert regular_loops[0] == 1
    assert all(b - a == 160 for a, b in zip(regular_loops[1:], regular_loops[2:], strict=False))
    assert all(s.t == pytest.approx(s.loop / 22.4) for s in m.snapshots)
    assert {s.player for s in m.snapshots} == pids
    first = {s.player: s for s in reversed(m.snapshots)}
    assert all(first[pid].loop == 1 for pid in pids)

    loops = [e.loop for e in m.unit_events]
    assert loops == sorted(loops)
    assert {e.player for e in m.unit_events} <= pids
    assert Counter(e.kind for e in m.unit_events).keys() == {
        "born",
        "init",
        "done",
        "died",
        "type_change",
    }
    for e in m.unit_events:
        has_pos = e.kind in ("born", "init", "died")
        assert (e.x is not None) == has_pos
        assert e.killer is None or (e.kind == "died" and e.killer in pids)
    assert all(not e.is_worker for e in m.unit_events if e.unit_type == "MULE")

    if "resource_trade" in fx["tags"]:
        assert m.resource_trades
    for tr in m.resource_trades:
        assert tr.from_player in pids and tr.to in pids and tr.from_player != tr.to
        assert m.player(tr.from_player).team == m.player(tr.to).team
    if "cc_landing" in fx["tags"]:
        assert m.land_commands
    for c in m.extra_supplies:
        assert m.player(c.player).race == "Terran"


@pytest.mark.parametrize("name", [fx["file"] for fx in FIXTURES])
def test_fixture_rules_and_drift(fixture_models, name):
    fx, m, _ = fixture_models[name]
    eight = "ruleset_8_workers" in fx["tags"]
    assert m.rules.build == fx["build"]
    assert m.rules.ruleset_id == ("w8-th13" if eight else "w12-th15")
    assert m.rules.verified_build
    assert m.rules.sc2reader_datapack == "97364"
    assert m.rules.overrides == {"extra_supplies": 8}
    assert set(m.rules.players) == {p.id for p in m.players}
    for p in m.players:
        r = m.rules.players[p.id]
        assert r.starting_workers == (8 if eight else 12)
        hall = 13 if eight else 15
        zerg = (4 if eight else 6) + 8
        assert r.starting_supply == (zerg if p.race == "Zerg" else hall)
    assert not any(w.code == "unverified_build" for w in m.warnings)
    d = m.rules.drift
    races = {p.race for p in m.players}
    for race in races:
        assert d[f"cap_agreement_{race}"] >= 0.95
    assert d["worker_agreement"] >= 0.99


def test_fixture_json_roundtrip_and_determinism(fixture_models):
    fx, m, path = next(iter(fixture_models.values()))
    again = ReplayModel.model_validate_json(m.model_dump_json())
    assert again == m
    assert ReplayModel.model_validate_json(m.model_dump_json(by_alias=True)) == m
    assert build_replay_model(path) == m


def test_unverified_build_warning():
    snap = Snapshot(t=1 / 22.4, loop=1, regular=True, player=1, minerals=50, gas=0,
                    income_per_min=0, supply_used=12, supply_made=15, workers=12,
                    army_value=0, army_lost=0, army_killed=0)  # fmt: skip
    rules, warnings = _rules(99999, "5.0.99.99999", NS(id="97364"), {1: "Terran"}, [snap])
    assert not rules.verified_build
    assert rules.ruleset_id == "w12-th15"
    assert rules.sc2reader_datapack == "97364"
    assert [w.code for w in warnings] == ["unverified_build"]
    assert "99999" in warnings[0].message and "stale" in warnings[0].message
    rules, warnings = _rules(98310, None, None, {1: "Terran"}, [snap])
    assert rules.verified_build and rules.sc2reader_datapack is None and not warnings
