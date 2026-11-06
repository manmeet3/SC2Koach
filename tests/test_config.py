from pathlib import Path

import pytest

from sc2koach.config import Config, effective_thresholds_dict, load_config
from sc2koach.errors import ConfigError
from sc2koach.thresholds import Thresholds


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    cwd = tmp_path / "work"
    home = tmp_path / "home"
    cwd.mkdir()
    home.mkdir()
    return cwd, home


def _home_file(home: Path) -> Path:
    return home / ".config" / "sc2koach" / "config.toml"


def test_defaults_when_no_files(dirs):
    cwd, home = dirs
    cfg = load_config(cwd=cwd, home=home)
    assert cfg == Config()
    assert cfg.focus.name == "blacksheep"
    assert cfg.focus.toon_handle is None
    assert cfg.focus.aliases == []
    assert cfg.roster == []
    assert cfg.thresholds.low_workers_at_4m == {"Terran": 22, "Protoss": 23, "Zerg": 19}
    assert cfg.report.top_n == 3
    assert cfg.coach.top_n == 5


def test_precedence_defaults_home_cwd_cli(dirs):
    cwd, home = dirs
    _write(
        _home_file(home),
        """
[focus]
name = "homename"
toon_handle = "1-S2-1-111"

[thresholds]
supply_block_min_s = 5
trade_grace_s = 11

[report]
top_n = 7
""",
    )
    _write(
        cwd / "sc2koach.toml",
        """
[focus]
name = "cwdname"

[thresholds]
supply_block_min_s = 6
""",
    )
    cfg = load_config(cli={"focus": {"name": "cliname"}}, cwd=cwd, home=home)
    assert cfg.focus.name == "cliname"  # CLI > cwd
    assert cfg.focus.toon_handle == "1-S2-1-111"  # from home, untouched by cwd
    assert cfg.thresholds.supply_block_min_s == 6  # cwd > home
    assert cfg.thresholds.trade_grace_s == 11  # home > default
    assert cfg.thresholds.high_bank_early == 800  # default
    assert cfg.report.top_n == 7

    cfg2 = load_config(cwd=cwd, home=home)
    assert cfg2.focus.name == "cwdname"


def test_deep_merge_nested_race_dict(dirs):
    cwd, home = dirs
    _write(_home_file(home), "[thresholds.low_workers_at_4m]\nZerg = 17\n")
    _write(cwd / "sc2koach.toml", "[thresholds.low_workers_at_4m]\nTerran = 25\n")
    cfg = load_config(cwd=cwd, home=home)
    assert cfg.thresholds.low_workers_at_4m == {"Terran": 25, "Protoss": 23, "Zerg": 17}
    assert cfg.thresholds.late_2nd_base_s == {"Terran": 300, "Protoss": 270, "Zerg": 180}


def test_explicit_path_replaces_cwd_and_home(dirs, tmp_path):
    cwd, home = dirs
    _write(_home_file(home), "[report]\ntop_n = 9\n")
    _write(cwd / "sc2koach.toml", '[focus]\nname = "cwdname"\n')
    explicit = _write(tmp_path / "custom.toml", "[thresholds]\nsupply_block_min_s = 3\n")
    cfg = load_config(cwd=cwd, home=home, explicit_path=explicit)
    assert cfg.thresholds.supply_block_min_s == 3
    assert cfg.focus.name == "blacksheep"
    assert cfg.report.top_n == 3


def test_explicit_path_still_overridden_by_cli(dirs, tmp_path):
    cwd, home = dirs
    explicit = _write(tmp_path / "custom.toml", '[focus]\nname = "filename"\n')
    cfg = load_config(cli={"focus": {"name": "cli"}}, cwd=cwd, home=home, explicit_path=explicit)
    assert cfg.focus.name == "cli"


def test_missing_explicit_path_errors(dirs, tmp_path):
    cwd, home = dirs
    missing = tmp_path / "nope.toml"
    with pytest.raises(ConfigError, match="nope.toml"):
        load_config(cwd=cwd, home=home, explicit_path=missing)


def test_unknown_top_level_key(dirs):
    cwd, home = dirs
    path = _write(cwd / "sc2koach.toml", "[bogus]\nx = 1\n")
    with pytest.raises(ConfigError) as exc:
        load_config(cwd=cwd, home=home)
    assert str(path) in str(exc.value)
    assert "unknown key 'bogus'" in str(exc.value)
    assert exc.value.exit_code == 4


def test_unknown_threshold_key(dirs):
    cwd, home = dirs
    path = _write(_home_file(home), "[thresholds]\nsuply_block_min_s = 3\n")
    with pytest.raises(ConfigError) as exc:
        load_config(cwd=cwd, home=home)
    assert str(path) in str(exc.value)
    assert "thresholds.suply_block_min_s" in str(exc.value)


def test_unknown_race_key(dirs):
    cwd, home = dirs
    _write(cwd / "sc2koach.toml", "[thresholds.low_workers_at_4m]\nTeran = 20\n")
    with pytest.raises(ConfigError, match="thresholds.low_workers_at_4m.Teran"):
        load_config(cwd=cwd, home=home)


def test_unknown_focus_key(dirs):
    cwd, home = dirs
    _write(cwd / "sc2koach.toml", '[focus]\nnick = "x"\n')
    with pytest.raises(ConfigError, match="focus.nick"):
        load_config(cwd=cwd, home=home)


def test_toml_syntax_error(dirs):
    cwd, home = dirs
    path = _write(cwd / "sc2koach.toml", "[thresholds\nsupply_block_min_s = 3\n")
    with pytest.raises(ConfigError) as exc:
        load_config(cwd=cwd, home=home)
    assert str(path) in str(exc.value)
    assert "TOML syntax error" in str(exc.value)


def test_invalid_type(dirs):
    cwd, home = dirs
    path = _write(cwd / "sc2koach.toml", '[report]\ntop_n = "three"\n')
    with pytest.raises(ConfigError) as exc:
        load_config(cwd=cwd, home=home)
    assert str(path) in str(exc.value)
    assert "report.top_n" in str(exc.value)


def test_invalid_cli_value_names_cli(dirs):
    cwd, home = dirs
    with pytest.raises(ConfigError, match="command-line"):
        load_config(cli={"report": {"top_n": "x"}}, cwd=cwd, home=home)


def test_none_cli_values_ignored(dirs):
    cwd, home = dirs
    _write(
        cwd / "sc2koach.toml",
        '[focus]\nname = "cwdname"\ntoon_handle = "1-S2-1-5"\naliases = ["a1"]\n',
    )
    cfg = load_config(
        cli={"focus": {"name": None, "toon_handle": None, "aliases": []}}, cwd=cwd, home=home
    )
    assert cfg.focus.name == "cwdname"
    assert cfg.focus.toon_handle == "1-S2-1-5"
    assert cfg.focus.aliases == ["a1"]


def test_cli_aliases_replace_config_aliases(dirs):
    cwd, home = dirs
    _write(cwd / "sc2koach.toml", '[focus]\naliases = ["a1", "a2"]\n')
    cfg = load_config(
        cli={"focus": {"name": None, "toon_handle": "1-S2-1-9", "aliases": ["b1"]}},
        cwd=cwd,
        home=home,
    )
    assert cfg.focus.aliases == ["b1"]
    assert cfg.focus.toon_handle == "1-S2-1-9"
    assert cfg.focus.name == "blacksheep"


def test_roster_loaded(dirs):
    cwd, home = dirs
    _write(
        cwd / "sc2koach.toml",
        """
[[roster]]
name = "blacksheep"
toon_handle = "1-S2-1-1234567"
aliases = ["blacksheep2"]

[[roster]]
name = "buddy"
""",
    )
    cfg = load_config(cwd=cwd, home=home)
    assert [m.name for m in cfg.roster] == ["blacksheep", "buddy"]
    assert cfg.roster[0].aliases == ["blacksheep2"]
    assert cfg.roster[1].toon_handle is None


def test_ruleset_overrides(dirs):
    cwd, home = dirs
    _write(
        cwd / "sc2koach.toml",
        """
[thresholds.rulesets.w8-th13]
late_2nd_base_s = { Terran = 320 }
supply_block_min_s = 9
""",
    )
    cfg = load_config(cwd=cwd, home=home)
    assert cfg.thresholds.rulesets == {
        "w8-th13": {"late_2nd_base_s": {"Terran": 320}, "supply_block_min_s": 9}
    }
    th = cfg.thresholds.for_ruleset("w8-th13")
    assert th.late_2nd_base_s == {"Terran": 320, "Protoss": 270, "Zerg": 180}
    assert th.supply_block_min_s == 9
    assert cfg.thresholds.for_ruleset("w12-th15") is cfg.thresholds


def test_ruleset_unknown_key_errors(dirs):
    cwd, home = dirs
    _write(cwd / "sc2koach.toml", "[thresholds.rulesets.w8-th13]\nbogus = 1\n")
    with pytest.raises(ConfigError, match="thresholds.rulesets.w8-th13.bogus"):
        load_config(cwd=cwd, home=home)


def test_ruleset_unknown_race_errors(dirs):
    cwd, home = dirs
    _write(
        cwd / "sc2koach.toml",
        "[thresholds.rulesets.w8-th13]\nlate_2nd_base_s = { Toss = 300 }\n",
    )
    with pytest.raises(ConfigError, match="late_2nd_base_s.Toss"):
        load_config(cwd=cwd, home=home)


def test_effective_thresholds_dict_is_json_friendly():
    import json

    th = Thresholds(rulesets={"w8-th13": {"supply_block_min_s": 9}})
    data = effective_thresholds_dict(th)
    assert data["supply_block_min_s"] == 7
    assert data["low_workers_at_4m"]["Zerg"] == 19
    assert data["rulesets"]["w8-th13"]["supply_block_min_s"] == 9
    assert json.loads(json.dumps(data)) == data
    assert Thresholds.model_validate(data) == th
