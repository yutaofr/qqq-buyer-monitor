"""TDD: Research Certifier — registry generation and metric outputs."""
import numpy as np
import pandas as pd
import pytest

from src.research.certifier import (
    certify_candidates,
    export_registry_json,
    REQUIRED_METRICS,
    _certify_status,
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


def _macro_history(price_history: pd.DataFrame, *, low_class_a_coverage: bool = False) -> pd.DataFrame:
    macro = pd.DataFrame({
        "observation_date": price_history.index,
        "effective_date": price_history.index,
    }).reset_index(drop=True)
    macro["credit_spread_bps"] = 350.0
    macro["credit_acceleration_pct_10d"] = 0.0
    macro["real_yield_10y_pct"] = 1.5
    macro["net_liquidity_usd_bn"] = 250.0
    macro["liquidity_roc_pct_4w"] = 0.0
    macro["funding_stress_flag"] = 0
    macro["source_credit_spread"] = "fred:BAMLH0A0HYM2"
    macro["source_real_yield"] = "fred:DFII10"
    macro["source_net_liquidity"] = "derived:WALCL-WDTGAL-RRPONTSYD"
    macro["source_funding_stress"] = "fred:NFCI"
    macro["build_version"] = "v7.0-class-a-research-r1"
    macro["benchmark_ret"] = price_history["qqq_ret"].values
    macro["nav_integrity"] = 1.0

    if low_class_a_coverage:
        macro.loc[macro.index[:20], "real_yield_10y_pct"] = pd.NA

    return macro


# ── Task 15 ────────────────────────────────────────────────────────────────────

def test_certifier_builds_registry_object():
    price_history = _price_history()
    registry = certify_candidates(
        price_history=price_history,
        macro_history=_macro_history(price_history),
        candidate_space=_candidate_space(),
    )
    assert isinstance(registry, CandidateRegistry)
    assert registry.registry_version
    assert len(registry.candidates) == 2


def test_certifier_assigns_registry_version_to_each_candidate():
    price_history = _price_history()
    registry = certify_candidates(
        price_history=price_history,
        macro_history=_macro_history(price_history),
        candidate_space=_candidate_space(),
        registry_version="test-v7-certifier-r1",
    )
    assert registry.registry_version == "test-v7-certifier-r1"
    for c in registry.candidates:
        assert c.registry_version == "test-v7-certifier-r1"


def test_certifier_outputs_all_required_metrics():
    """SRD AC-8: all 8 required metrics must be present for each candidate."""
    price_history = _price_history()
    registry = certify_candidates(
        price_history=price_history,
        macro_history=_macro_history(price_history),
        candidate_space=_candidate_space(),
    )
    for c in registry.candidates:
        for metric in REQUIRED_METRICS:
            assert metric in c.research_metrics, f"Missing metric '{metric}' for {c.candidate_id}"


def test_certifier_sets_correct_risk_state():
    price_history = _price_history()
    registry = certify_candidates(
        price_history=price_history,
        macro_history=_macro_history(price_history),
        candidate_space=_candidate_space(),
    )
    neutral = next(c for c in registry.candidates if c.candidate_id == "neutral-test-001")
    defense = next(c for c in registry.candidates if c.candidate_id == "defense-test-001")
    assert neutral.allowed_risk_state == RiskState.RISK_NEUTRAL
    assert defense.allowed_risk_state == RiskState.RISK_DEFENSE


def test_certifier_assigns_certification_status():
    price_history = _price_history()
    registry = certify_candidates(
        price_history=price_history,
        macro_history=_macro_history(price_history),
        candidate_space=_candidate_space(),
    )
    for c in registry.candidates:
        assert c.certification_status in {"CERTIFIED", "CONDITIONAL", "REJECTED"}


def test_certifier_uses_csv_like_macro_history_with_rangeindex_and_explicit_dates():
    price_history = _price_history()
    macro = _macro_history(price_history).sample(frac=1.0, random_state=7).reset_index(drop=True)

    registry = certify_candidates(
        price_history=price_history,
        macro_history=macro,
        candidate_space=_candidate_space(),
    )

    assert len(registry.candidates) == 2
    assert all(c.research_metrics["nav_integrity"] == 1.0 for c in registry.candidates)
    assert all(c.research_metrics["mean_interval_beta_deviation"] < 0.05 for c in registry.candidates)


def test_certifier_applies_beta_fidelity_gate():
    base_metrics = {
        "max_drawdown": 0.29,
        "nav_integrity": 1.0,
    }

    assert _certify_status({**base_metrics, "mean_interval_beta_deviation": 0.049}) == "CERTIFIED"
    assert _certify_status({**base_metrics, "mean_interval_beta_deviation": 0.08}) == "CONDITIONAL"
    assert _certify_status({**base_metrics, "mean_interval_beta_deviation": 0.11}) == "REJECTED"


def test_certifier_works_with_no_price_history():
    """Graceful handling when price_history is None."""
    price_history = _price_history()
    registry = certify_candidates(
        price_history=None,
        macro_history=_macro_history(price_history),
        candidate_space=_candidate_space(),
    )
    # Should still produce candidates, just with NaN metrics
    assert len(registry.candidates) == 2


def test_certifier_drawdown_budget_respected():
    """Candidates with MDD > budget must not be CERTIFIED."""
    # Use volatile history that should blow out the budget
    rng = np.random.default_rng(0)
    bad_history = pd.DataFrame({
        "qqq_ret": rng.normal(-0.004, 0.04, 252),
        "qld_ret": rng.normal(-0.008, 0.08, 252),
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
        macro_history=_macro_history(bad_history),
        candidate_space=high_leverage_space,
        drawdown_budget=0.30,
    )
    # With very bad returns, this should NOT be CERTIFIED
    c = registry.candidates[0]
    if c.research_metrics["max_drawdown"] > 0.30:
        assert c.certification_status != "CERTIFIED"


def test_certifier_beta_fidelity_gate_blocks_certified_status():
    """Low-MDD but beta-misaligned candidates must not be CERTIFIED."""
    aligned_qqq = pd.Series(
        [0.001 + (i % 5) * 0.0001 for i in range(252)],
        index=pd.date_range("2024-01-01", periods=252, freq="B"),
    )
    bad_history = pd.DataFrame(
        {
            "qqq_ret": aligned_qqq,
            "qld_ret": aligned_qqq * 2.0,
        }
    )
    macro_history = _macro_history(bad_history)
    macro_history["benchmark_ret"] = 0.01
    candidate_space = [{
        "candidate_id": "beta-bad",
        "allowed_risk_state": "RISK_ON",
        "qqq_pct": 0.0,
        "qld_pct": 1.0,
        "cash_pct": 0.0,
    }]
    registry = certify_candidates(
        price_history=bad_history,
        macro_history=macro_history,
        candidate_space=candidate_space,
        drawdown_budget=0.30,
    )
    candidate = registry.candidates[0]
    assert candidate.research_metrics["max_drawdown"] <= 0.30
    assert candidate.research_metrics["mean_interval_beta_deviation"] > 0.05
    assert candidate.certification_status != "CERTIFIED"


def test_certifier_requires_external_audit_inputs_for_certified_status():
    candidate_space = [{
        "candidate_id": "missing-audit",
        "allowed_risk_state": "RISK_NEUTRAL",
        "qqq_pct": 0.70,
        "qld_pct": 0.10,
        "cash_pct": 0.20,
    }]
    with pytest.raises(ValueError, match="macro_history is required"):
        certify_candidates(
            price_history=_price_history(),
            macro_history=None,
            candidate_space=candidate_space,
            drawdown_budget=0.30,
        )


def test_certifier_export_and_reload(tmp_path):
    """Round-trip: certify → export JSON → reload via load_registry."""
    from src.engine.candidate_registry import load_registry

    price_history = _price_history()
    registry = certify_candidates(
        price_history=price_history,
        macro_history=_macro_history(price_history),
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


def test_certifier_requires_macro_audit_inputs():
    price_history = _price_history()
    with pytest.raises(ValueError, match="benchmark_ret|nav_integrity"):
        certify_candidates(
            price_history=price_history,
            macro_history=_macro_history(price_history).drop(columns=["benchmark_ret"]),
            candidate_space=_candidate_space(),
        )


def test_certifier_rejects_low_class_a_macro_coverage():
    price_history = _price_history()
    with pytest.raises(ValueError, match="Class A|coverage"):
        certify_candidates(
            price_history=price_history,
            macro_history=_macro_history(price_history, low_class_a_coverage=True),
            candidate_space=_candidate_space(),
        )


def test_certifier_accepts_explicit_subset_macro_input():
    price_history = _price_history()
    macro = _macro_history(price_history)[
        [
            "observation_date",
            "effective_date",
            "credit_spread_bps",
            "credit_acceleration_pct_10d",
            "real_yield_10y_pct",
            "net_liquidity_usd_bn",
            "liquidity_roc_pct_4w",
            "funding_stress_flag",
            "benchmark_ret",
            "nav_integrity",
        ]
    ].copy()

    registry = certify_candidates(
        price_history=price_history,
        macro_history=macro,
        candidate_space=_candidate_space(),
    )

    assert len(registry.candidates) == 2
