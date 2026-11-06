"""End-to-end pipeline tests: synthetic (runs in CI) and fixture golden files (local only)."""

import json
import os
from pathlib import Path

import pytest
from metrics_helpers import ev, make_replay, pl, rsnap
from typer.testing import CliRunner

from sc2koach.cli import app
from sc2koach.config import Config, FocusConfig, load_config
from sc2koach.models import AnalysisResult
from sc2koach.pipeline import analyze_model, prepare_replay
from sc2koach.report import render_markdown

GOLDEN_DIR = Path(__file__).parent / "golden"  # gitignored: contains player names
MANIFEST = json.loads((Path(__file__).parent / "fixtures" / "replays.json").read_text("utf-8"))


def _synthetic_replay():
    players = [pl(1, 1, "Terran"), pl(2, 1, "Protoss"), pl(3, 2, "Zerg"), pl(4, 2, "Terran")]
    events = [ev(0, "born", 100 + p["id"], "CommandCenter", p["id"]) for p in players]
    snaps = []
    for i in range(0, 85):  # ~10 minutes of regular snapshots
        for p in players:
            kw = dict(
                income_per_min=900.0,
                workers=20,
                minerals=300,
                supply_used=40,
                supply_made=60,
                army_value=1000,
            )
            if p["id"] == 1 and 10 <= i < 16:  # supply blocked ~1:11-1:47 with money
                kw.update(supply_used=30, supply_made=30, minerals=200)
            if p["id"] == 1 and i >= 60:  # banks heavily after ~7:08
                kw.update(minerals=2500)
            snaps.append(rsnap(i, p["id"], **kw))
    return make_replay(players, snaps=snaps, events=events, duration=610)


def test_synthetic_end_to_end():
    config = Config(focus=FocusConfig(name="P1"))
    replay = prepare_replay(_synthetic_replay(), config, pairs=["p1:p4"])
    assert replay.focus_player_id == 1
    assert replay.player(1).counterpart_id == 4
    assert replay.player(1).counterpart_source == "manual"

    result = analyze_model(replay, config)
    types = {(f.type, f.player) for f in result.findings}
    assert ("supply_block", 1) in types
    assert ("high_bank", 1) in types
    assert [f.id for f in result.findings] == [
        f"f-{i:03d}" for i in range(1, len(result.findings) + 1)
    ]
    assert AnalysisResult.model_validate_json(result.model_dump_json(by_alias=True)) == result

    md = render_markdown(result)
    assert "Focus: p1" in md
    assert "You were supply blocked" in md
    assert md == render_markdown(analyze_model(replay, config))


def test_ruleset_threshold_overrides_apply(tmp_path):
    cfg = tmp_path / "c.toml"
    cfg.write_text('[thresholds.rulesets."w12-th15"]\nsupply_block_min_s = 60\n', encoding="utf-8")
    config = load_config(explicit_path=cfg)
    result = analyze_model(prepare_replay(_synthetic_replay(), config), config)
    assert result.generated_with.thresholds["supply_block_min_s"] == 60
    assert not [f for f in result.findings if f.type == "supply_block"]


@pytest.mark.replays
@pytest.mark.parametrize("fixture", MANIFEST, ids=[f["file"] for f in MANIFEST])
def test_fixture_golden(fixture, replay_paths, tmp_path, monkeypatch):
    """Byte-for-byte comparison with stored outputs. The first run records them.

    Set SC2KOACH_UPDATE_GOLDEN=1 to re-record after an intended change.
    """
    path = replay_paths[0].parent / fixture["file"]
    if not path.exists():
        pytest.skip("fixture replay not present")
    monkeypatch.chdir(tmp_path)  # no stray sc2koach.toml from the developer's cwd
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    out = tmp_path / "report.md"
    res = CliRunner().invoke(app, ["analyze", str(path), "-o", str(out), "--focus", "blackSheep"])
    assert res.exit_code == 0, res.output
    md = out.read_bytes()
    js = out.with_suffix(".findings.json").read_bytes()

    key = fixture["sha256"][:16]
    golden_md, golden_js = GOLDEN_DIR / f"{key}.md", GOLDEN_DIR / f"{key}.findings.json"
    if os.environ.get("SC2KOACH_UPDATE_GOLDEN") or not golden_md.exists():
        GOLDEN_DIR.mkdir(exist_ok=True)
        golden_md.write_bytes(md)
        golden_js.write_bytes(js)
        pytest.skip(f"recorded golden files for {fixture['file']}")
    assert md == golden_md.read_bytes()
    assert js == golden_js.read_bytes()
