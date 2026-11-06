from types import SimpleNamespace as NS

import pytest

from sc2koach.errors import UnsupportedReplayError
from sc2koach.gametime import fmt_mmss, loop_to_seconds
from sc2koach.parser import classify_mode


def _replay(*team_sizes, computers=(), ladder=True, archon=False, seconds=600):
    teams, players, pid = [], [], 1
    for n, size in enumerate(team_sizes, start=1):
        members = []
        for _ in range(size):
            p = NS(pid=pid, is_observer=False, archon_leader_id=0 if archon else None)
            members.append(p)
            players.append(p)
            pid += 1
        teams.append(NS(number=n, players=members))
    return NS(
        teams=teams,
        players=players,
        computers=list(computers),
        is_ladder=ladder,
        frames=int(seconds * 22.4),
    )


@pytest.mark.parametrize("sizes,mode", [((2, 2), "2v2"), ((3, 3), "3v3")])
def test_supported_modes(sizes, mode):
    info = classify_mode(_replay(*sizes))
    assert info.mode == mode
    assert info.warnings == []


def test_4v4_and_non_ladder_warn():
    info = classify_mode(_replay(4, 4, ladder=False))
    assert info.mode == "4v4"
    assert len(info.warnings) == 2


@pytest.mark.parametrize(
    "replay",
    [
        _replay(1, 1),
        _replay(2, 3),
        _replay(1, 1, 1, 1),
        _replay(2, 2, computers=[object()]),
        _replay(2, 2, archon=True),
        _replay(5, 5),
        _replay(3, 3, seconds=45),
    ],
    ids=["1v1", "uneven", "ffa", "ai", "archon", "5v5", "under-60s"],
)
def test_unsupported_modes(replay):
    with pytest.raises(UnsupportedReplayError):
        classify_mode(replay)


def test_time_conversion():
    assert loop_to_seconds(22.4 * 240) == pytest.approx(240.0)
    assert loop_to_seconds(160) == pytest.approx(7.142857, rel=1e-5)
    assert fmt_mmss(130.4) == "2:10"
    assert fmt_mmss(59.6) == "1:00"
