"""Analyze every local replay: errors, determinism, timing, finding/warning counts.

Usage: python scripts/run_all.py [replay_dir] [--workers 8]
Prints aggregates only (no player names).
"""

from __future__ import annotations

import argparse
import collections
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def run(path: Path) -> dict:
    from sc2koach.config import Config
    from sc2koach.errors import UnsupportedReplayError
    from sc2koach.pipeline import analyze
    from sc2koach.report import render_markdown

    t0 = time.perf_counter()
    try:
        res = analyze(path, Config())
        md = render_markdown(res)
        elapsed = time.perf_counter() - t0
        deterministic = md == render_markdown(analyze(path, Config()))
    except UnsupportedReplayError as exc:
        return {"file": path.name, "unsupported": str(exc)}
    except Exception:
        return {"file": path.name, "error": traceback.format_exc()[-800:]}
    return {
        "file": path.name,
        "s": elapsed,
        "deterministic": deterministic,
        "types": collections.Counter(f.type for f in res.findings),
        "warn": collections.Counter(w.code for w in res.warnings),
        "players": len(res.replay.players),
        "nfind": len(res.findings),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("replay_dir", nargs="?", default="replays")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    paths = sorted(Path(args.replay_dir).glob("*.SC2Replay"))
    with ProcessPoolExecutor(args.workers) as ex:
        recs = list(ex.map(run, paths, chunksize=2))
    errs = [r for r in recs if "error" in r]
    ok = [r for r in recs if "s" in r]
    unsupported = sum("unsupported" in r for r in recs)
    print(f"ok {len(ok)}  unsupported {unsupported}  errors {len(errs)}")
    for e in errs[:5]:
        print(e["file"], e["error"])
    if not ok:
        return 1 if errs else 0
    ts = sorted(r["s"] for r in ok)
    print(f"seconds per analysis: p50 {ts[len(ts) // 2]:.2f}  max {ts[-1]:.2f}")
    print("non-deterministic:", sum(not r["deterministic"] for r in ok))
    types, warns = collections.Counter(), collections.Counter()
    for r in ok:
        types.update(r["types"])
        warns.update(r["warn"])
    players = sum(r["players"] for r in ok)
    print("findings per player-game:", {k: round(v / players, 2) for k, v in types.most_common()})
    print("warnings:", dict(warns))
    return 1 if errs or any(not r["deterministic"] for r in ok) else 0


if __name__ == "__main__":
    raise SystemExit(main())
