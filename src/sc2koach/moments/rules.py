"""Finding detection rules (design/DESIGN.md §7).

Each rule is a pure function `(replay, metrics, team_metrics, th) -> list[Finding]`. Rules
emit findings with an empty id and zero severity; `ranking.finalize` assigns both.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Callable, Sequence

from sc2koach.models import (
    Finding,
    FindingType,
    MetricsBundle,
    ReplayModel,
    Series,
    TeamMetrics,
)
from sc2koach.thresholds import Thresholds

Rule = Callable[[ReplayModel, list[MetricsBundle], list[TeamMetrics], Thresholds], list[Finding]]


# --------------------------------------------------------------------------- helpers


def _finding(
    type_: FindingType,
    scope: str,
    team: int,
    player: int | None,
    start: float,
    end: float,
    evidence: dict,
) -> Finding:
    return Finding(
        id="",
        type=type_,
        scope=scope,
        team=team,
        player=player,
        start=float(start),
        end=float(end),
        severity=0.0,
        evidence=evidence,
    )


def _value_at(series: Sequence[Sequence[float]], t: float, default: float = 0.0) -> float:
    """Value of the latest point at or before `t` (series sorted by t)."""
    idx = bisect_right([p[0] for p in series], t) - 1
    return float(series[idx][1]) if idx >= 0 else default


def income_rate_at(income: Series, t: float) -> float:
    """Income in resources/s from the latest income point at or before `t`."""
    return _value_at(income, t) / 60.0


def _num(x: float) -> int | float:
    """Int when integral, else rounded to 1 decimal."""
    r = round(float(x), 1)
    return int(r) if r == int(r) else r


def _runs(flags: Sequence[bool]) -> list[tuple[int, int]]:
    """Maximal [first, last] index runs where the flag is True."""
    runs: list[tuple[int, int]] = []
    first: int | None = None
    for i, flag in enumerate(flags):
        if flag and first is None:
            first = i
        elif not flag and first is not None:
            runs.append((first, i - 1))
            first = None
    if first is not None:
        runs.append((first, len(flags) - 1))
    return runs


def _run_end(times: Sequence[float], last: int) -> float:
    """Time of the first point after the run, or the run's last point time if none."""
    return times[last + 1] if last + 1 < len(times) else times[last]


def _interval(times: Sequence[float], i: int) -> float:
    return times[i + 1] - times[i] if i + 1 < len(times) else 0.0


def _bundles(metrics: list[MetricsBundle]) -> dict[int, MetricsBundle]:
    return {m.player: m for m in metrics}


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


# --------------------------------------------------------------------------- player rules


def supply_block(replay, metrics, team_metrics, th) -> list[Finding]:
    out = []
    for m in metrics:
        p = replay.player(m.player)
        for b in m.supply_blocks:
            cost = round(b.duration_s * income_rate_at(m.income, b.start))
            evidence = {
                "est_cost": int(cost),
                "duration_s": _num(b.duration_s),
                "supply": _num(b.supply),
                "minerals": int(b.minerals),
            }
            out.append(_finding("supply_block", "player", p.team, p.id, b.start, b.end, evidence))
    return out


def high_bank(replay, metrics, team_metrics, th) -> list[Finding]:
    out = []
    for m in metrics:
        p = replay.player(m.player)
        times = [float(pt[0]) for pt in m.unspent.series]
        banks = [float(pt[1]) for pt in m.unspent.series]
        n = len(times)
        i = 0
        while i < n:
            # The threshold is fixed by the run's start time, so runs are scanned explicitly.
            thr = th.high_bank_early if times[i] < th.high_bank_cutover_s else th.high_bank_late
            if banks[i] <= thr:
                i += 1
                continue
            last = i
            while last + 1 < n and banks[last + 1] > thr:
                last += 1
            start = times[i]
            end = _run_end(times, last)
            duration = end - start
            if duration >= th.high_bank_min_s:
                excess = sum(
                    (banks[k] - thr) * _interval(times, k) * th.bank_opportunity_factor
                    for k in range(i, last + 1)
                )
                evidence = {
                    "est_cost": int(round(excess)),
                    "threshold": int(thr),
                    "peak": int(round(max(banks[i : last + 1]))),
                    "duration_s": _num(duration),
                }
                out.append(_finding("high_bank", "player", p.team, p.id, start, end, evidence))
            i = last + 1
    return out


def low_workers(replay, metrics, team_metrics, th) -> list[Finding]:
    known = {
        m.player: float(m.workers_at_4m.value) for m in metrics if m.workers_at_4m.value is not None
    }
    game_avg = _avg(list(known.values()))
    out = []
    for m in metrics:
        workers = m.workers_at_4m.value
        if workers is None:
            continue
        p = replay.player(m.player)
        threshold = th.low_workers_threshold(p.race, m.starting_workers)
        if workers >= threshold:
            continue
        deficit = threshold - workers
        cost = round(deficit * th.worker_income_per_s * max(0.0, min(p.end_t, 480.0) - 240.0))
        team_avg = _avg([v for pid, v in known.items() if replay.player(pid).team == p.team])
        counterpart = known.get(p.counterpart_id) if p.counterpart_id is not None else None
        evidence = {
            "est_cost": int(cost),
            "workers": _num(workers),
            "threshold": int(threshold),
            "game_avg": game_avg,
            "team_avg": team_avg,
            "counterpart": _num(counterpart) if counterpart is not None else None,
        }
        out.append(_finding("low_workers", "player", p.team, p.id, 240.0, 240.0, evidence))
    return out


def _base_finished(m: MetricsBundle | None, n: int) -> float | None:
    if m is None:
        return None
    return next((e.finished for e in m.expansions if e.n == n), None)


def late_expansion(replay, metrics, team_metrics, th) -> list[Finding]:
    by_player = _bundles(metrics)
    out = []
    for m in metrics:
        p = replay.player(m.player)
        cp = by_player.get(p.counterpart_id) if p.counterpart_id is not None else None
        for n, targets in ((2, th.late_2nd_base_s), (3, th.late_3rd_base_s)):
            target = float(targets[p.race])
            finished = _base_finished(m, n)
            cp_finished = _base_finished(cp, n)
            if finished is not None:
                if finished <= target:
                    continue
                end, missing = finished, 0
            else:
                if p.end_t <= target:
                    continue
                end, missing = p.end_t, 1
            evidence = {
                "est_cost": int(round((end - target) * th.base_income_per_s)),
                "base": n,
                "finished": _num(finished) if finished is not None else None,
                "target_s": _num(target),
                "missing": missing,
                "counterpart_finished": _num(cp_finished) if cp_finished is not None else None,
            }
            out.append(_finding("late_expansion", "player", p.team, p.id, target, end, evidence))
    return out


Window = tuple[float, float, float, float, float]  # start, end, lost, killed, army_before


def army_collapse(replay, metrics, team_metrics, th) -> list[Finding]:
    out = []
    for m in metrics:
        p = replay.player(m.player)
        army = [(float(t), float(v)) for t, v in m.army_value if t <= p.end_t]
        times = [t for t, _ in army]
        cands: list[Window] = []
        for i, (t0, v0) in enumerate(army):
            if v0 < th.army_collapse_min_army:
                continue
            j = bisect_right(times, t0 + th.army_collapse_window_s) - 1
            if j <= i:
                continue
            t1 = times[j]
            lost = _value_at(m.army_lost, t1) - _value_at(m.army_lost, t0)
            killed = _value_at(m.army_killed, t1) - _value_at(m.army_killed, t0)
            if lost >= th.army_collapse_frac * v0 and lost > killed:
                cands.append((t0, t1, lost, killed, v0))
        groups: list[list[Window]] = []
        group_end = float("-inf")
        for c in cands:
            if groups and c[0] <= group_end:
                groups[-1].append(c)
                group_end = max(group_end, c[1])
            else:
                groups.append([c])
                group_end = c[1]
        for g in groups:
            # earliest window wins ties on (lost - killed)
            t0, t1, lost, killed, v0 = max(g, key=lambda c: (c[2] - c[3], -c[0]))
            evidence = {
                "est_cost": int(round(lost - killed)),
                "army_before": int(round(v0)),
                "lost": int(round(lost)),
                "killed": int(round(killed)),
                "window_s": _num(t1 - t0),
            }
            out.append(_finding("army_collapse", "player", p.team, p.id, t0, t1, evidence))
    return out


# --------------------------------------------------------------------------- team rules


def _mean_income_rate_before(m: MetricsBundle | None, t: float, span: float = 60.0) -> float:
    if m is None or not m.income:
        return 0.0
    vals = [float(v) for pt, v in m.income if t - span <= pt <= t]
    if vals:
        return sum(vals) / len(vals) / 60.0
    return income_rate_at(m.income, t)


def early_ally_death(replay, metrics, team_metrics, th) -> list[Finding]:
    by_player = _bundles(metrics)
    out = []
    for tm in team_metrics:
        for e in tm.eliminations:
            if not e.early:
                continue
            left = e.left_at is not None and (
                e.eliminated_at is None or e.left_at <= e.eliminated_at
            )
            rate = _mean_income_rate_before(by_player.get(e.player), e.departed_at)
            evidence = {
                "est_cost": int(round(rate * e.team_played_on_s)),
                "departed_player": e.player,
                "how": "left" if left else "eliminated",
                "played_on_s": _num(e.team_played_on_s),
            }
            end = e.departed_at + e.team_played_on_s
            out.append(
                _finding(
                    "early_ally_death", "team", tm.team, e.player, e.departed_at, end, evidence
                )
            )
    return out


def _enemy_army(team_metrics: list[TeamMetrics], team: int) -> dict[float, float]:
    """Summed army value of all other teams at the times they all share."""
    others = [tm for tm in team_metrics if tm.team != team]
    if not others:
        return {}
    common = set.intersection(*({float(t) for t, _ in tm.army_value} for tm in others))
    total: dict[float, float] = {}
    for tm in others:
        for t, v in tm.army_value:
            if float(t) in common:
                total[float(t)] = total.get(float(t), 0.0) + float(v)
    return total


def team_army_deficit(replay, metrics, team_metrics, th) -> list[Finding]:
    out = []
    for tm in team_metrics:
        enemy = _enemy_army(team_metrics, tm.team)
        aligned = [
            (float(t), float(v), enemy[float(t)]) for t, v in tm.army_value if float(t) in enemy
        ]
        times = [a[0] for a in aligned]
        flags = [
            own <= th.team_army_deficit_ratio * en and en >= th.team_army_deficit_enemy_min
            for _, own, en in aligned
        ]
        for first, last in _runs(flags):
            start = times[first]
            end = _run_end(times, last)
            duration = end - start
            if duration < th.team_army_deficit_min_s:
                continue
            idx = range(first, last + 1)
            cost = sum(
                (aligned[k][2] - aligned[k][1]) * _interval(times, k) * th.army_deficit_factor
                for k in idx
            )
            evidence = {
                "est_cost": int(round(cost)),
                "min_ratio": round(min(aligned[k][1] / aligned[k][2] for k in idx), 2),
                "duration_s": _num(duration),
                "peak_gap": int(round(max(aligned[k][2] - aligned[k][1] for k in idx))),
            }
            out.append(_finding("team_army_deficit", "team", tm.team, None, start, end, evidence))
    return out


RULES: tuple[Rule, ...] = (
    supply_block,
    high_bank,
    low_workers,
    late_expansion,
    army_collapse,
    early_ally_death,
    team_army_deficit,
)
