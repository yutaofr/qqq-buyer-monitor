"""TDD: Research Certifier — registry generation and metric outputs."""
import numpy as np
import pandas as pd
import pytest

from src.research.certifier import (
    certify_candidates,
    export_registry_json,
    REQUIRED_METRICS,
)
from src.models.candidate import CandidateRegistry
from src.models.risk import RiskState


def _price_history(n: int = 252) -> pd.DataFrame:
    """Generate simple synthetic price history for testing."""
    rng = np.random.default_rng(42)
    qqq_ret = pd.Series(rng.normal(0.0004, 0.012, n))
    qld_ret = qqq_ret * 2.0 + rng.normal(0, 0.002, n)
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame({"qqq_ret": qqq_ret.values, "qld_ret": qld_ret.values}, index=idx)


def _candidate_space() -> list[dict]:
    return [
        {
            "candidate_id": "neutral-test-001",
            "allowed_risk_state": "RISK_NEUTRAL",
            "qqq_pct": 0.70,
            "qld_pct": 0.10,
            "cash_pct": 0.20,
        },
        {
            "candidate_id": "defense-test-001",
            "allowed_risk_state": "RISK_DEFENSE",
            "qqq_pct": 0.30,
            "qld_pct": 0.00,
            "cash_pct": 0.70,
        },
    ]


# ── Task 15 ────────────────────────────────────────────────────────────────────

def test_certifier_builds_registry_object():
    registry = certify_candidates(
        price_history=_price_history(),
        macro_history=None,
        candidate_space=_candidate_space(),
    )
    assert isinstance(registry, CandidateRegistry)
    assert registry.registry_version
    assert len(registry.candidates) == 2


def test_certifier_assigns_registry_version_to_each_candidate():
    registry = certify_candidates(
        price_history=_price_history(),
        macro_history=None,
        candidate_space=_candidate_space(),
        registry_version="test-v7-certifier-r1",
    )
    assert registry.registry_version == "test-v7-certifier-r1"
    for c in registry.candidates:
        assert c.registry_version == "test-v7-certifier-r1"


def test_certifier_outputs_all_required_metrics():
    """SRD AC-8: all 8 required metrics must be present for each candidate."""
    registry = certify_candidates(
        price_history=_price_history(),
        macro_history=None,
        candidate_space=_candidate_space(),
    )
    for c in registry.candidates:
        for metric in REQUIRED_METRICS:
            assert metric in c.research_metrics, f"Missing metric '{metric}' for {c.candidate_id}"


def test_certifier_sets_correct_risk_state():
    registry = certify_candidates(
        price_history=_price_history(),
        macro_history=None,
        candidate_space=_candidate_space(),
    )
    neutral = next(c for c in registry.candidates if c.candidate_id == "neutral-test-001")
    defense = next(c for c in registry.candidates if c.candidate_id == "defense-test-001")
    assert neutral.allowed_risk_state == RiskState.RISK_NEUTRAL
    assert defense.allowed_risk_state == RiskState.RISK_DEFENSE


def test_certifier_assigns_certification_status():
    registry = certify_candidates(
        price_history=_price_history(),
        macro_history=None,
        candidate_space=_candidate_space(),
    )
    for c in registry.candidates:
        assert c.certification_status in {"CERTIFIED", "CONDITIONAL", "REJECTED"}


def test_certifier_works_with_no_price_history():
    """Graceful handling when price_history is None."""
    registry = certify_candidates(
        price_history=None,
        macro_history=None,
        candidate_space=_candidate_space(),
    )
    # Should still produce candidates, just with NaN metrics
    assert len(registry.candidates) == 2


def test_certifier_drawdown_budget_respected():
    """Candidates with MDD > budget must not be CERTIFIED."""
    # Use volatile history that should blow out the budget
    rng = np.random.default_rng(0)
    bad_history = pd.DataFrame({
        "qqq_ret": pd.Series(rng.normal(-0.004, 0.04, 252)),
        "qld_ret": pd.Series(rng.normal(-0.008, 0.08, 252)),
    }, index=pd.date_range("2024-01-01", periods=252, freq="B"))

    high_leverage_space = [{
        "candidate_id": "risky-test",
        "allowed_risk_state": "RISK_ON",
        "qqq_pct": 0.0,
        "qld_pct": 1.0,  # 2x leveraged fully
        "cash_pct": 0.0,
    }]
    registry = certify_candidates(
        price_history=bad_history,
        macro_history=None,
        candidate_space=high_leverage_space,
        drawdown_budget=0.30,
    )
    # With very bad returns, this should NOT be CERTIFIED
    c = registry.candidates[0]
    if c.research_metrics["max_drawdown"] > 0.30:
        assert c.certification_status != "CERTIFIED"


def test_certifier_export_and_reload(tmp_path):
    """Round-trip: certify → export JSON → reload via load_registry."""
    from src.engine.candidate_registry import load_registry

    registry = certify_candidates(
        price_history=_price_history(),
        macro_history=None,
        candidate_space=_candidate_space(),
        registry_version="export-test-r1",
    )
    export_path = str(tmp_path / "registry_export.json")
    export_registry_json(registry, export_path)

    reloaded = load_registry(export_path)
    assert reloaded.registry_version == "export-test-r1"
    assert len(reloaded.candidates) == 2
    # Verify round-trip for a metric
    orig = {c.candidate_id: c for c in registry.candidates}
    for c in reloaded.candidates:
        assert abs(c.research_metrics["max_drawdown"] - orig[c.candidate_id].research_metrics["max_drawdown"]) < 1e-9
