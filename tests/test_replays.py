"""M0: real replays load and expose the identity fields the design relies on."""

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sc2koach.cli import app
from sc2koach.errors import UnsupportedReplayError
from sc2koach.parser import load_replay

pytestmark = pytest.mark.replays
SAMPLE = 10
MANIFEST = json.loads((Path(__file__).parent / "fixtures" / "replays.json").read_text("utf-8"))


@pytest.mark.parametrize("fixture", MANIFEST, ids=[f["file"] for f in MANIFEST])
def test_fixture_replays_present_and_unchanged(fixture, replay_paths):
    path = replay_paths[0].parent / fixture["file"]
    if not path.exists():
        pytest.skip(f"fixture {fixture['file']} not in local replay dir")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == fixture["sha256"]
    replay, mode = load_replay(path)
    assert mode.mode == fixture["mode"]
    assert replay.build == fixture["build"]


def _team_games(paths):
    out = []
    for path in paths:
        try:
            replay, mode = load_replay(path)
        except UnsupportedReplayError:
            continue
        out.append((path, replay, mode))
        if len(out) >= SAMPLE:
            break
    return out


@pytest.fixture(scope="module")
def team_games(replay_paths):
    games = _team_games(replay_paths)
    if not games:
        pytest.skip("no supported team-game replays found")
    return games


def test_team_games_have_identity_fields(team_games):
    for path, replay, mode in team_games:
        assert mode.mode in {"2v2", "3v3", "4v4"}, path.name
        for p in replay.players:
            assert p.toon_handle, f"{path.name}: missing toon handle"
            assert isinstance(p.sid, int), f"{path.name}: missing lobby slot"
            assert p.play_race in {"Terran", "Protoss", "Zerg"}, path.name


def test_info_cli_runs(team_games):
    path = team_games[0][0]
    result = CliRunner().invoke(app, ["info", str(path)])
    assert result.exit_code == 0, result.output
    assert "slot" in result.output
