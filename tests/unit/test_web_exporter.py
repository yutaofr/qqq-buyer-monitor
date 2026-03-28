"""
Unit tests for the web exporter.
Focuses on timezone-aware leap logic and the v9 runtime narrative contract.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from datetime import date as date_cls
from pathlib import Path

import pytest
import pytz

from src.models import (
    Signal,
    SignalDetail,
    SignalResult,
    TargetAllocationState,
    Tier1Result,
    Tier2Result,
)
from src.models.deployment import DeploymentState
from src.models.risk import RiskState
from src.output.cli import build_runtime_logic_trace, build_v8_explanation
from src.output.web_exporter import MarketCursor, export_web_snapshot

# Timezone constants
EASTERN = pytz.timezone("US/Eastern")


@pytest.fixture
def cursor():
    """Returns a MarketCursor instance for NYSE."""
    return MarketCursor(calendar_name="NYSE")


def to_eastern(dt_str: str) -> datetime:
    """Helper to create an aware Eastern datetime from string."""
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    return EASTERN.localize(dt)


def _detail(name: str) -> SignalDetail:
    return SignalDetail(name, 0.0, 0, (0, 0), False, False)


def _runtime_result() -> SignalResult:
    t1 = Tier1Result(
        score=50,
        drawdown_52w=_detail("dd"),
        ma200_deviation=_detail("ma"),
        vix=_detail("vix"),
        fear_greed=_detail("fg"),
        breadth=_detail("br"),
    )
    t2 = Tier2Result(0, None, None, None, False, False, False, True, "yf", 0, 0)
    result = SignalResult(
        date=date_cls(2026, 3, 27),
        price=562.58,
        signal=Signal.WATCH,
        final_score=110,
        tier1=t1,
        tier2=t2,
        explanation="placeholder",
        target_allocation=TargetAllocationState(0.60, 0.30, 0.10, 0.50),
        confidence="high",
        data_quality={
            "credit_spread": {"usable": True},
            "erp": {"usable": True},
            "vix": {"usable": True},
        },
    )
    result.cycle_regime = "LATE_CYCLE"
    result.tier0_regime = "RICH_TIGHTENING"
    result.risk_state = RiskState.RISK_REDUCED
    result.deployment_state = DeploymentState.DEPLOY_BASE
    result.selected_candidate_id = "reduced-limited-001"
    result.registry_version = "2026-03-24-v7.0-r1"
    result.raw_target_beta = 0.80
    result.target_beta = 0.50
    result.target_exposure_ceiling = 0.80
    result.target_cash_floor = 0.20
    result.qld_share_ceiling = 0.10
    result.should_adjust = False
    result.rebalance_action = {"reason": "upshift_confirmation"}
    result.deployment_action = {
        "deploy_mode": "BASE",
        "reason": "rich_tightening_base",
        "path": "qqq_only_new_cash",
    }
    result.risk_reasons = [{"rule": "single_stress", "tier0_regime": "RICH_TIGHTENING"}]
    result.cycle_reasons = [{"rule": "late_cycle"}]
    result.deployment_reasons = [{"rule": "rich_tightening_base", "path": "qqq_only_new_cash"}]
    result.feature_values = {
        "credit_spread": 321.0,
        "erp": 2.02,
        "price_vs_ma200": -0.03,
        "net_liquidity": 5818.97,
        "liquidity_roc": 0.78,
        "vix": 31.1,
        "fear_greed": 10.0,
        "rolling_drawdown": 0.113,
        "tactical_stress_score": 52,
    }
    result.logic_trace = build_runtime_logic_trace(result)
    result.explanation = build_v8_explanation(result)
    return result


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
    expected_utc = to_eastern("2026-03-30 13:30:00").astimezone(UTC)

    # Assertions
    assert expires_at == expected_utc
    assert expires_at.tzinfo == UTC


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
    expected_utc = to_eastern("2026-11-30 13:30:00").astimezone(UTC)

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
    expected_utc = to_eastern("2026-03-09 13:30:00").astimezone(UTC)

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
    expected_utc = to_eastern("2026-03-30 15:00:00").astimezone(UTC)

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


def test_export_web_snapshot_contains_v9_decision_chain(tmp_path, monkeypatch):
    result = _runtime_result()
    output_path = tmp_path / "status.json"

    monkeypatch.setattr(MarketCursor, "get_market_state", lambda self, now: "FROZEN")
    monkeypatch.setattr(
        MarketCursor,
        "get_expires_at_utc",
        lambda self, now, jitter_hours=4: datetime(2026, 3, 30, 17, 30, tzinfo=UTC),
    )

    ok = export_web_snapshot(result, output_path=output_path)

    assert ok is True
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["meta"]["version"] == "v10.0"
    assert payload["signal"]["contract"] == "target_beta_signal"
    assert payload["signal"]["cycle_regime"] == "LATE_CYCLE"
    assert payload["signal"]["target_beta"] == 0.50
    assert payload["signal"]["candidate_id"] == "reduced-limited-001"
    assert "用户自行决定资产配置比例" in payload["signal"]["contract_desc"]
    assert "仅用于说明一种实现目标 beta 的仓位组合" in payload["signal"]["reference_desc"]
    assert payload["signal"]["reference_path"]["qqq_pct"] == 0.30
    steps = [trace["step"] for trace in payload["evidence"]["node_traces"]]
    assert steps == [
        "tier0_regime",
        "cycle_regime",
        "risk_controller",
        "candidate_selection",
        "beta_advisory",
        "deployment_controller",
        "reference_path",
    ]


def test_web_index_narrative_uses_v9_target_beta_contract():
    html = Path("src/web/public/index.html").read_text(encoding="utf-8")

    assert "v10.0" in html
    assert "v8.2" not in html
    assert "目标 Beta (系统 contract)" in html
    assert "Tier-0 -> Cycle -> Risk -> Candidate -> Advisory -> Deployment" in html
