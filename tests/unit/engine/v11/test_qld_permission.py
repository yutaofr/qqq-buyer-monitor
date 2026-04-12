from __future__ import annotations

import pandas as pd

from src.engine.v11.signal.qld_permission import QLDPermissionEvaluator


def _context(
    *,
    erp_base: float = 0.034,
    erp_step: float = 0.00005,
    capex_base: float = 8.0,
    capex_step: float = 0.12,
    periods: int = 260,
) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=periods)
    return pd.DataFrame(
        {
            "observation_date": dates,
            "erp_ttm_pct": [erp_base + (erp_step * i) for i in range(periods)],
            "core_capex_mm": [capex_base + (capex_step * i) for i in range(periods)],
        }
    ).set_index("observation_date")


def _quality(*, erp_quality: float = 1.0, capex_quality: float = 1.0) -> dict:
    return {
        "fields": {
            "erp_ttm": {
                "available": erp_quality > 0.0,
                "quality": erp_quality,
                "source": "direct:test",
                "degraded": erp_quality < 1.0,
            },
            "core_capex": {
                "available": capex_quality > 0.0,
                "quality": capex_quality,
                "source": "direct:test",
                "degraded": capex_quality < 1.0,
            },
        }
    }


def _baseline(
    *,
    tractor_prob: float = 0.02,
    sidecar_prob: float = 0.03,
    sidecar_status: str = "success_cached_trace",
) -> dict:
    return {
        "tractor": {
            "prob": tractor_prob,
            "prev_prob": tractor_prob,
            "delta_1d": 0.0,
            "status": "success_cached_trace",
        },
        "sidecar": {
            "prob": sidecar_prob,
            "prev_prob": sidecar_prob,
            "delta_1d": 0.0,
            "status": sidecar_status,
        },
    }


def test_fundamental_override_fails_closed_on_missing_or_degraded_inputs():
    evaluator = QLDPermissionEvaluator()

    decision = evaluator.evaluate(
        context_df=_context(),
        baseline_result=_baseline(),
        resonance_result={"action": "HOLD", "confidence": 0.0},
        overlay={"positive_score": 0.8, "negative_score": 0.0},
        effective_entropy=0.42,
        topology_state={
            "regime": "RECOVERY",
            "confidence": 0.82,
        },
        quality_audit=_quality(erp_quality=0.4, capex_quality=1.0),
        base_reentry_signal=0.7,
        target_beta=0.72,
    )

    assert decision.fundamental_override["active"] is False
    assert decision.fundamental_override["source_ready"] is False
    assert decision.allow_sub1x_qld is False
    assert decision.relaxed_entry_signal == 0.0


def test_fundamental_override_activates_on_capex_impulse_and_erp_support():
    evaluator = QLDPermissionEvaluator()

    decision = evaluator.evaluate(
        context_df=_context(),
        baseline_result=_baseline(),
        resonance_result={"action": "BUY_QLD", "confidence": 0.9},
        overlay={"positive_score": 0.85, "negative_score": 0.0},
        effective_entropy=0.34,
        topology_state={
            "regime": "RECOVERY",
            "confidence": 0.86,
        },
        quality_audit=_quality(),
        base_reentry_signal=0.72,
        target_beta=0.74,
    )

    assert decision.fundamental_override["active"] is True
    assert decision.allow_sub1x_qld is True
    assert decision.relaxed_entry_signal > 0.72
    assert decision.forced_bucket == "QLD"


def test_qld_permission_binds_resonance_sell_to_qqq():
    evaluator = QLDPermissionEvaluator()

    decision = evaluator.evaluate(
        context_df=_context(),
        baseline_result=_baseline(),
        resonance_result={"action": "SELL_QLD", "confidence": 0.91},
        overlay={"positive_score": 0.9, "negative_score": 0.0},
        effective_entropy=0.81,
        topology_state={
            "regime": "RECOVERY",
            "confidence": 0.10,
            "expected_beta": 0.72,
        },
        quality_audit=_quality(),
        base_reentry_signal=0.8,
        target_beta=0.74,
    )

    assert decision.qld_allowed is False
    assert decision.forced_bucket == "QQQ"
    assert decision.reason_code == "RESONANCE_SELL_BINDING"
    assert decision.relaxed_entry_signal == 0.0


def test_fundamental_override_can_release_resonance_sell_when_recovery_process_is_confirmed():
    evaluator = QLDPermissionEvaluator()

    decision = evaluator.evaluate(
        context_df=_context(),
        baseline_result=_baseline(tractor_prob=0.08, sidecar_prob=0.12),
        resonance_result={"action": "SELL_QLD", "confidence": 0.88},
        overlay={"positive_score": 0.82, "negative_score": 0.0},
        effective_entropy=0.31,
        topology_state={
            "regime": "RECOVERY",
            "confidence": 0.20,
            "expected_beta": 0.84,
        },
        quality_audit=_quality(),
        base_reentry_signal=0.60,
        target_beta=0.73,
    )

    assert decision.qld_allowed is True
    assert decision.forced_bucket == "QLD"
    assert decision.reason_code == "FUNDAMENTAL_OVERRIDE_RELEASE"
    assert decision.relaxed_entry_signal >= 0.85


def test_qld_permission_requires_sidecar_valid_calm_entropy_and_override_for_sub1x():
    evaluator = QLDPermissionEvaluator()

    decision = evaluator.evaluate(
        context_df=_context(),
        baseline_result=_baseline(sidecar_status="degraded_cached_trace"),
        resonance_result={"action": "BUY_QLD", "confidence": 0.88},
        overlay={"positive_score": 0.92, "negative_score": 0.0},
        effective_entropy=0.33,
        topology_state={
            "regime": "RECOVERY",
            "confidence": 0.87,
        },
        quality_audit=_quality(),
        base_reentry_signal=0.75,
        target_beta=0.71,
    )

    assert decision.qld_allowed is True
    assert decision.allow_sub1x_qld is False
    assert decision.relaxed_entry_signal == 0.0


def test_buy_qld_only_relaxes_entry_when_permission_is_already_open():
    evaluator = QLDPermissionEvaluator()

    blocked = evaluator.evaluate(
        context_df=_context(),
        baseline_result=_baseline(),
        resonance_result={"action": "BUY_QLD", "confidence": 0.95},
        overlay={"positive_score": 0.85, "negative_score": 0.0},
        effective_entropy=0.79,
        topology_state={
            "regime": "RECOVERY",
            "confidence": 0.84,
        },
        quality_audit=_quality(),
        base_reentry_signal=0.74,
        target_beta=0.69,
    )
    allowed = evaluator.evaluate(
        context_df=_context(),
        baseline_result=_baseline(),
        resonance_result={"action": "BUY_QLD", "confidence": 0.95},
        overlay={"positive_score": 0.85, "negative_score": 0.0},
        effective_entropy=0.31,
        topology_state={
            "regime": "RECOVERY",
            "confidence": 0.84,
        },
        quality_audit=_quality(),
        base_reentry_signal=0.74,
        target_beta=0.73,
    )

    assert blocked.allow_sub1x_qld is False
    assert blocked.relaxed_entry_signal == 0.0
    assert allowed.allow_sub1x_qld is True
    assert allowed.relaxed_entry_signal > blocked.relaxed_entry_signal
