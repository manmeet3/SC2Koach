from typer.testing import CliRunner

from sc2koach.cli import app

runner = CliRunner()


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "info" in result.output


def test_missing_replay_exits_3(tmp_path):
    result = runner.invoke(app, ["info", str(tmp_path / "nope.SC2Replay")])
    assert result.exit_code == 3


def test_corrupt_replay_exits_3(tmp_path):
    bad = tmp_path / "bad.SC2Replay"
    bad.write_bytes(b"not a replay")
    result = runner.invoke(app, ["info", str(bad)])
    assert result.exit_code == 3


def test_analyze_not_implemented(tmp_path):
    result = runner.invoke(app, ["analyze", str(tmp_path / "x.SC2Replay")])
    assert result.exit_code == 1
