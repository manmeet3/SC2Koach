"""Game-time conversion. All sc2Koach times are real seconds matching the in-game clock."""

LOOPS_PER_SECOND = 22.4  # "Faster" game speed
STATS_INTERVAL_LOOPS = 160  # PlayerStatsEvent cadence, ~7.14 s


def loop_to_seconds(loop: int) -> float:
    return loop / LOOPS_PER_SECOND


def fmt_mmss(seconds: float) -> str:
    total = int(round(seconds))
    return f"{total // 60}:{total % 60:02d}"
