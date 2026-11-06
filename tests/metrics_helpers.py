"""Synthetic ReplayModel builders for metric tests."""

from __future__ import annotations

from sc2koach.gamedata import supply_table
from sc2koach.models import (
    GameInfo,
    GameRules,
    LandCommand,
    Player,
    PlayerRules,
    ReplayModel,
    ResourceTrade,
    Snapshot,
    Team,
    UnitEvent,
)

LOOPS_PER_S = 22.4


def rt(i: int) -> float:
    """Time of the i-th regular snapshot (loop 160 * i)."""
    return 160 * i / LOOPS_PER_S


def snap(t: float, pid: int = 1, *, loop: int | None = None, **kw) -> Snapshot:
    loop = round(t * LOOPS_PER_S) if loop is None else loop
    data = dict(
        minerals=0,
        gas=0,
        income_per_min=0.0,
        supply_used=12,
        supply_made=15,
        workers=12,
        army_value=0,
        army_lost=0,
        army_killed=0,
    )
    data.update(kw)
    return Snapshot(
        t=loop / LOOPS_PER_S,
        loop=loop,
        regular=loop == 1 or loop % 160 == 0,
        player=pid,
        **data,
    )


def rsnap(i: int, pid: int = 1, **kw) -> Snapshot:
    return snap(rt(i), pid, loop=160 * i, **kw)


def ev(t: float, kind: str, uid: int, utype: str, pid: int = 1, **kw) -> UnitEvent:
    return UnitEvent(
        t=t, loop=round(t * LOOPS_PER_S), player=pid, kind=kind, unit_id=uid, unit_type=utype, **kw
    )


def pl(pid: int, team: int = 1, race: str = "Terran", **kw) -> dict:
    return dict(id=pid, team=team, race=race, **kw)


def trade(t: float, frm: int, to: int, minerals: int = 0, gas: int = 0) -> ResourceTrade:
    return ResourceTrade(t=t, **{"from": frm}, to=to, minerals=minerals, gas=gas, kind="trade")


def land(t: float, x: float, y: float, pid: int = 1) -> LandCommand:
    return LandCommand(t=t, player=pid, x=x, y=y)


def make_replay(
    players: list[dict] | None = None,
    snaps=(),
    events=(),
    trades=(),
    lands=(),
    duration: float = 600.0,
    drift: dict | None = None,
) -> ReplayModel:
    players = players or [pl(1)]
    built: list[Player] = []
    rules: dict[int, PlayerRules] = {}
    for d in players:
        d = dict(d)
        d.setdefault("name", f"p{d['id']}")
        if "end_t" not in d:
            ends = [x for x in (d.get("left_at"), d.get("eliminated_at")) if x is not None]
            d["end_t"] = min([duration, *ends])
        built.append(Player(**d))
        start = 14 if d["race"] == "Zerg" else 15
        rules[d["id"]] = PlayerRules(
            starting_workers=12, starting_supply=12, supply_table=supply_table(d["race"], start)
        )
    team_ids = sorted({p.team for p in built})
    teams = [
        Team(
            id=tid,
            result="Unknown",
            composition="".join(sorted(p.race[0] for p in built if p.team == tid)),
            players=[p.id for p in built if p.team == tid],
        )
        for tid in team_ids
    ]
    return ReplayModel(
        game=GameInfo(
            map="m",
            duration_s=duration,
            end_loop=round(duration * LOOPS_PER_S),
            build=1,
            mode="2v2",
            is_ladder=True,
            replay_sha256="x",
        ),
        rules=GameRules(
            build=1,
            ruleset_id="w12-th15",
            overrides={"extra_supplies": 8},
            players=rules,
            drift=drift or {},
        ),
        teams=teams,
        players=built,
        snapshots=sorted(snaps, key=lambda s: (s.loop, s.player)),
        unit_events=sorted(events, key=lambda e: e.loop),
        resource_trades=list(trades),
        land_commands=list(lands),
    )
