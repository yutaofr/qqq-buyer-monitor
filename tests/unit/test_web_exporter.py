"""
Unit tests for WebExporter (v8.2 Industrial).
Focuses on timezone-aware leap logic, market calendar awareness, and DST transitions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest
import pytz
from src.output.web_exporter import MarketCursor

# Timezone constants
EASTERN = pytz.timezone("US/Eastern")
UTC = pytz.utc

@pytest.fixture
def cursor():
    """Returns a MarketCursor instance for NYSE."""
    return MarketCursor(calendar_name="NYSE")

def to_eastern(dt_str: str) -> datetime:
    """Helper to create an aware Eastern datetime from string."""
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    return EASTERN.localize(dt)

def test_friday_close_leap_to_monday(cursor):
    """
    Scenario: Friday, March 27, 2026, 16:01:00 EST (Just after close).
    Expected: Leap to Monday, March 30, 2026, 09:30:00 EST + 4h Jitter = 13:30:00 EST.
    UTC Equivalent: 2026-03-30T17:30:00Z (EDT is UTC-4 in March).
    """
    now_est = to_eastern("2026-03-27 16:01:00")
    
    # Execution
    expires_at = cursor.get_expires_at_utc(now=now_est, jitter_hours=4)
    
    # Expected: Monday 09:30 + 4h = 13:30 EDT
    expected_utc = to_eastern("2026-03-30 13:30:00").astimezone(timezone.utc)
    
    # Assertions
    assert expires_at == expected_utc
    assert expires_at.tzinfo == timezone.utc

def test_half_day_black_friday_leap(cursor):
    """
    Scenario: Friday, Nov 27, 2026 (Black Friday), 13:01:00 EST (Just after early close).
    Expected: Recognize 13:00 close, leap to next Monday open + 4h.
    Monday, Nov 30, 09:30 EST + 4h = 13:30 EST.
    UTC Equivalent: 2026-11-30T18:30:00Z (EST is UTC-5 in Nov).
    """
    now_est = to_eastern("2026-11-27 13:01:00")
    
    # Execution
    expires_at = cursor.get_expires_at_utc(now=now_est, jitter_hours=4)
    
    # Expected: Monday 13:30 EST
    expected_utc = to_eastern("2026-11-30 13:30:00").astimezone(timezone.utc)
    
    # Assertions
    assert expires_at == expected_utc

def test_dst_transition_spring_forward(cursor):
    """
    Scenario: Friday, March 6, 2026 (Before DST switch on March 8).
    Expected: Leap to Monday, March 9 (After DST switch).
    Monday March 9, 09:30 EST (now EDT) + 4h = 13:30 EDT.
    UTC: 13:30 + 4 = 17:30 UTC.
    """
    now_est = to_eastern("2026-03-06 16:05:00")
    
    # Execution
    expires_at = cursor.get_expires_at_utc(now=now_est, jitter_hours=4)
    
    # Expected: Monday 13:30 EDT
    expected_utc = to_eastern("2026-03-09 13:30:00").astimezone(timezone.utc)
    
    # Assertions
    assert expires_at == expected_utc

def test_market_active_state_logic(cursor):
    """
    Scenario: Monday, March 30, 2026, 10:00:00 EST (During market hours).
    Expected State: ACTIVE.
    Next Run: Today's close (16:00 EST) or next hour depending on strategy.
    """
    now_est = to_eastern("2026-03-30 10:00:00")
    
    # Execution
    state = cursor.get_market_state(now=now_est)
    expires_at = cursor.get_expires_at_utc(now=now_est, jitter_hours=4)
    
    # Expected: Next hour (11:00 EDT) + 4h = 15:00 EDT
    expected_utc = to_eastern("2026-03-30 15:00:00").astimezone(timezone.utc)
    
    # Assertions
    assert state == "ACTIVE"
    assert expires_at == expected_utc

def test_frozen_state_weekend(cursor):
    """
    Scenario: Sunday, March 29, 2026.
    Expected State: FROZEN.
    """
    now_est = to_eastern("2026-03-29 12:00:00")
    
    # Execution
    state = cursor.get_market_state(now=now_est)
    
    # Assertions
    assert state == "FROZEN"

def test_strict_aware_datetime_requirement(cursor):
    """
    Scenario: Passing a naive datetime should raise ValueError to prevent timezone hell.
    """
    from datetime import datetime
    naive_dt = datetime(2026, 3, 27, 16, 0)
    with pytest.raises(ValueError, match="aware datetime"):
        cursor.get_expires_at_utc(now=naive_dt)
