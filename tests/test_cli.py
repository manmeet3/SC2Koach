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


def test_analyze_missing_replay_exits_3(tmp_path):
    result = runner.invoke(app, ["analyze", str(tmp_path / "x.SC2Replay")])
    assert result.exit_code == 3


def test_analyze_bad_config_exits_4(tmp_path):
    cfg = tmp_path / "bad.toml"
    cfg.write_text("[thresholds]\nnot_a_key = 1\n", encoding="utf-8")
    result = runner.invoke(app, ["analyze", str(tmp_path / "x.SC2Replay"), "--config", str(cfg)])
    assert result.exit_code == 4
