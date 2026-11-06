from sc2koach.gamedata import supply_table
from sc2koach.models import (
    ExtraSuppliesCast,
    GameInfo,
    GameRules,
    Player,
    PlayerRules,
    ReplayModel,
    Snapshot,
    Team,
    UnitEvent,
)
from sc2koach.supply import compute_drift, rebuild_cap, value_at


def _ev(t, kind, uid, utype, pid=1, **kw):
    return UnitEvent(
        t=t, loop=int(t * 22.4), player=pid, kind=kind, unit_id=uid, unit_type=utype, **kw
    )


def _replay(events, snaps=(), casts=()):
    rules = GameRules(
        build=1,
        ruleset_id="w12-th15",
        overrides={"extra_supplies": 8},
        players={
            1: PlayerRules(
                starting_workers=12, starting_supply=15, supply_table=supply_table("Terran", 15)
            )
        },
    )
    return ReplayModel(
        game=GameInfo(
            map="m",
            duration_s=600,
            end_loop=13440,
            build=1,
            mode="2v2",
            is_ladder=True,
            replay_sha256="x",
        ),
        rules=rules,
        teams=[Team(id=1, result="Win", composition="T", players=[1])],
        players=[Player(id=1, team=1, name="a", race="Terran", end_t=600)],
        snapshots=list(snaps),
        unit_events=list(events),
        extra_supplies=list(casts),
    )


def test_rebuild_cap_born_done_died_and_extra_supplies():
    r = _replay(
        [
            _ev(0, "born", 1, "CommandCenter"),
            _ev(20, "init", 2, "SupplyDepot"),
            _ev(41, "done", 2, "SupplyDepot"),
            _ev(50, "type_change", 1, "OrbitalCommand"),
            _ev(90, "died", 2, "SupplyDepot", killer=2),
        ],
        casts=[ExtraSuppliesCast(t=60, player=1, target_unit_id=2)],
    )
    cap = rebuild_cap(r, 1)
    assert value_at(cap, 0) == 15
    assert value_at(cap, 30) == 15
    assert value_at(cap, 41) == 23
    assert value_at(cap, 60) == 31
    assert value_at(cap, 90) == 15


def test_drift_agreement():
    snaps = [
        Snapshot(
            t=t,
            loop=int(t * 22.4),
            regular=True,
            player=1,
            minerals=0,
            gas=0,
            income_per_min=0,
            supply_used=12,
            supply_made=made,
            workers=12,
            army_value=0,
            army_lost=0,
            army_killed=0,
        )
        for t, made in ((7.14, 15), (50, 23), (100, 30))
    ]
    r = _replay(
        [_ev(0, "born", 1, "CommandCenter")]
        + [_ev(0, "born", 10 + i, "SCV", is_worker=True) for i in range(12)]
        + [_ev(41, "done", 2, "SupplyDepot")],
        snaps,
    )
    d = compute_drift(r)
    assert d["cap_agreement"] == round(2 / 3, 4)
    assert d["cap_agreement_Terran"] == round(2 / 3, 4)
    assert d["cap_agreement_Zerg"] is None
    assert d["worker_agreement"] == 1.0
