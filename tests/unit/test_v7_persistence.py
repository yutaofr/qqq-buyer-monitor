"""TDD: v7 persistence — save and reload v7 fields via DB."""
from datetime import date

from src.models import (
    Signal,
    SignalDetail,
    SignalResult,
    Tier1Result,
    Tier2Result,
)
from src.models.deployment import DeploymentState
from src.models.risk import RiskState
from src.store.db import load_history, save_signal


def _detail(name: str) -> SignalDetail:
    return SignalDetail(name, 0.0, 0, (0, 0), False, False)


def _v7_result() -> SignalResult:
    t1 = Tier1Result(
        score=50,
        drawdown_52w=_detail("dd"),
        ma200_deviation=_detail("ma"),
        vix=_detail("vix"),
        fear_greed=_detail("fg"),
        breadth=_detail("br"),
    )
    t2 = Tier2Result(0, None, None, None, False, False, False, True, "none", None, None)
    return SignalResult(
        date=date(2026, 3, 24),
        price=450.0,
        signal=Signal.NO_SIGNAL,
        final_score=50,
        tier1=t1,
        tier2=t2,
        explanation="v7 test",
        risk_state=RiskState.RISK_NEUTRAL,
        deployment_state=DeploymentState.DEPLOY_BASE,
        selected_candidate_id="neutral-base-001",
        registry_version="2026-03-24-v7.0-r1",
        tier0_regime="NEUTRAL",
        tier0_applied=False,
        target_beta=0.90,
        should_adjust=False,
        rebalance_action={"should_adjust": False, "reason": "within_band:gap=0.000"},
        deployment_action={"deploy_mode": "BASE", "reason": "default_base"},
        candidate_selection_audit=[{"candidate_id": "neutral-low-drift", "reason": "higher_adjustment_cost"}],
    )


def test_save_and_reload_v7_risk_state(tmp_path):
    path = str(tmp_path / "signals_v7.db")
    result = _v7_result()
    save_signal(result, path=path)
    history = load_history(1, path=path)
    assert history[0]["risk_state"] == "RISK_NEUTRAL"


def test_save_and_reload_v7_deployment_state(tmp_path):
    path = str(tmp_path / "signals_v7.db")
    save_signal(_v7_result(), path=path)
    history = load_history(1, path=path)
    assert history[0]["deployment_state"] == "DEPLOY_BASE"


def test_save_and_reload_v7_candidate_fields(tmp_path):
    path = str(tmp_path / "signals_v7.db")
    save_signal(_v7_result(), path=path)
    history = load_history(1, path=path)
    rec = history[0]
    assert rec["selected_candidate_id"] == "neutral-base-001"
    assert rec["registry_version"] == "2026-03-24-v7.0-r1"


def test_save_and_reload_v7_actions(tmp_path):
    path = str(tmp_path / "signals_v7.db")
    save_signal(_v7_result(), path=path)
    history = load_history(1, path=path)
    rec = history[0]
    assert rec["rebalance_action"]["should_adjust"] is False
    assert rec["deployment_action"]["deploy_mode"] == "BASE"


def test_save_and_reload_v8_linear_pipeline_fields(tmp_path):
    path = str(tmp_path / "signals_v8.db")
    save_signal(_v7_result(), path=path)
    history = load_history(1, path=path)
    rec = history[0]
    assert rec["tier0_regime"] == "NEUTRAL"
    assert rec["tier0_applied"] is False
    assert rec["target_beta"] == 0.9
    assert rec["should_adjust"] is False


def test_save_and_reload_v7_audit(tmp_path):
    path = str(tmp_path / "signals_v7.db")
    save_signal(_v7_result(), path=path)
    history = load_history(1, path=path)
    audit = history[0]["candidate_selection_audit"]
    assert len(audit) == 1
    assert audit[0]["candidate_id"] == "neutral-low-drift"


def test_legacy_result_has_null_v7_fields(tmp_path):
    """Old-style result without v7 fields must load cleanly with null defaults."""
    path = str(tmp_path / "signals_legacy.db")
    t1 = Tier1Result(
        score=0, drawdown_52w=_detail("dd"), ma200_deviation=_detail("ma"),
        vix=_detail("vix"), fear_greed=_detail("fg"), breadth=_detail("br"),
    )
    t2 = Tier2Result(0, None, None, None, False, False, False, True, "none", None, None)
    legacy = SignalResult(
        date=date(2025, 1, 1), price=400.0, signal=Signal.NO_SIGNAL,
        final_score=0, tier1=t1, tier2=t2, explanation="legacy",
    )
    save_signal(legacy, path=path)
    history = load_history(1, path=path)
    rec = history[0]
    assert rec["risk_state"] is None
    assert rec["deployment_state"] is None
    assert rec["tier0_regime"] is None
    assert rec["tier0_applied"] is False
    assert rec["target_beta"] is None
    assert rec["should_adjust"] is None
    assert rec["rebalance_action"] == {}
    assert rec["candidate_selection_audit"] == []
