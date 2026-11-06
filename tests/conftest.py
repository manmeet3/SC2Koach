import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _replay_dir() -> Path:
    return Path(os.environ.get("SC2KOACH_REPLAYS", REPO_ROOT / "replays"))


@pytest.fixture(scope="session")
def replay_paths() -> list[Path]:
    paths = sorted(_replay_dir().glob("*.SC2Replay"))
    if not paths:
        pytest.skip("no local replays (set SC2KOACH_REPLAYS or add replays/)")
    return paths
