from sc2koach.config import FocusConfig, RosterMember
from sc2koach.identity import (
    apply_pairs,
    default_counterparts,
    resolve_focus,
    resolve_roster,
)
from sc2koach.models import Player, Team


def _p(pid, team, name, slot=None, toon=None, race="Terran", cp=None, src=None):
    return Player(
        id=pid,
        team=team,
        name=name,
        race=race,
        lobby_slot=slot,
        toon_handle=toon,
        counterpart_id=cp,
        counterpart_source=src,
        end_t=600.0,
    )


def _teams(players):
    out = []
    for tid in sorted({p.team for p in players}):
        out.append(
            Team(
                id=tid,
                result="Unknown",
                composition="TTT",
                players=[p.id for p in players if p.team == tid],
            )
        )
    return out


def _codes(warnings):
    return [w.code for w in warnings]


PLAYERS = [
    _p(1, 1, "BlackSheep", slot=0, toon="1-S2-1-100"),
    _p(2, 1, "Buddy", slot=1, toon="1-S2-1-200"),
    _p(3, 2, "Enemy", slot=0, toon="1-S2-1-300"),
    _p(4, 2, "Other", slot=1, toon="1-S2-1-400"),
]


# --------------------------------------------------------------------------- focus


def test_focus_toon_handle_beats_name():
    focus = FocusConfig(name="Buddy", toon_handle="1-S2-1-300")
    assert resolve_focus(PLAYERS, focus) == (3, [])


def test_focus_unmatched_toon_falls_through_to_name():
    focus = FocusConfig(name="buddy", toon_handle="1-S2-1-999")
    assert resolve_focus(PLAYERS, focus) == (2, [])


def test_focus_toon_handle_is_exact():
    players = [_p(1, 1, "a", toon="1-S2-1-ABC"), _p(2, 2, "b")]
    pid, warnings = resolve_focus(players, FocusConfig(name=None, toon_handle="1-s2-1-abc"))
    assert pid is None
    assert _codes(warnings) == ["focus_not_found"]


def test_focus_default_name_case_insensitive():
    assert resolve_focus(PLAYERS, FocusConfig()) == (1, [])


def test_focus_alias_match():
    focus = FocusConfig(name="nobody", aliases=["xx", "OTHER"])
    assert resolve_focus(PLAYERS, focus) == (4, [])


def test_focus_ambiguous_name_does_not_fall_through():
    players = [
        _p(1, 1, "Twin"),
        _p(2, 1, "twin"),
        _p(3, 2, "Alias"),
        _p(4, 2, "x"),
    ]
    pid, warnings = resolve_focus(players, FocusConfig(name="TWIN", aliases=["alias"]))
    assert pid is None
    assert _codes(warnings) == ["focus_ambiguous"]


def test_focus_ambiguous_alias():
    focus = FocusConfig(name=None, aliases=["buddy", "enemy"])
    pid, warnings = resolve_focus(PLAYERS, focus)
    assert pid is None
    assert _codes(warnings) == ["focus_ambiguous"]


def test_focus_not_found_warns():
    pid, warnings = resolve_focus(PLAYERS, FocusConfig(name="ghost", aliases=["spook"]))
    assert pid is None
    assert _codes(warnings) == ["focus_not_found"]
    assert "ghost" in warnings[0].message


def test_focus_nothing_configured_no_warning():
    assert resolve_focus(PLAYERS, FocusConfig(name=None)) == (None, [])


# --------------------------------------------------------------------------- roster


def test_roster_mapping():
    roster = [
        RosterMember(name="blacksheep", toon_handle="1-S2-1-100"),
        RosterMember(name="pal", aliases=["BUDDY"]),
        RosterMember(name="absent"),
    ]
    assert resolve_roster(PLAYERS, roster) == {1: "blacksheep", 2: "pal"}


def test_roster_ambiguous_member_skipped():
    players = [_p(1, 1, "Twin"), _p(2, 2, "twin"), _p(3, 1, "solo")]
    roster = [RosterMember(name="twin"), RosterMember(name="Solo")]
    assert resolve_roster(players, roster) == {3: "Solo"}


# --------------------------------------------------------------------------- pairs


def _paired(players):
    return {p.id: (p.counterpart_id, p.counterpart_source) for p in players}


def _with_defaults():
    return default_counterparts(PLAYERS, _teams(PLAYERS))


def test_apply_pairs_valid_repairs_previous_partners():
    players = _with_defaults()
    assert _paired(players) == {1: (3, "slot"), 2: (4, "slot"), 3: (1, "slot"), 4: (2, "slot")}
    out, warnings = apply_pairs(players, _teams(PLAYERS), [" blacksheep : OTHER "])
    assert warnings == []
    assert _paired(out) == {1: (4, "manual"), 4: (1, "manual"), 2: (None, None), 3: (None, None)}
    # originals untouched
    assert _paired(players)[1] == (3, "slot")
    assert [p.id for p in out] == [1, 2, 3, 4]


def test_apply_pairs_later_pair_restores_partner():
    players = _with_defaults()
    out, warnings = apply_pairs(players, _teams(PLAYERS), ["BlackSheep:Other", "Buddy:Enemy"])
    assert warnings == []
    assert _paired(out) == {
        1: (4, "manual"),
        4: (1, "manual"),
        2: (3, "manual"),
        3: (2, "manual"),
    }


def test_apply_pairs_repairing_unpairs_earlier_manual():
    players = _with_defaults()
    out, _ = apply_pairs(players, _teams(PLAYERS), ["BlackSheep:Other", "Buddy:Other"])
    assert _paired(out) == {1: (None, None), 2: (4, "manual"), 3: (None, None), 4: (2, "manual")}


def test_apply_pairs_same_team():
    players = _with_defaults()
    out, warnings = apply_pairs(players, _teams(PLAYERS), ["BlackSheep:Buddy"])
    assert _codes(warnings) == ["bad_pair"]
    assert "same team" in warnings[0].message
    assert _paired(out) == _paired(players)


def test_apply_pairs_unknown_and_malformed():
    players = _with_defaults()
    pairs = ["BlackSheep:Ghost", "nocolon", ":Enemy", "BlackSheep:", "Buddy:Enemy"]
    out, warnings = apply_pairs(players, _teams(PLAYERS), pairs)
    assert _codes(warnings) == ["bad_pair"] * 4
    assert "Ghost" in warnings[0].message
    assert _paired(out)[2] == (3, "manual")
    assert _paired(out)[1] == (None, None)


def test_apply_pairs_ambiguous_name():
    players = [_p(1, 1, "Twin"), _p(2, 1, "x"), _p(3, 2, "twin"), _p(4, 2, "y")]
    out, warnings = apply_pairs(players, _teams(players), ["twin:y"])
    assert _codes(warnings) == ["bad_pair"]
    assert _paired(out) == _paired(players)


# --------------------------------------------------------------------------- defaults


def test_default_counterparts_by_slot():
    players = [
        _p(1, 1, "a", slot=2),
        _p(2, 1, "b", slot=0),
        _p(3, 1, "c", slot=1),
        _p(4, 2, "d", slot=4),
        _p(5, 2, "e", slot=3),
        _p(6, 2, "f", slot=5),
    ]
    out = default_counterparts(players, _teams(players))
    assert _paired(out) == {
        2: (5, "slot"),
        5: (2, "slot"),
        3: (4, "slot"),
        4: (3, "slot"),
        1: (6, "slot"),
        6: (1, "slot"),
    }
    assert all(p.counterpart_id is None for p in players)


def test_default_counterparts_player_id_fallback():
    players = [
        _p(1, 1, "a", slot=1),
        _p(2, 1, "b", slot=0),
        _p(3, 2, "c", slot=None),
        _p(4, 2, "d", slot=0),
    ]
    out = default_counterparts(players, _teams(players))
    assert _paired(out) == {
        1: (3, "player_id"),
        3: (1, "player_id"),
        2: (4, "player_id"),
        4: (2, "player_id"),
    }


def test_default_counterparts_teams_sorted_by_id():
    players = [_p(1, 2, "a", slot=0), _p(2, 1, "b", slot=0)]
    teams = list(reversed(_teams(players)))
    out = default_counterparts(players, teams)
    assert _paired(out) == {1: (2, "slot"), 2: (1, "slot")}
