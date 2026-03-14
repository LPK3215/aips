from __future__ import annotations

import sys
from pathlib import Path

import pytest


# Allow `pytest` to run from repo root (so `import app` works).
AIPS_API_DIR = Path(__file__).resolve().parents[1]
if str(AIPS_API_DIR) not in sys.path:
    sys.path.insert(0, str(AIPS_API_DIR))

from app.services.rate_limit_service import rate_limit_service


@pytest.fixture(autouse=True)
def reset_rate_limit_service():
    rate_limit_service.reset()
    yield
    rate_limit_service.reset()
