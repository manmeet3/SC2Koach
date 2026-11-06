"""Summarize one player's recurring problems across many replays (wins vs losses).

Usage:
    python scripts/trends.py <replay_dir> --player NAME [--last N] [--workers 8]

Analyzes every supported 2v2/3v3/4v4 replay in <replay_dir> that the player is in and
prints medians and finding frequencies, split by wins and losses. Output stays on screen;
nothing is written. See docs/improvement-playbook.md.
"""

from __future__ import annotations

import argparse
import statistics as st
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

FINDING_TYPES = (
    "army_collapse",
    "team_army_deficit",
    "early_ally_death",
    "late_expansion",
    "low_workers",
    "supply_block",
    "high_bank",
)


def _one(args: tuple[Path, str]) -> dict | None:
    from sc2koach.config import Config, FocusConfig
    from sc2koach.errors import Sc2KoachError
    from sc2koach.pipeline import analyze

    path, name = args
    try:
        res = analyze(path, Config(focus=FocusConfig(name=name)))
    except Sc2KoachError:
        return None
    pid = res.replay.focus_player_id
    if pid is None:
        return None
    player = next(p for p in res.replay.players if p.id == pid)
    team = next(t for t in res.replay.teams if t.id == player.team)
    m = next(b for b in res.metrics if b.player == pid)
    mine = [f for f in res.findings if f.player == pid and f.scope == "player"]
    ours = [f for f in res.findings if f.scope == "team" and f.team == player.team]
    bases = {e.n: e.finished for e in m.expansions}
    return {
        "played_at": res.replay.game.played_at or "",
        "result": team.result,
        "race": player.race,
        "workers_4m": m.workers_at_4m.value,
        "sq": m.unspent.sq,
        "base2": bases.get(2),
        "base3": bases.get(3),
        "blocked_s": sum(b.duration_s for b in m.supply_blocks),
        "types": Counter(f.type for f in mine + ours),
        "top": max(mine, key=lambda f: f.evidence.get("est_cost", 0)).type if mine else None,
    }


def _med(values: list) -> float | None:
    vals = [v for v in values if v is not None]
    return st.median(vals) if vals else None


def _fmt(v: float | None, kind: str = "num") -> str:
    if v is None:
        return "—"
    if kind == "time":
        return f"{int(v // 60)}:{int(v % 60):02d}"
    return f"{v:.0f}" if kind == "int" else f"{v:.1f}"


def _row(label: str, games: list[dict]) -> list[str]:
    n = len(games)
    out = [
        label,
        str(n),
        _fmt(_med([g["workers_4m"] for g in games]), "int"),
        _fmt(_med([g["sq"] for g in games]), "int"),
        _fmt(_med([g["base2"] for g in games]), "time"),
        _fmt(_med([g["base3"] for g in games]), "time"),
        f"{(sum(g['base3'] is None for g in games) / n):.0%}" if n else "—",
        _fmt(_med([g["blocked_s"] for g in games]), "int"),
    ]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("replay_dir", type=Path)
    ap.add_argument("--player", required=True, help="Player name (case-insensitive)")
    ap.add_argument("--last", type=int, default=0, help="Only the N most recent games")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    paths = sorted(args.replay_dir.glob("*.SC2Replay"))
    with ProcessPoolExecutor(args.workers) as ex:
        games = [g for g in ex.map(_one, [(p, args.player) for p in paths], chunksize=2) if g]
    games.sort(key=lambda g: g["played_at"])
    if args.last:
        games = games[-args.last :]
    if not games:
        print(f"No supported replays found with player '{args.player}'.")
        return 1

    wins = [g for g in games if g["result"] == "Win"]
    losses = [g for g in games if g["result"] == "Loss"]
    unknown = len(games) - len(wins) - len(losses)
    races = Counter(g["race"] for g in games)
    print(
        f"{args.player}: {len(games)} games ({len(wins)} W / {len(losses)} L / "
        f"{unknown} result unknown), races {dict(races)}"
    )
    if unknown:
        print("  Result is unknown when the replay doesn't record a winner (often after")
        print("  someone left early). Those games count only in 'All'.")
    print()
    header = ["", "Games", "Workers@4", "SQ", "2nd base", "3rd base", "No 3rd", "Blocked s"]
    rows = [_row("All", games), _row("Wins", wins), _row("Losses", losses)]
    widths = [max(len(r[i]) for r in [header, *rows]) for i in range(len(header))]
    for r in [header, *rows]:
        print("  ".join(c.rjust(w) for c, w in zip(r, widths, strict=True)))

    print("\nShare of games where each finding fired (yours, or your team's):")
    print(f"  {'finding':<20} {'all':>6} {'wins':>6} {'losses':>7}")
    for t in FINDING_TYPES:

        def share(gs: list[dict], t: str = t) -> str:
            return f"{sum(1 for g in gs if g['types'][t]) / len(gs):.0%}" if gs else "—"

        print(f"  {t:<20} {share(games):>6} {share(wins):>6} {share(losses):>7}")

    gaps = []
    for t in FINDING_TYPES:
        if wins and losses:
            w = sum(1 for g in wins if g["types"][t]) / len(wins)
            lo = sum(1 for g in losses if g["types"][t]) / len(losses)
            gaps.append((lo - w, t))
    gaps.sort(reverse=True)
    if gaps and gaps[0][0] > 0:
        print("\nBiggest difference between your losses and wins (start here):")
        for diff, t in gaps[:3]:
            if diff > 0:
                print(f"  {t}: fires in {diff * 100:.0f} percentage points more of your losses")
    top = Counter(g["top"] for g in games if g["top"])
    print("\nMost common #1 Top priority:", ", ".join(f"{t} ({n})" for t, n in top.most_common(3)))
    print("Note: high_bank is over-weighted in Top priorities; compare SQ instead.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
