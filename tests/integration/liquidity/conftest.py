"""Integration test conftest — shared fixtures for real-data tests.

These tests require:
  - FRED_API_KEY in .env
  - Network access to fred.stlouisfed.org and finance.yahoo.com
  - Docker: docker compose run --rm test pytest -m external_service

Data is cached locally (.cache/liquidity/) to avoid repeated API calls.
"""

from __future__ import annotations

import pytest

from src.liquidity.config import load_config


@pytest.fixture(scope="session")
def config():
    """Load bocpd_params.json once per session."""
    return load_config()
