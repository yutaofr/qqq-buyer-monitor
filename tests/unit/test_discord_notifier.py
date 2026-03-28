from __future__ import annotations

from datetime import date

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
from src.output.discord_notifier import send_discord_signal


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
        date=date(2026, 3, 27),
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
    result.deployment_reasons = [{"rule": "rich_tightening_base", "path": "qqq_only_new_cash"}]
    result.feature_values = {
        "credit_spread": 321.0,
        "erp": 2.02,
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


def test_discord_notification_uses_v9_target_beta_contract(monkeypatch):
    captured: dict = {}

    class _Response:
        def raise_for_status(self) -> None:
            return None

    def fake_post(url, json, timeout):  # noqa: ANN001
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr("src.output.discord_notifier.requests.post", fake_post)

    ok = send_discord_signal(_runtime_result(), "https://example.test/webhook")

    assert ok is True
    embed = captured["json"]["embeds"][0]
    assert captured["url"] == "https://example.test/webhook"
    assert "v9.0" in embed["title"]
    assert "v8.2" not in embed["title"]
    assert "Decision Contract" in embed["description"]
    field_names = [field["name"] for field in embed["fields"]]
    assert "🧭 Decision Path" in field_names
    assert "📎 Reference Path" in field_names
    assert "📊 Recommended Portfolio" not in field_names
    decision_value = next(field["value"] for field in embed["fields"] if field["name"] == "🧭 Decision Path")
    reference_value = next(field["value"] for field in embed["fields"] if field["name"] == "📎 Reference Path")
    assert "Tier-0(RICH_TIGHTENING)" in decision_value
    assert "Candidate(reduced-limited-001)" in decision_value
    assert "Deployment(DEPLOY_BASE)" in decision_value
    assert "non-binding" in reference_value
    assert "QQQ=30.0%" in reference_value
