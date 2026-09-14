from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def repo_root() -> Path:
    return EXAMPLES_DIR / "sample_repo"


@pytest.fixture
def sample_log() -> str:
    return (EXAMPLES_DIR / "sample_ci.log").read_text(encoding="utf-8")
