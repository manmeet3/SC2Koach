"""Workers, income, unspent resources and spending quotient (design/DESIGN.md §6)."""

from __future__ import annotations

import math

from ..models import NullableScalar, ReplayModel, Series, Unspent
from ..thresholds import Thresholds
from .common import player_snapshots

WORKERS_AT_S = 240.0


def workers_series(replay: ReplayModel, pid: int) -> Series:
    return [(s.t, float(s.workers)) for s in player_snapshots(replay, pid)]


def workers_at_4m(replay: ReplayModel, pid: int) -> NullableScalar:
    """Snapshot workers at the last regular snapshot at or before 4:00 (3:56)."""
    if replay.game.duration_s < WORKERS_AT_S:
        return NullableScalar(reason="game_ended")
    if replay.player(pid).end_t < WORKERS_AT_S:
        return NullableScalar(reason="player_ended")
    last = None
    for s in player_snapshots(replay, pid):
        if s.regular and s.t <= WORKERS_AT_S:
            last = s
    if last is None:
        return NullableScalar(reason="no_data")
    return NullableScalar(value=float(last.workers))


def income_series(replay: ReplayModel, pid: int) -> Series:
    return [(s.t, float(s.income_per_min)) for s in player_snapshots(replay, pid)]


def bank_adjusted(replay: ReplayModel, pid: int, th: Thresholds) -> Series:
    """Minerals + gas per snapshot, minus resources received in the last trade_grace_s."""
    received = [(tr.t, tr.minerals + tr.gas) for tr in replay.resource_trades if tr.to == pid]
    out: Series = []
    for s in player_snapshots(replay, pid):
        recent = sum(amount for t, amount in received if s.t - th.trade_grace_s < t <= s.t)
        out.append((s.t, float(max(0, s.minerals + s.gas - recent))))
    return out


def high_bank_threshold(t: float, th: Thresholds) -> int:
    return th.high_bank_early if t < th.high_bank_cutover_s else th.high_bank_late


def seconds_above_threshold(series: Series, th: Thresholds) -> float:
    """Total length of snapshot intervals that start with the bank above its threshold."""
    total = 0.0
    for (t0, bank), (t1, _) in zip(series, series[1:], strict=False):
        if bank > high_bank_threshold(t0, th):
            total += t1 - t0
    return total


def spending_quotient(mean_income_per_min: float, mean_unspent: float) -> float:
    """Kasting's SQ = 35 × (0.00137 × I − ln U) + 240, with U floored at 1."""
    u = max(1.0, mean_unspent)
    return 35 * (0.00137 * mean_income_per_min - math.log(u)) + 240


def unspent(replay: ReplayModel, pid: int, th: Thresholds) -> Unspent:
    """Trade-adjusted bank series and summary. Mean and SQ use regular snapshots in
    [0, end_t] (all snapshots if there are no regular ones)."""
    series = bank_adjusted(replay, pid, th)
    snaps = player_snapshots(replay, pid)
    idx = [i for i, s in enumerate(snaps) if s.regular] or list(range(len(snaps)))
    if not idx:
        return Unspent(mean=0.0, peak=0.0, sq=None, seconds_above_threshold=0.0, series=series)
    mean_bank = sum(series[i][1] for i in idx) / len(idx)
    mean_income = sum(snaps[i].income_per_min for i in idx) / len(idx)
    return Unspent(
        mean=mean_bank,
        peak=max(v for _, v in series),
        sq=spending_quotient(mean_income, mean_bank),
        seconds_above_threshold=seconds_above_threshold(series, th),
        series=series,
    )
