import math

import pytest
from metrics_helpers import ev, land, make_replay, pl, rsnap, rt, snap, trade

from sc2koach.metrics import (
    compute_all,
    expansions,
    spending_quotient,
    supply_blocks,
    team_metrics,
    unresolved_landings,
    unspent,
    workers_at_4m,
)
from sc2koach.thresholds import Thresholds

TH = Thresholds()
MAIN = (30.0, 30.0)


def cc_born(uid=1, pid=1, x=MAIN[0], y=MAIN[1], utype="CommandCenter"):
    return ev(0, "born", uid, utype, pid, x=x, y=y, is_building=True)


# --------------------------------------------------------------------------- workers


def test_workers_at_4m_uses_last_regular_snapshot_before_240s():
    snaps = [rsnap(i, workers=10 + i) for i in range(1, 41)] + [snap(238, workers=99)]
    r = make_replay(snaps=snaps)
    assert rt(33) < 240 < rt(34)
    assert workers_at_4m(r, 1).value == 43
    assert workers_at_4m(r, 1).reason is None


def test_workers_at_4m_game_ended():
    r = make_replay(snaps=[rsnap(i) for i in range(1, 28)], duration=200)
    assert workers_at_4m(r, 1).model_dump() == {"value": None, "reason": "game_ended"}


def test_workers_at_4m_player_ended():
    r = make_replay([pl(1, left_at=200)], snaps=[rsnap(i) for i in range(1, 40)])
    assert workers_at_4m(r, 1).model_dump() == {"value": None, "reason": "player_ended"}


def test_workers_at_4m_no_data():
    assert workers_at_4m(make_replay(), 1).reason == "no_data"


# --------------------------------------------------------------------------- unspent / SQ


def test_receiver_bank_adjusted_within_grace_window_sender_unaffected():
    snaps = [
        snap(105, 2, minerals=100),
        snap(110, 2, minerals=700),
        snap(119.9, 2, minerals=700),
        snap(120, 2, minerals=700),
        snap(110, 1, minerals=300),
    ]
    r = make_replay([pl(1), pl(2)], snaps=snaps, trades=[trade(100, 1, 2, minerals=400, gas=100)])
    recv = [v for _, v in unspent(r, 2, TH).series]
    assert recv == [0, 200, 200, 700]
    assert unspent(r, 1, TH).series == [(110.0, 300.0)]


def test_seconds_above_threshold_early_and_late():
    banks = [(300, 900), (310, 900), (320, 900), (360, 900), (370, 900), (390, 1300), (400, 0)]
    r = make_replay(snaps=[snap(t, minerals=b) for t, b in banks])
    u = unspent(r, 1, TH)
    assert u.seconds_above_threshold == pytest.approx(70)
    assert u.peak == 1300


def test_sq_formula_uses_regular_snapshots():
    snaps = [rsnap(i, minerals=400, gas=100, income_per_min=1000) for i in range(1, 5)]
    snaps.append(snap(rt(4) + 1, minerals=5000, income_per_min=0))
    u = unspent(make_replay(snaps=snaps), 1, TH)
    assert u.mean == 500
    assert u.peak == 5000
    assert u.sq == pytest.approx(35 * (0.00137 * 1000 - math.log(500)) + 240)


def test_sq_floors_unspent_at_one_and_none_without_snapshots():
    assert spending_quotient(1000, 0) == pytest.approx(35 * 1.37 + 240)
    u = unspent(make_replay(), 1, TH)
    assert u.sq is None and u.series == [] and u.mean == 0


# --------------------------------------------------------------------------- supply blocks

BLOCKED = dict(supply_used=23, supply_made=23, minerals=100)


def _block_snaps(blocked, n=10, overrides=None):
    overrides = overrides or {}
    out = []
    for i in range(1, n + 1):
        kw = dict(BLOCKED) if i in blocked else dict(supply_used=20, supply_made=23, minerals=100)
        kw.update(overrides.get(i, {}))
        out.append(rsnap(i, **kw))
    return out


def test_supply_block_basic():
    r = make_replay(snaps=_block_snaps({3, 4, 5}), events=[cc_born()])
    blocks = supply_blocks(r, 1, TH)
    assert len(blocks) == 1
    b = blocks[0]
    assert b.start == rt(3) and b.end == rt(6)
    assert b.duration_s == pytest.approx(rt(6) - rt(3))
    assert b.supply == 23 and b.minerals == 100


def test_supply_block_broke_is_not_a_block():
    snaps = _block_snaps({3, 4, 5}, overrides={i: {"minerals": 40} for i in (3, 4, 5)})
    assert supply_blocks(make_replay(snaps=snaps, events=[cc_born()]), 1, TH) == []


def test_supply_block_not_at_200_cap():
    over = {i: {"supply_used": 200, "supply_made": 200} for i in (3, 4, 5)}
    snaps = _block_snaps({3, 4, 5}, overrides=over)
    assert supply_blocks(make_replay(snaps=snaps, events=[cc_born()]), 1, TH) == []


def test_supply_block_needs_living_town_hall():
    snaps = _block_snaps({3, 4, 5})
    assert supply_blocks(make_replay(snaps=snaps), 1, TH) == []
    died = [cc_born(), ev(rt(2), "died", 1, "CommandCenter", killer=3)]
    assert supply_blocks(make_replay(snaps=snaps, events=died), 1, TH) == []


def _depot_events(done_t):
    return [
        cc_born(),
        ev(done_t - 21, "init", 2, "SupplyDepot", x=40, y=40, is_building=True),
        ev(done_t, "done", 2, "SupplyDepot", is_building=True),
    ]


def test_supply_block_end_refined_by_depot_done():
    snaps = _block_snaps({3, 4}, overrides={5: {"supply_made": 31, "supply_used": 24}})
    r = make_replay(snaps=snaps, events=_depot_events(rt(4) + 3))
    (b,) = supply_blocks(r, 1, TH)
    assert b.start == rt(3)
    assert b.end == pytest.approx(rt(4) + 3)


def test_supply_block_split_when_cap_frees_then_fills_again():
    over = {i: {"supply_made": 31, "supply_used": 31} for i in (4, 5)}
    snaps = _block_snaps({3, 4, 5}, overrides=over)
    r = make_replay(snaps=snaps, events=_depot_events(rt(3) + 1))
    (b,) = supply_blocks(r, 1, TH)  # the 1s block at rt(3) is dropped
    assert b.start == rt(4) and b.end == rt(6) and b.supply == 31


def test_supply_block_drift_fallback_ends_at_next_unblocked_snapshot():
    snaps = _block_snaps({3, 4}, overrides={5: {"supply_made": 31, "supply_used": 24}})
    events = _depot_events(rt(4) + 3)
    low = make_replay(snaps=snaps, events=events, drift={"cap_agreement_Terran": 0.5})
    assert supply_blocks(low, 1, TH)[0].end == rt(5)
    ok = make_replay(snaps=snaps, events=events, drift={"cap_agreement_Terran": None})
    assert supply_blocks(ok, 1, TH)[0].end == pytest.approx(rt(4) + 3)


def test_short_supply_block_dropped():
    snaps = _block_snaps({3}, overrides={4: {"supply_made": 31}})
    r = make_replay(snaps=snaps, events=_depot_events(rt(3) + 3))
    assert supply_blocks(r, 1, TH) == []


def test_supply_blocks_after_end_t_ignored_and_clipped_at_end_t():
    end_t = rt(5) + 1
    snaps = _block_snaps({7, 8})
    r = make_replay([pl(1, left_at=end_t)], snaps=snaps, events=[cc_born()])
    assert supply_blocks(r, 1, TH) == []
    r = make_replay([pl(1, left_at=end_t)], snaps=_block_snaps({4, 5, 6, 7}), events=[cc_born()])
    (b,) = supply_blocks(r, 1, TH)
    assert b.start == rt(4) and b.end == end_t


# --------------------------------------------------------------------------- expansions


def _build(uid, init_t, done_t, x, y, utype="CommandCenter", pid=1):
    return [
        ev(init_t, "init", uid, utype, pid, x=x, y=y, is_building=True),
        ev(done_t, "done", uid, utype, pid, is_building=True),
    ]


def _exp(r, pid=1):
    return [(e.n, e.started, e.finished, e.x, e.y, e.source) for e in expansions(r, pid, TH)]


def test_expansion_start_base_and_natural():
    r = make_replay(events=[cc_born(), *_build(2, 100, 171, 50, 30)])
    assert _exp(r) == [(1, None, 0.0, 30, 30, "start"), (2, 100, 171, 50, 30, "built")]


def test_in_base_town_hall_not_counted_and_blocks_nearby_candidates():
    events = [cc_born(), *_build(2, 100, 171, 40, 30), *_build(3, 200, 271, 52, 30)]
    assert [e[0] for e in _exp(make_replay(events=events))] == [1]
    events = [cc_born(), *_build(2, 100, 171, 35, 32), *_build(3, 200, 271, 55, 30)]
    assert _exp(make_replay(events=events))[1:] == [(2, 200, 271, 55, 30, "built")]


def test_rebuild_at_lost_base_not_counted():
    events = [
        cc_born(),
        *_build(2, 100, 171, 50, 30),
        ev(300, "died", 2, "CommandCenter", killer=3),
        *_build(4, 320, 391, 51, 31),
        *_build(5, 420, 491, 80, 30),
    ]
    assert [(e[0], e[2]) for e in _exp(make_replay(events=events))] == [(1, 0), (2, 171), (3, 491)]


def test_zerg_hatcheries():
    events = [
        cc_born(utype="Hatchery"),
        *_build(2, 60, 131, 52, 30, utype="Hatchery"),
        *_build(3, 140, 211, 33, 33, utype="Hatchery"),  # macro hatch
        ev(250, "type_change", 1, "Lair"),
    ]
    r = make_replay([pl(1, race="Zerg")], events=events)
    assert [(e[0], e[5]) for e in _exp(r)] == [(1, "start"), (2, "built")]


def test_cc_landing_counted_at_land_command_position():
    events = [
        cc_born(),
        *_build(2, 100, 171, 35, 30),
        ev(200, "type_change", 2, "CommandCenterFlying"),
        ev(225, "type_change", 2, "CommandCenter"),
    ]
    lands = [land(150, 90, 90), land(210, 60, 30), land(220, 99, 99, pid=2)]
    r = make_replay([pl(1), pl(2)], events=events, lands=lands)
    assert _exp(r)[1:] == [(2, 100, 225, 60, 30, "landed")]
    assert unresolved_landings(r) == []


def test_start_cc_landing_has_no_started_time():
    events = [
        cc_born(),
        ev(200, "type_change", 1, "CommandCenterFlying"),
        ev(220, "type_change", 1, "CommandCenter"),
    ]
    r = make_replay(events=events, lands=[land(205, 60, 30)])
    assert _exp(r)[1:] == [(2, None, 220, 60, 30, "landed")]


def test_landing_without_land_command_skipped():
    events = [
        cc_born(),
        ev(200, "type_change", 1, "CommandCenterFlying"),
        ev(225, "type_change", 1, "CommandCenter"),
    ]
    lands = [land(230, 60, 30), land(210, 60, 30, pid=2)]
    r = make_replay([pl(1), pl(2)], events=events, lands=lands)
    assert [e[0] for e in _exp(r)] == [1]
    assert unresolved_landings(r) == [(1, 225)]


def test_expansion_after_end_t_ignored():
    r = make_replay([pl(1, left_at=150)], events=[cc_born(), *_build(2, 100, 171, 50, 30)])
    assert [e[0] for e in _exp(r)] == [1]


# --------------------------------------------------------------------------- team


def _team_replay(p2_events):
    players = [pl(1, 1), pl(2, 1, left_at=rt(2)), pl(3, 2), pl(4, 2)]
    army = {1: 2000, 2: 1000, 3: 1500, 4: 1000}
    snaps = [
        rsnap(i, pid, army_value=army[pid])
        for i in range(1, 5)
        for pid in (1, 2, 3, 4)
        if pid != 2 or i <= 2
    ]
    return make_replay(players, snaps=snaps, events=p2_events)


def test_team_army_estimates_leaver_from_event_army_ratio():
    marines = [ev(1, "born", 100 + i, "Marine", 2, minerals=50, is_army=True) for i in range(10)]
    deaths = [ev(rt(3) - 1, "died", 100 + i, "Marine", 2, killer=3) for i in range(4)]
    noise = [
        ev(1, "born", 200, "Marine", 2, minerals=50, is_army=True, hallucinated=True),
        ev(1, "init", 201, "Thor", 2, minerals=300, vespene=200, is_army=True),
        ev(rt(3) - 2, "born", 202, "Marine", 3, minerals=50, is_army=True),
    ]
    tm = team_metrics(_team_replay(marines + deaths + noise), TH)
    t1, t2 = tm
    assert [t for t, _ in t1.army_value] == [rt(i) for i in range(1, 5)]
    assert [v for _, v in t1.army_value] == [3000, 3000, 2600, 2600]
    assert [v for _, v in t2.army_value] == [2500] * 4
    assert [v for _, v in t1.army_disparity] == [500, 500, 100, 100]
    assert [v for _, v in t2.army_disparity] == [-500, -500, -100, -100]


def test_team_army_leaver_with_zero_event_army_counts_zero():
    t1, _ = team_metrics(_team_replay([]), TH)
    assert [v for _, v in t1.army_value] == [3000, 3000, 2000, 2000]


def test_eliminations_early_and_not_early():
    players = [
        pl(1, 1),
        pl(2, 1, left_at=300),
        pl(3, 2),
        pl(4, 2, eliminated_at=580, left_at=590),
    ]
    t1, t2 = team_metrics(make_replay(players), TH)
    (e2,) = t1.eliminations
    assert (e2.player, e2.departed_at, e2.team_played_on_s, e2.early) == (2, 300, 300, True)
    (e4,) = t2.eliminations
    assert (e4.departed_at, e4.left_at, e4.eliminated_at) == (580, 590, 580)
    assert (e4.team_played_on_s, e4.early) == (20, False)


def test_eliminations_whole_team_departs_sorted():
    players = [pl(1, 1, left_at=130), pl(2, 1, left_at=100), pl(3, 2)]
    t1, t2 = team_metrics(make_replay(players), TH)
    assert [(e.player, e.team_played_on_s) for e in t1.eliminations] == [(2, 30), (1, 0)]
    assert t2.eliminations == []


# --------------------------------------------------------------------------- compute_all


def test_compute_all_orders_by_id_and_fills_bundle():
    players = [pl(4, 2), pl(3, 2), pl(2, 1), pl(1, 1)]
    snaps = [
        rsnap(i, pid, army_value=10 * pid, army_lost=i, army_killed=2 * i)
        for i in (1, 2)
        for pid in (1, 2, 3, 4)
    ]
    events = [cc_born(pid, pid, x=30 * pid, y=30) for pid in (1, 2, 3, 4)]
    bundles, teams = compute_all(make_replay(players, snaps=snaps, events=events), TH)
    assert [b.player for b in bundles] == [1, 2, 3, 4]
    assert [t.team for t in teams] == [1, 2]
    b = bundles[2]
    assert b.starting_workers == 12
    assert b.army_value == [(rt(1), 30), (rt(2), 30)]
    assert b.army_lost == [(rt(1), 1), (rt(2), 2)]
    assert b.army_killed == [(rt(1), 2), (rt(2), 4)]
    assert b.workers == [(rt(1), 12), (rt(2), 12)]
    assert b.income == [(rt(1), 0), (rt(2), 0)]
    assert [e.source for e in b.expansions] == ["start"]
    assert teams[0].army_value == [(rt(1), 30), (rt(2), 30)]
