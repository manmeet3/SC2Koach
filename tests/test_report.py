"""Tests for the Markdown/JSON report writer (design/DESIGN.md §8)."""

from __future__ import annotations

import json

import pytest

from sc2koach.models import (
    AnalysisResult,
    AnalysisWarning,
    Coaching,
    Elimination,
    Expansion,
    Finding,
    GameInfo,
    GameRules,
    GeneratedWith,
    MetricsBundle,
    NullableScalar,
    Player,
    Priority,
    ReplayHeader,
    SupplyBlock,
    Team,
    TeamMetrics,
    Unspent,
)
from sc2koach.report import finding_text, render_markdown, write_outputs
from sc2koach.report.markdown import NO_ISSUES
from sc2koach.thresholds import Thresholds

DURATION = 830.0
SECTIONS = ["## Team", "## Summary", "## Players", "## Key Moments", "## Appendix"]


def _series(fn, until: float = DURATION, step: float = 10.0) -> list[tuple[float, float]]:
    out, t = [], 0.0
    while t <= until:
        out.append((t, float(fn(t))))
        t += step
    return out


def _metrics(pid: int, *, workers: int | None, blocks=(), expansions=(), end_t=DURATION):
    return MetricsBundle(
        player=pid,
        starting_workers=12,
        workers_at_4m=NullableScalar(
            value=workers, reason=None if workers is not None else "player_ended"
        ),
        workers=_series(lambda t: 12 + t // 20, end_t),
        unspent=Unspent(
            mean=480.4 + pid,
            peak=1900,
            sq=62.4,
            seconds_above_threshold=35.7,
            series=_series(lambda t: 100, end_t),
        ),
        income=_series(lambda t: 600, end_t),
        supply_blocks=list(blocks),
        expansions=list(expansions),
        army_value=_series(lambda t: t * 3 + pid, end_t),
        army_lost=_series(lambda t: 0, end_t),
        army_killed=_series(lambda t: 0, end_t),
    )


def _finding(fid, type_, *, player, team, start, end, est_cost, scope="player", **evidence):
    return Finding(
        id=fid,
        type=type_,
        scope=scope,
        team=team,
        player=player,
        start=start,
        end=end,
        severity=round(est_cost / 5000, 3),
        evidence={"est_cost": est_cost, **evidence},
    )


def _findings() -> list[Finding]:
    return [
        _finding(
            "f-001", "supply_block", player=1, team=1, start=130, end=155, est_cost=375,
            duration_s=25, supply=22, minerals=150,
        ),
        _finding(
            "f-002", "low_workers", player=2, team=1, start=236, end=236, est_cost=650,
            workers=17, threshold=19, game_avg=20.5, team_avg=19.0, counterpart=None,
        ),
        _finding(
            "f-003", "late_expansion", player=1, team=1, start=300, end=340, est_cost=400,
            base=2, finished=340, target_s=300, missing=0, counterpart_finished=290,
        ),
        _finding(
            "f-004", "high_bank", player=3, team=2, start=360, end=395, est_cost=900,
            threshold=1200, peak=1640, duration_s=35,
        ),
        _finding(
            "f-005", "early_ally_death", scope="team", player=2, team=1, start=460, end=830,
            est_cost=5000, departed_player=2, how="left", played_on_s=370,
        ),
        _finding(
            "f-006", "team_army_deficit", scope="team", player=None, team=1, start=480, end=630,
            est_cost=3600, min_ratio=0.35, duration_s=150, peak_gap=2400,
        ),
        _finding(
            "f-007", "army_collapse", player=1, team=1, start=550, end=580, est_cost=1500,
            army_before=2800, lost=2100, killed=600, window_s=30,
        ),
        _finding(
            "f-008", "late_expansion", player=1, team=1, start=600, end=830, est_cost=2300,
            base=3, finished=None, target_s=600, missing=1, counterpart_finished=None,
        ),
        _finding(
            "f-009", "supply_block", player=1, team=1, start=700, end=710, est_cost=100,
            duration_s=10, supply=94, minerals=420,
        ),
    ]  # fmt: skip


def make_result(focus: int | None = 1, coaching: list[Coaching] | None = None) -> AnalysisResult:
    players = [
        Player(
            id=1, team=1, name="Alpha", race="Terran", mmr=4200, lobby_slot=0,
            counterpart_id=3, counterpart_source="slot", end_t=DURATION,
        ),
        Player(
            id=2, team=1, name="blackSheep", race="Zerg", mmr=4200, lobby_slot=1,
            counterpart_id=4, counterpart_source="manual", left_at=460.0, end_t=460.0,
        ),
        Player(
            id=3, team=2, name="Gamma|Δ", race="Protoss", mmr=None, lobby_slot=0,
            counterpart_id=1, counterpart_source="slot", end_t=DURATION,
        ),
        Player(
            id=4, team=2, name="Δelta", race="Terran", mmr=3900, lobby_slot=1,
            counterpart_id=None, end_t=DURATION,
        ),
    ]  # fmt: skip
    replay = ReplayHeader(
        game=GameInfo(
            map="Synthetic Ruins LE",
            duration_s=DURATION,
            end_loop=int(DURATION * 22.4),
            build=98310,
            release="5.0.16.98310",
            mode="2v2",
            is_ladder=True,
            played_at="2026-10-31T20:15:00Z",
            replay_sha256="ab" * 32,
        ),
        rules=GameRules(
            build=98310,
            ruleset_id="w12-th15",
            sc2reader_datapack="97364",
            drift={"cap_agreement": 1.0, "worker_agreement": None},
        ),
        focus_player_id=focus,
        teams=[
            Team(id=1, result="Loss", composition="TZ", players=[1, 2]),
            Team(id=2, result="Win", composition="PT", players=[3, 4]),
        ],
        players=players,
    )
    metrics = [
        _metrics(
            1,
            workers=21,
            blocks=[
                SupplyBlock(start=130, end=155, duration_s=25, supply=22, minerals=150),
                SupplyBlock(start=700, end=710, duration_s=10, supply=94, minerals=420),
            ],
            expansions=[
                Expansion(n=1, started=None, finished=0, x=1, y=1, source="start"),
                Expansion(n=2, started=240, finished=340, x=2, y=2, source="built"),
            ],
        ),
        _metrics(2, workers=17, end_t=460.0),
        _metrics(3, workers=24),
        _metrics(4, workers=None),
    ]
    team_metrics = [
        TeamMetrics(
            team=1,
            army_value=_series(lambda t: t * 2),
            army_disparity=_series(lambda t: -t),
            eliminations=[
                Elimination(
                    player=2,
                    eliminated_at=None,
                    left_at=460.0,
                    departed_at=460.0,
                    team_played_on_s=370.0,
                    early=True,
                )
            ],
        ),
        TeamMetrics(
            team=2,
            army_value=_series(lambda t: t * 3),
            army_disparity=_series(lambda t: t),
            eliminations=[],
        ),
    ]
    return AnalysisResult(
        tool_version="0.1.0",
        generated_with=GeneratedWith(sc2reader="1.9.0", thresholds=Thresholds().model_dump()),
        replay=replay,
        metrics=metrics,
        team_metrics=team_metrics,
        findings=_findings(),
        coaching=coaching,
        warnings=[
            AnalysisWarning(code="unverified_build", message="Build 98310 is unverified"),
            AnalysisWarning(code="focus_ambiguous", message="Two matches", player=2),
        ],
    )


def _by_id(result: AnalysisResult, fid: str) -> Finding:
    return next(f for f in result.findings if f.id == fid)


def _player_block(md: str, heading: str) -> str:
    start = md.index(heading)
    nxt = md.find("\n### ", start + 1)
    nxt_section = md.find("\n## ", start + 1)
    ends = [i for i in (nxt, nxt_section) if i != -1]
    return md[start : min(ends)] if ends else md[start:]


# --------------------------------------------------------------------------- finding_text


def test_finding_text_second_person_only_for_focus():
    r = make_result(focus=1)
    assert finding_text(_by_id(r, "f-001"), r) == (
        "You were supply blocked at 2:10 for at least 25s (22 supply) with 150 minerals banked"
    )
    assert finding_text(_by_id(r, "f-003"), r) == (
        "Your second base finished 5:40 (target 5:00; counterpart finished 4:50)"
    )
    assert finding_text(_by_id(r, "f-007"), r) == (
        "You lost 2,100 of 2,800 army value 9:10–9:40 while killing 600"
    )
    assert finding_text(_by_id(r, "f-008"), r) == "You had no third base by 13:50 (target 10:00)"


def test_finding_text_third_person_for_others():
    r = make_result(focus=1)
    assert finding_text(_by_id(r, "f-004"), r) == (
        "Gamma|Δ banked over 1,200 for 35s from 6:00 (peak 1,640)"
    )
    # counterpart None is omitted
    assert finding_text(_by_id(r, "f-002"), r) == (
        "blackSheep had 17 workers at 4:00 (target 19; game average 20.5; team average 19.0)"
    )
    for fid in ("f-002", "f-004"):
        text = finding_text(_by_id(r, fid), r)
        assert not text.startswith(("You", "Your"))


def test_finding_text_team_findings():
    r = make_result(focus=1)
    assert finding_text(_by_id(r, "f-005"), r) == (
        "Your team played a player down for 6:10 after blackSheep left at 7:40"
    )
    assert finding_text(_by_id(r, "f-006"), r) == (
        "Your team's army value was at or below 60% of the enemy's 8:00–10:30 "
        "(lowest 35%; largest gap 2,400)"
    )
    other = make_result(focus=3)
    assert finding_text(_by_id(other, "f-005"), other).startswith("Team 1 played a player down")
    assert finding_text(_by_id(other, "f-006"), other).startswith("Team 1's army value")
    assert finding_text(_by_id(other, "f-004"), other).startswith("You banked over 1,200")
    assert finding_text(_by_id(other, "f-001"), other).startswith("Alpha was supply blocked")
    leaver = make_result(focus=2)
    assert finding_text(_by_id(leaver, "f-005"), leaver) == (
        "Your team played a player down for 6:10 after you left at 7:40"
    )


@pytest.mark.parametrize(
    "type_",
    [
        "supply_block",
        "high_bank",
        "low_workers",
        "late_expansion",
        "army_collapse",
        "early_ally_death",
        "team_army_deficit",
    ],
)
def test_finding_text_robust_to_none_evidence(type_):
    r = make_result()
    keys = [
        "duration_s", "supply", "minerals", "threshold", "peak", "workers", "game_avg",
        "team_avg", "counterpart", "base", "finished", "target_s", "missing",
        "counterpart_finished", "army_before", "lost", "killed", "window_s",
        "departed_player", "how", "played_on_s", "min_ratio", "peak_gap",
    ]  # fmt: skip
    scope = "team" if type_ in ("early_ally_death", "team_army_deficit") else "player"
    f = Finding(
        id="f-100",
        type=type_,
        scope=scope,
        team=1,
        player=None if type_ == "team_army_deficit" else 1,
        start=61,
        end=95,
        severity=0.1,
        evidence={"est_cost": 10, **dict.fromkeys(keys)},
    )
    text = finding_text(f, r)
    assert text and "None" not in text
    bare = f.model_copy(update={"evidence": {"est_cost": 10}})
    assert finding_text(bare, r)
    r.findings.append(f)
    assert "f-100" in render_markdown(r)


def test_unknown_type_and_missing_cost_render_generic_text():
    r = make_result()
    f = Finding.model_construct(
        id="f-101",
        type="mystery_rule",
        scope="player",
        team=2,
        player=4,
        start=125,
        end=185,
        severity=0.0,
        evidence={"weird": "x"},
        benchmark=None,
    )
    assert finding_text(f, r) == "Δelta: mystery rule 2:05–3:05"
    r.findings.append(f)
    md = render_markdown(r)
    assert "`f-101`" in md
    assert NO_ISSUES not in _player_block(md, "### Δelta")


# --------------------------------------------------------------------------- render_markdown


def test_header_and_section_order():
    md = render_markdown(make_result())
    lines = md.splitlines()
    assert lines[0] == "# Alpha, blackSheep vs Gamma|Δ, Δelta — Synthetic Ruins LE (2v2, TZ vs PT)"
    assert "2026-10-31 · 13:50 · Loss · build 98310 (w12-th15)" in lines
    assert "Focus: Alpha" in lines
    positions = [md.index(f"\n{s}\n") for s in SECTIONS]
    assert positions == sorted(positions)
    assert md.endswith("\n") and not md.endswith("\n\n")


def test_neutral_report_without_focus():
    md = render_markdown(make_result(focus=None))
    assert "Focus: none (neutral report)" in md
    assert "Team 2 won" in md
    assert "You " not in md and "Your " not in md and "you " not in md
    assert "Team 1 played a player down for 6:10 after blackSheep left at 7:40" in md
    assert "Alpha was supply blocked at 2:10" in md
    rows = [ln for ln in md.split("## Summary")[1].split("## Players")[0].splitlines()]
    names = [ln.split("|")[1].strip() for ln in rows if ln.startswith("| ") and "Player" not in ln]
    assert names == ["Alpha", "blackSheep", "Gamma\\", "Δelta"]


def test_summary_and_player_order_focus_first():
    md = render_markdown(make_result(focus=3))
    assert md.splitlines()[0].startswith("# Gamma|Δ, Δelta vs Alpha, blackSheep")
    assert "Win" in md.splitlines()[2]
    summary = md.split("## Summary")[1].split("## Players")[0]
    rows = [ln.split(" | ")[0] for ln in summary.splitlines() if ln.startswith("| ")][1:]
    assert rows == ["| Gamma\\|Δ", "| Δelta", "| Alpha", "| blackSheep"]
    players = md.split("## Players")[1].split("## Key Moments")[0]
    heads = [ln for ln in players.splitlines() if ln.startswith("### ")]
    assert heads == [
        "### Gamma|Δ (Protoss, Team 2, MMR n/a)",
        "### Δelta (Terran, Team 2, MMR 3900)",
        "### Alpha (Terran, Team 1, MMR 4200)",
        "### blackSheep (Zerg, Team 1, MMR 4200)",
    ]


def test_summary_table_contents():
    md = render_markdown(make_result())
    summary = md.split("## Summary")[1].split("## Players")[0]
    assert (
        "| Alpha | Terran | 1 | 4200 | 21 | 481 | 62 | 2 / 35s | 5:40 | — "
        "| Gamma\\|Δ (lobby slot) |" in summary
    )
    assert "| blackSheep | Zerg | 2 |" not in summary  # team column is the team id
    assert "| blackSheep | Zerg | 1 | 4200 | 17 |" in summary
    assert "Δelta (manual)" in summary
    assert "| Δelta | Terran | 2 | 3900 | n/a |" in summary
    assert summary.rstrip().endswith("|") is False
    assert "share a team rating" in summary


def test_top_priorities_ordered_by_cost_and_top_n():
    r = make_result()
    block = _player_block(render_markdown(r), "### Alpha")
    prio = block.split("#### Top priorities")[1].split("#### Metrics")[0]
    assert [ln[:3] for ln in prio.strip().splitlines()] == ["1. ", "2. ", "3. "]
    assert prio.index("`f-008`") < prio.index("`f-007`") < prio.index("`f-003`")
    assert "`f-001`" not in prio and "`f-009`" not in prio
    assert "1. 10:00 — You had no third base by 13:50 (target 10:00) (`f-008`)" in prio

    one = _player_block(render_markdown(r, top_n=1), "### Alpha")
    prio1 = one.split("#### Top priorities")[1].split("#### Metrics")[0]
    assert "`f-008`" in prio1 and "`f-007`" not in prio1


def test_no_issues_and_departure_note():
    md = render_markdown(make_result())
    delta = _player_block(md, "### Δelta")
    assert NO_ISSUES in delta
    assert "Nominal counterpart" not in delta
    sheep = _player_block(md, "### blackSheep")
    assert "Left at 7:40." in sheep
    assert "Workers at 4:00: 17" in sheep
    army = next(ln for ln in sheep.splitlines() if ln.startswith("Army value"))
    assert army.endswith("7:30 1,352")  # stops at the player's end_t (7:40)
    assert "8:00" not in army
    gamma = _player_block(md, "### Gamma|Δ")
    assert "1. 6:00 — Gamma|Δ banked over 1,200 for 35s from 6:00 (peak 1,640) (`f-004`)" in gamma


def test_player_metrics_tables():
    md = render_markdown(make_result())
    alpha = _player_block(md, "### Alpha")
    assert "| Start | Duration | Supply | Minerals |" in alpha
    assert "| 2:10 | 25s | 22 | 150 |" in alpha
    assert "| 11:40 | 10s | 94 | 420 |" in alpha
    assert "| Base | Started | Finished | Source |" in alpha
    assert "| 1 | — | 0:00 | start |" in alpha
    assert "| 2 | 4:00 | 5:40 | built |" in alpha
    assert "- Bank: mean 481, peak 1,900, SQ 62" in alpha
    assert "Army value (every 30s): 0:00 1 · 0:30 91 · 1:00 181" in alpha
    delta = _player_block(md, "### Δelta")
    assert "Workers at 4:00: n/a (player ended)" in delta
    assert "Supply blocks: none" in delta


def test_team_section():
    md = render_markdown(make_result())
    team = md.split("\n## Team\n")[1].split("## Summary")[0]
    assert "| Time | Team 1 | Team 2 | Gap |" in team
    assert "| 0:00 | 0 | 0 | 0 |" in team
    assert "| 1:00 | 120 | 180 | -60 |" in team
    assert "| 13:30 | 1,620 | 2,430 | -810 |" in team
    assert "- blackSheep (Team 1) left at 7:40; the team played on for 6:10 (early)" in team
    findings = team.split("### Team findings")[1]
    assert findings.index("`f-005`") < findings.index("`f-006`")
    assert "1. 7:40 — Your team played a player down for 6:10" in findings


def test_key_moments_chronological_with_team_label():
    md = render_markdown(make_result())
    km = md.split("## Key Moments")[1].split("## Appendix")[0]
    rows = [ln for ln in km.splitlines() if ln.startswith("| ") and "`f-" in ln]
    assert [r.split("`")[-2] for r in rows] == [f"f-{i:03d}" for i in range(1, 10)]
    assert rows[0].startswith("| 2:10 | Alpha | `supply_block` | You were supply blocked")
    assert rows[3].startswith("| 6:00 | Gamma\\|Δ | `high_bank` | Gamma\\|Δ banked")
    assert rows[4].startswith("| 7:40 | Team 1 | `early_ally_death` |")
    assert rows[5].startswith("| 8:00 | Team 1 | `team_army_deficit` |")


def test_appendix():
    md = render_markdown(make_result())
    app = md.split("## Appendix")[1]
    lines = app.splitlines()
    thresholds = [ln for ln in lines if ln.startswith("- `") and ln.count("`") == 2][:3]
    assert thresholds[0] == "- `army_collapse_frac`: 0.6"
    assert "- `low_workers_at_4m.Protoss`: 23" in lines
    assert "- `rulesets`: {}" in lines
    keys = [
        ln.split("`")[1]
        for ln in app.split("### Thresholds")[1].split("### Warnings")[0].splitlines()
        if ln.startswith("- `")
    ]
    assert keys == sorted(keys)
    assert "- `unverified_build`: Build 98310 is unverified" in lines
    assert "- `focus_ambiguous`: Two matches (blackSheep)" in lines
    assert "- Tool version: 0.1.0" in lines
    assert "- sc2reader: 1.9.0" in lines
    assert "- Schema version: 1" in lines
    assert f"- Replay SHA-256: `{'ab' * 32}`" in lines
    assert "- `cap_agreement`: 1.000" in lines
    assert "- `worker_agreement`: n/a" in lines


def test_coaching_replaces_top_priorities():
    coaching = [
        Coaching(
            player=1,
            priorities=[
                Priority(
                    rank=2, title="Build depots ahead", finding_ids=["f-001"],
                    why="Blocks cost you units.", drill="Depot at 14 and 19 supply.",
                ),
                Priority(
                    rank=1, title="Take your third", finding_ids=["f-008", "f-003"],
                    why="You stayed on two bases.", drill="Third CC by 9:00.",
                ),
            ],
        )
    ]  # fmt: skip
    md = render_markdown(make_result(coaching=coaching))
    alpha = _player_block(md, "### Alpha")
    prio = alpha.split("#### Top priorities")[1].split("#### Metrics")[0]
    assert "1. **Take your third** (`f-008`, `f-003`)" in prio
    assert "   - Why: You stayed on two bases." in prio
    assert "   - Drill: Third CC by 9:00." in prio
    assert "2. **Build depots ahead** (`f-001`)" in prio
    assert "`f-007`" not in prio
    # players without coaching keep finding-based priorities
    assert "`f-004`" in _player_block(md, "### Gamma|Δ")


# --------------------------------------------------------------------------- outputs


def test_render_is_byte_stable():
    assert render_markdown(make_result()) == render_markdown(make_result())


def test_write_outputs(tmp_path):
    result = make_result()
    md_path, json_path = write_outputs(result, tmp_path / "a" / "report.md")
    assert md_path == tmp_path / "a" / "report.md"
    assert json_path == tmp_path / "a" / "report.findings.json"
    md_bytes, json_bytes = md_path.read_bytes(), json_path.read_bytes()
    assert b"\r\n" not in md_bytes and b"\r\n" not in json_bytes
    assert md_bytes.decode("utf-8") == render_markdown(result)
    text = json_bytes.decode("utf-8")
    data = json.loads(text)
    assert text == json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    assert "Δelta" in text  # ensure_ascii=False
    assert data == result.model_dump(mode="json", by_alias=True)
    assert AnalysisResult.model_validate(data) == result

    md2, json2 = write_outputs(make_result(), tmp_path / "b" / "report.md")
    assert md2.read_bytes() == md_bytes
    assert json2.read_bytes() == json_bytes


def test_write_outputs_top_n(tmp_path):
    md_path, _ = write_outputs(make_result(), tmp_path / "game.md", top_n=1)
    alpha = _player_block(md_path.read_text(encoding="utf-8"), "### Alpha")
    assert "`f-007`" not in alpha.split("#### Metrics")[0]
