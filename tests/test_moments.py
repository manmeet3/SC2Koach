import random

import pytest

from sc2koach.models import (
    Elimination,
    Expansion,
    Finding,
    GameInfo,
    GameRules,
    MetricsBundle,
    NullableScalar,
    Player,
    ReplayModel,
    SupplyBlock,
    Team,
    TeamMetrics,
    Unspent,
)
from sc2koach.moments import detect_all, rank_for_player, rank_team
from sc2koach.moments.ranking import finalize
from sc2koach.thresholds import Thresholds

TH = Thresholds()

EVIDENCE_KEYS = {
    "supply_block": {"est_cost", "duration_s", "supply", "minerals"},
    "high_bank": {"est_cost", "threshold", "peak", "duration_s"},
    "low_workers": {"est_cost", "workers", "threshold", "game_avg", "team_avg", "counterpart"},
    "late_expansion": {
        "est_cost",
        "base",
        "finished",
        "target_s",
        "missing",
        "counterpart_finished",
    },
    "army_collapse": {"est_cost", "army_before", "lost", "killed", "window_s"},
    "early_ally_death": {"est_cost", "departed_player", "how", "played_on_s"},
    "team_army_deficit": {"est_cost", "min_ratio", "duration_s", "peak_gap"},
}


# --------------------------------------------------------------------------- builders


def _replay(*players, duration=900.0):
    """players: (id, team, race, end_t, counterpart_id)."""
    ps = [
        Player(id=pid, team=team, name=f"p{pid}", race=race, end_t=end_t, counterpart_id=cp)
        for pid, team, race, end_t, cp in players
    ]
    teams = sorted({p.team for p in ps})
    return ReplayModel(
        game=GameInfo(
            map="m",
            duration_s=duration,
            end_loop=int(duration * 22.4),
            build=1,
            mode="2v2",
            is_ladder=True,
            replay_sha256="x",
        ),
        rules=GameRules(build=1, ruleset_id="w12-th15"),
        teams=[
            Team(
                id=t,
                result="Unknown",
                composition="".join(sorted(p.race[0] for p in ps if p.team == t)),
                players=[p.id for p in ps if p.team == t],
            )
            for t in teams
        ],
        players=ps,
    )


def _on_time_bases():
    return [
        Expansion(n=1, started=None, finished=0, x=0, y=0, source="start"),
        Expansion(n=2, started=60, finished=100, x=30, y=0, source="built"),
        Expansion(n=3, started=150, finished=200, x=60, y=0, source="built"),
    ]


def _bundle(pid, **kw):
    data = dict(
        player=pid,
        starting_workers=12,
        workers_at_4m=NullableScalar(value=None, reason="no_data"),
        workers=[],
        unspent=Unspent(mean=0, peak=0, seconds_above_threshold=0, series=[]),
        income=[],
        supply_blocks=[],
        expansions=_on_time_bases(),
        army_value=[],
        army_lost=[],
        army_killed=[],
    )
    if "bank" in kw:
        kw["unspent"] = Unspent(mean=0, peak=0, seconds_above_threshold=0, series=kw.pop("bank"))
    if "w4" in kw:
        kw["workers_at_4m"] = NullableScalar(value=kw.pop("w4"))
    data.update(kw)
    return MetricsBundle(**data)


def _solo(race="Terran", end_t=900.0, **kw):
    """One player (id 1, team 1) plus an idle opponent (id 2, team 2)."""
    replay = _replay((1, 1, race, end_t, 2), (2, 2, "Protoss", end_t, 1))
    return replay, [_bundle(1, **kw), _bundle(2)]


def _detect(replay, metrics, team_metrics=(), th=TH):
    return detect_all(replay, metrics, list(team_metrics), th)


def _of(findings, type_):
    return [f for f in findings if f.type == type_]


def _block(start, duration, supply=22, minerals=150):
    return SupplyBlock(
        start=start, end=start + duration, duration_s=duration, supply=supply, minerals=minerals
    )


def _series(start, step, values):
    return [(start + i * step, v) for i, v in enumerate(values)]


# --------------------------------------------------------------------------- baseline


def test_quiet_game_has_no_findings():
    replay, metrics = _solo()
    assert _detect(replay, metrics) == []


# --------------------------------------------------------------------------- supply_block


def test_supply_block_cost_uses_income_at_block_start():
    income = [(0.0, 600.0), (100.0, 1200.0)]
    replay, metrics = _solo(income=income, supply_blocks=[_block(100, 20), _block(50, 20)])
    found = _of(_detect(replay, metrics), "supply_block")
    assert [(f.start, f.evidence["est_cost"]) for f in found] == [(50.0, 200), (100.0, 400)]
    f = found[1]
    assert f.scope == "player" and f.player == 1 and f.team == 1 and f.end == 120.0
    assert f.evidence == {"est_cost": 400, "duration_s": 20, "supply": 22, "minerals": 150}


def test_supply_block_before_first_income_point_costs_zero():
    replay, metrics = _solo(income=[(10.0, 600.0)], supply_blocks=[_block(5, 8)])
    (f,) = _of(_detect(replay, metrics), "supply_block")
    assert f.evidence["est_cost"] == 0


# --------------------------------------------------------------------------- high_bank


def test_high_bank_fires_above_early_threshold():
    bank = _series(90, 10, [0, 801, 1000, 801, 801, 0])  # run 100..130, next point 140
    replay, metrics = _solo(bank=bank)
    (f,) = _of(_detect(replay, metrics), "high_bank")
    assert (f.start, f.end) == (100.0, 140.0)
    # (1 + 200 + 1 + 1) * 10s * 0.05
    assert f.evidence == {"est_cost": 102, "threshold": 800, "peak": 1000, "duration_s": 40}


def test_high_bank_exactly_at_threshold_does_not_count():
    bank = _series(100, 10, [800, 800, 800, 800, 800, 0])
    replay, metrics = _solo(bank=bank)
    assert _of(_detect(replay, metrics), "high_bank") == []


def test_high_bank_min_duration_boundary():
    at_min = _series(100, 10, [900, 900, 900, 0])  # 100 -> 130 = 30s
    below = _series(100, 10, [900, 900, 0])  # 100 -> 120 = 20s
    for bank, expected in ((at_min, 1), (below, 0)):
        replay, metrics = _solo(bank=bank)
        assert len(_of(_detect(replay, metrics), "high_bank")) == expected


def test_high_bank_run_to_end_of_series_uses_last_point():
    bank = _series(100, 10, [900, 900, 900, 900])  # last point 130 -> duration 30
    replay, metrics = _solo(bank=bank)
    (f,) = _of(_detect(replay, metrics), "high_bank")
    assert f.end == 130.0 and f.evidence["duration_s"] == 30
    assert f.evidence["est_cost"] == round(100 * 10 * 0.05 * 3)  # last point has no interval


def test_high_bank_threshold_fixed_by_run_start_at_cutover():
    # Starts at 350 (< 360): early threshold 800 applies for the whole run.
    before = _series(350, 10, [1000, 1000, 1000, 1000, 0])
    # Starts exactly at the cutover: late threshold 1200, 1000 isn't high.
    at = _series(360, 10, [1000, 1000, 1000, 1000, 0])
    replay, metrics = _solo(bank=before)
    (f,) = _of(_detect(replay, metrics), "high_bank")
    assert f.evidence["threshold"] == 800 and f.start == 350.0
    replay, metrics = _solo(bank=at)
    assert _of(_detect(replay, metrics), "high_bank") == []
    replay, metrics = _solo(bank=_series(360, 10, [1300] * 4 + [0]))
    (f,) = _of(_detect(replay, metrics), "high_bank")
    assert f.evidence["threshold"] == 1200


# --------------------------------------------------------------------------- low_workers


@pytest.mark.parametrize(
    "race,starting,workers,fires",
    [
        ("Terran", 12, 22, False),
        ("Terran", 12, 21, True),
        ("Zerg", 12, 19, False),
        ("Zerg", 12, 18, True),
        ("Terran", 8, 20, False),  # 22 - round(0.5 * 4) = 20
        ("Terran", 8, 19, True),
    ],
)
def test_low_workers_threshold_boundaries(race, starting, workers, fires):
    replay, metrics = _solo(race=race, starting_workers=starting, w4=workers)
    assert len(_of(_detect(replay, metrics), "low_workers")) == int(fires)


def test_low_workers_evidence_and_cost():
    replay = _replay(
        (1, 1, "Terran", 900.0, 3),
        (2, 1, "Zerg", 900.0, 4),
        (3, 2, "Protoss", 900.0, 1),
        (4, 2, "Zerg", 900.0, 2),
    )
    metrics = [
        _bundle(1, w4=19, starting_workers=8),
        _bundle(2, w4=30),
        _bundle(3, w4=24),
        _bundle(4),  # no value: skipped and excluded from averages
    ]
    (f,) = _of(_detect(replay, metrics), "low_workers")
    assert (f.player, f.start, f.end) == (1, 240.0, 240.0)
    assert f.evidence == {
        "est_cost": round(1 * 0.9 * 240),
        "workers": 19,
        "threshold": 20,
        "game_avg": round((19 + 30 + 24) / 3, 1),
        "team_avg": 24.5,
        "counterpart": 24,
    }


def test_low_workers_cost_window_capped_by_end_t():
    replay, metrics = _solo(w4=20, end_t=300.0)
    (f,) = _of(_detect(replay, metrics), "low_workers")
    assert f.evidence["est_cost"] == round(2 * 0.9 * 60)
    assert f.evidence["counterpart"] is None


# --------------------------------------------------------------------------- late_expansion


def _bases(second=None, third=None):
    out = [Expansion(n=1, started=None, finished=0, x=0, y=0, source="start")]
    if second is not None:
        out.append(Expansion(n=2, started=second - 70, finished=second, x=30, y=0, source="built"))
    if third is not None:
        out.append(Expansion(n=3, started=third - 70, finished=third, x=60, y=0, source="built"))
    return out


def test_late_expansion_boundary_and_evidence():
    replay, metrics = _solo(expansions=_bases(300, 200))
    assert _of(_detect(replay, metrics), "late_expansion") == []
    replay, metrics = _solo(expansions=_bases(310, 200))
    metrics[1] = _bundle(2, expansions=_bases(250, 400))
    (f,) = _of(_detect(replay, metrics), "late_expansion")
    assert (f.start, f.end) == (300.0, 310.0)
    assert f.evidence == {
        "est_cost": 100,
        "base": 2,
        "finished": 310,
        "target_s": 300,
        "missing": 0,
        "counterpart_finished": 250,
    }


def test_late_expansion_race_specific():
    # 3:10 natural is late for Zerg (3:00) but fine for Terran (5:00).
    replay, metrics = _solo(race="Zerg", expansions=_bases(190, 300))
    (f,) = _of(_detect(replay, metrics), "late_expansion")
    assert f.evidence["target_s"] == 180 and f.evidence["est_cost"] == 100
    replay, metrics = _solo(race="Terran", expansions=_bases(190, 300))
    assert _of(_detect(replay, metrics), "late_expansion") == []


def test_late_expansion_missing_bases_run_to_end_t():
    replay, metrics = _solo(end_t=700.0, expansions=_bases())
    found = _of(_detect(replay, metrics), "late_expansion")
    assert [(f.evidence["base"], f.start, f.end, f.evidence["est_cost"]) for f in found] == [
        (2, 300.0, 700.0, 4000),
        (3, 600.0, 700.0, 1000),
    ]
    assert all(f.evidence["missing"] == 1 and f.evidence["finished"] is None for f in found)


def test_late_expansion_missing_not_flagged_if_player_gone_by_target():
    replay, metrics = _solo(end_t=300.0, expansions=_bases())
    assert _of(_detect(replay, metrics), "late_expansion") == []


# --------------------------------------------------------------------------- army_collapse


def _army(values, lost, killed, start=100.0, step=10.0):
    return dict(
        army_value=_series(start, step, values),
        army_lost=_series(start, step, lost),
        army_killed=_series(start, step, killed),
    )


def test_army_collapse_overlapping_windows_merge():
    kw = _army([2000, 2000, 500, 300, 300], [0, 0, 1500, 1700, 1700], [0, 0, 100, 100, 100])
    replay, metrics = _solo(**kw)
    (f,) = _of(_detect(replay, metrics), "army_collapse")
    # windows 100-130 and 110-140 both qualify with the same lost - killed; earliest kept
    assert (f.start, f.end) == (100.0, 130.0)
    assert f.evidence == {
        "est_cost": 1600,
        "army_before": 2000,
        "lost": 1700,
        "killed": 100,
        "window_s": 30,
    }


def test_army_collapse_frac_boundary_fires():
    kw = _army([2000, 800, 800, 800], [0, 1200, 1200, 1200], [0, 0, 0, 0])
    replay, metrics = _solo(**kw)
    assert len(_of(_detect(replay, metrics), "army_collapse")) == 1


def test_army_collapse_requires_lost_gt_killed():
    kw = _army([2000, 800, 800, 800], [0, 1500, 1500, 1500], [0, 1500, 1500, 1500])
    replay, metrics = _solo(**kw)
    assert _of(_detect(replay, metrics), "army_collapse") == []


def test_army_collapse_requires_min_army():
    kw = _army([999, 0, 0, 0], [0, 999, 999, 999], [0, 0, 0, 0])
    replay, metrics = _solo(**kw)
    assert _of(_detect(replay, metrics), "army_collapse") == []
    kw = _army([1000, 0, 0, 0], [0, 1000, 1000, 1000], [0, 0, 0, 0])
    replay, metrics = _solo(**kw)
    assert len(_of(_detect(replay, metrics), "army_collapse")) == 1


def test_army_collapse_separate_fights_stay_separate():
    values = [2000, 0, 0, 0, 0, 0, 3000, 0, 0, 0]
    lost = [0, 2000, 2000, 2000, 2000, 2000, 2000, 5000, 5000, 5000]
    kw = _army(values, lost, [0] * 10)
    replay, metrics = _solo(**kw)
    found = _of(_detect(replay, metrics), "army_collapse")
    assert [(f.start, f.evidence["est_cost"]) for f in found] == [(100.0, 2000), (160.0, 3000)]


# --------------------------------------------------------------------------- early_ally_death


def _elim(player, departed, played_on, early, left=None, elim=None):
    return Elimination(
        player=player,
        eliminated_at=elim,
        left_at=left,
        departed_at=departed,
        team_played_on_s=played_on,
        early=early,
    )


def test_early_ally_death_only_when_early():
    replay = _replay(
        (1, 1, "Terran", 200.0, 3),
        (2, 1, "Zerg", 300.0, 4),
        (3, 2, "Protoss", 300.0, 1),
        (4, 2, "Zerg", 300.0, 2),
    )
    income = [(100.0, 600.0), (150.0, 1200.0), (200.0, 1800.0)]
    metrics = [_bundle(1, income=income), _bundle(2), _bundle(3), _bundle(4)]
    tms = [
        TeamMetrics(
            team=1,
            army_value=[],
            army_disparity=[],
            eliminations=[_elim(1, 200.0, 100.0, True, left=200.0, elim=250.0)],
        ),
        TeamMetrics(
            team=2,
            army_value=[],
            army_disparity=[],
            eliminations=[_elim(3, 280.0, 20.0, False, elim=280.0)],
        ),
    ]
    (f,) = _of(_detect(replay, metrics, tms), "early_ally_death")
    assert (f.scope, f.team, f.player, f.start, f.end) == ("team", 1, 1, 200.0, 300.0)
    # mean of 1200 and 1800 /min over [140, 200] = 25/s × 100s
    assert f.evidence == {
        "est_cost": 2500,
        "departed_player": 1,
        "how": "left",
        "played_on_s": 100,
    }


def test_early_ally_death_how_eliminated():
    replay = _replay((1, 1, "Terran", 200.0, None), (2, 2, "Zerg", 300.0, None))
    tm = TeamMetrics(
        team=1,
        army_value=[],
        army_disparity=[],
        eliminations=[_elim(1, 200.0, 100.0, True, left=210.0, elim=200.0)],
    )
    (f,) = _of(_detect(replay, [_bundle(1), _bundle(2)], [tm]), "early_ally_death")
    assert f.evidence["how"] == "eliminated" and f.evidence["est_cost"] == 0


# --------------------------------------------------------------------------- team_army_deficit


def _teams(own, enemy, start=100.0, step=10.0):
    return [
        TeamMetrics(
            team=1, army_value=_series(start, step, own), army_disparity=[], eliminations=[]
        ),
        TeamMetrics(
            team=2, army_value=_series(start, step, enemy), army_disparity=[], eliminations=[]
        ),
    ]


def test_team_army_deficit_fires_with_evidence():
    own = [600] * 7 + [2000]
    enemy = [1500] * 7 + [1500]
    replay, metrics = _solo()
    (f,) = _of(_detect(replay, metrics, _teams(own, enemy)), "team_army_deficit")
    assert (f.scope, f.team, f.player, f.start, f.end) == ("team", 1, None, 100.0, 170.0)
    assert f.evidence == {
        "est_cost": round(900 * 10 * 0.01 * 7),
        "min_ratio": 0.4,
        "duration_s": 70,
        "peak_gap": 900,
    }


def test_team_army_deficit_ratio_boundary_counts():
    replay, metrics = _solo()
    found = _of(_detect(replay, metrics, _teams([900] * 8, [1500] * 8)), "team_army_deficit")
    assert len(found) == 1 and found[0].evidence["min_ratio"] == 0.6


def test_team_army_deficit_requires_enemy_min():
    replay, metrics = _solo()
    found = _of(_detect(replay, metrics, _teams([0] * 8, [1499] * 8)), "team_army_deficit")
    assert found == []


def test_team_army_deficit_min_duration():
    replay, metrics = _solo()
    short = _teams([0] * 6 + [2000], [1500] * 7)  # 100 -> 160 = 60s: fires
    shorter = _teams([0] * 5 + [2000], [1500] * 6)  # 50s: doesn't
    assert len(_of(_detect(replay, metrics, short), "team_army_deficit")) == 1
    assert _of(_detect(replay, metrics, shorter), "team_army_deficit") == []


# --------------------------------------------------------------------------- end_t, costs


def test_no_player_finding_starts_after_end_t():
    replay, metrics = _solo(
        end_t=400.0,
        income=[(0.0, 600.0)],
        supply_blocks=[_block(390, 10), _block(401, 10)],
        bank=_series(420, 10, [2000] * 5),
    )
    found = _detect(replay, metrics)
    player_found = [f for f in found if f.scope == "player"]
    assert all(f.start <= 400.0 for f in player_found)
    assert [f.start for f in _of(found, "supply_block")] == [390.0]
    assert _of(found, "high_bank") == []


def _busy_game():
    replay = _replay(
        (1, 1, "Terran", 900.0, 3),
        (2, 1, "Zerg", 500.0, 4),
        (3, 2, "Protoss", 900.0, 1),
        (4, 2, "Zerg", 900.0, 2),
    )
    income = [(0.0, 700.0), (300.0, 1500.0)]
    metrics = [
        _bundle(
            1,
            w4=18,
            income=income,
            supply_blocks=[_block(130, 13.3), _block(500, 25)],
            bank=_series(400, 7.1, [1500] * 6 + [0]),
            expansions=_bases(333, None),
            **_army([3000, 3000, 100, 100], [0, 0, 2900, 2900], [0, 0, 500, 500], start=600),
        ),
        _bundle(2, w4=17, income=income, expansions=_bases(150, 500)),
        _bundle(3, w4=24, supply_blocks=[_block(130, 9)], income=income),
        _bundle(4, w4=25),
    ]
    tms = _teams([300] * 10 + [5000], [2000] * 11, start=650)
    tms[0].eliminations.append(_elim(2, 500.0, 400.0, True, left=500.0))
    return replay, metrics, tms


def test_est_cost_is_int_and_evidence_keys_match_contract():
    replay, metrics, tms = _busy_game()
    found = _detect(replay, metrics, tms)
    assert {f.type for f in found} == set(EVIDENCE_KEYS)
    for f in found:
        assert set(f.evidence) == EVIDENCE_KEYS[f.type], f.type
        assert type(f.evidence["est_cost"]) is int
        Finding.model_validate(f.model_dump())


def test_severity_normalized_to_max_cost():
    replay, metrics, tms = _busy_game()
    found = _detect(replay, metrics, tms)
    top = max(f.evidence["est_cost"] for f in found)
    assert max(f.severity for f in found) == 1.0
    for f in found:
        assert f.severity == round(f.evidence["est_cost"] / top, 4)


def test_severity_zero_when_all_costs_zero():
    replay, metrics = _solo(supply_blocks=[_block(100, 10)])
    (f,) = _detect(replay, metrics)
    assert f.evidence["est_cost"] == 0 and f.severity == 0.0


# --------------------------------------------------------------------------- ids, determinism


def test_ids_follow_start_team_player_type_order():
    replay, metrics, tms = _busy_game()
    found = _detect(replay, metrics, tms)
    assert [f.id for f in found] == [f"f-{i:03d}" for i in range(1, len(found) + 1)]
    keys = [(f.start, f.team, f.player or 0, f.type) for f in found]
    assert keys == sorted(keys)
    # same start (130.0): team 1 before team 2
    at_130 = [(f.team, f.player) for f in found if f.start == 130.0]
    assert at_130 == [(1, 1), (2, 3)]


def test_detect_all_is_deterministic_and_input_order_independent():
    replay, metrics, tms = _busy_game()
    first = _detect(replay, metrics, tms)
    assert _detect(replay, metrics, tms) == first
    shuffled = metrics[:]
    random.Random(7).shuffle(shuffled)
    assert _detect(replay, shuffled, list(reversed(tms))) == first


def test_id_width_grows_past_999():
    fs = [
        Finding(
            id="",
            type="supply_block",
            scope="player",
            team=1,
            player=1,
            start=float(i),
            end=float(i),
            severity=0,
            evidence={"est_cost": i},
        )
        for i in range(1000)
    ]
    out = finalize(fs)
    assert out[0].id == "f-0001" and out[-1].id == "f-1000"


# --------------------------------------------------------------------------- ranking


def test_rank_for_player_sorted_by_cost_then_id():
    replay, metrics, tms = _busy_game()
    found = _detect(replay, metrics, tms)
    ranked = rank_for_player(found, 1, 100)
    assert ranked and all(f.scope == "player" and f.player == 1 for f in ranked)
    assert [(-f.evidence["est_cost"], f.id) for f in ranked] == sorted(
        (-f.evidence["est_cost"], f.id) for f in ranked
    )
    assert len(ranked) == len([f for f in found if f.scope == "player" and f.player == 1])
    assert rank_for_player(found, 1, 3) == ranked[:3]
    assert rank_for_player(found, 99, 3) == []


def test_rank_for_player_ties_broken_by_id():
    replay, metrics = _solo(income=[(0.0, 600.0)], supply_blocks=[_block(200, 10), _block(100, 10)])
    ranked = rank_for_player(_detect(replay, metrics), 1, 5)
    assert [f.id for f in ranked] == ["f-001", "f-002"]


def test_rank_team_only_team_findings_for_team():
    replay, metrics, tms = _busy_game()
    found = _detect(replay, metrics, tms)
    ranked = rank_team(found, 1)
    assert {f.type for f in ranked} == {"early_ally_death", "team_army_deficit"}
    assert all(f.scope == "team" and f.team == 1 for f in ranked)
    costs = [f.evidence["est_cost"] for f in ranked]
    assert costs == sorted(costs, reverse=True)
    assert rank_team(found, 2) == []
