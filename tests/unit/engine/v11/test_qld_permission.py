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


def test_left_side_probe_opens_on_generic_exhaustion_plus_macro_relief():
    evaluator = QLDPermissionEvaluator()

    context = _context().assign(
        real_yield_10y_pct=[1.95 - (0.0025 * i) for i in range(260)],
        credit_spread_bps=[540.0 - (0.8 * i) for i in range(260)],
    )
    decision = evaluator.evaluate(
        context_df=context,
        baseline_result=_baseline(tractor_prob=0.10, sidecar_prob=0.13),
        resonance_result={"action": "HOLD", "confidence": 0.45},
        overlay={"positive_score": 0.72, "negative_score": 0.18},
        effective_entropy=0.66,
        topology_state={
            "regime": "BUST",
            "confidence": 0.28,
            "expected_beta": 0.67,
            "damage_memory": 0.74,
            "recovery_impulse": 0.31,
            "repair_persistence": 0.42,
            "bust_pressure": 0.34,
            "bullish_divergence": 0.18,
            "recovery_prob_delta": 0.014,
            "recovery_prob_acceleration": 0.006,
        },
        quality_audit=_quality(),
        base_reentry_signal=0.58,
        target_beta=0.66,
    )

    assert decision.reason_code == "LEFT_SIDE_PROBE"
    assert decision.allow_sub1x_qld is True
    assert decision.forced_bucket == "QLD"
    assert decision.entry_mode == "LEFT_SIDE_PROBE"
    assert decision.left_side_kernel["active"] is True
    assert decision.regime_specific_override["active"] is True


def test_left_side_probe_can_release_sell_binding_when_exhaustion_is_confirmed():
    evaluator = QLDPermissionEvaluator()

    context = _context().assign(
        real_yield_10y_pct=[1.95 - (0.003 * i) for i in range(260)],
        credit_spread_bps=[560.0 - (1.1 * i) for i in range(260)],
    )
    decision = evaluator.evaluate(
        context_df=context,
        baseline_result=_baseline(tractor_prob=0.09, sidecar_prob=0.12),
        resonance_result={"action": "SELL_QLD", "confidence": 0.88},
        overlay={"positive_score": 0.76, "negative_score": 0.14},
        effective_entropy=0.63,
        topology_state={
            "regime": "BUST",
            "confidence": 0.24,
            "expected_beta": 0.68,
            "damage_memory": 0.82,
            "recovery_impulse": 0.35,
            "repair_persistence": 0.46,
            "bust_pressure": 0.30,
            "bullish_divergence": 0.22,
            "recovery_prob_delta": 0.018,
            "recovery_prob_acceleration": 0.008,
        },
        quality_audit=_quality(erp_quality=0.4, capex_quality=0.4),
        base_reentry_signal=0.60,
        target_beta=0.66,
    )

    assert decision.qld_allowed is True
    assert decision.reason_code == "LEFT_SIDE_PROBE"
    assert decision.entry_mode == "LEFT_SIDE_PROBE"
    assert decision.forced_bucket == "QLD"


def test_left_side_probe_requires_stage_specific_support_not_just_generic_damage():
    evaluator = QLDPermissionEvaluator()

    flat_context = _context().assign(
        real_yield_10y_pct=[1.85 + (0.001 * i) for i in range(260)],
        credit_spread_bps=[420.0 + (0.2 * i) for i in range(260)],
    )
    decision = evaluator.evaluate(
        context_df=flat_context,
        baseline_result=_baseline(tractor_prob=0.10, sidecar_prob=0.14),
        resonance_result={"action": "HOLD", "confidence": 0.40},
        overlay={"positive_score": 0.42, "negative_score": 0.41},
        effective_entropy=0.64,
        topology_state={
            "regime": "BUST",
            "confidence": 0.26,
            "expected_beta": 0.66,
            "damage_memory": 0.72,
            "recovery_impulse": 0.29,
            "repair_persistence": 0.36,
            "bust_pressure": 0.36,
            "bullish_divergence": 0.01,
            "recovery_prob_delta": 0.010,
            "recovery_prob_acceleration": 0.004,
        },
        quality_audit=_quality(erp_quality=0.4, capex_quality=0.4),
        base_reentry_signal=0.57,
        target_beta=0.66,
    )

    assert decision.left_side_kernel["active"] is True
    assert decision.regime_specific_override["active"] is False
    assert decision.allow_sub1x_qld is False
    assert decision.reason_code == "SUB1X_BLOCKED"


def test_bubble_unwind_exhaustion_cluster_can_authorize_left_side_probe():
    evaluator = QLDPermissionEvaluator()

    context = _context().assign(
        erp_ttm_pct=[0.018 + (0.00012 * i) for i in range(260)],
        breadth_proxy=[0.12 + (0.0012 * i) for i in range(260)],
        real_yield_10y_pct=[0.011 + (0.0002 * i) for i in range(260)],
    )
    decision = evaluator.evaluate(
        context_df=context,
        baseline_result=_baseline(tractor_prob=0.11, sidecar_prob=0.15),
        resonance_result={"action": "HOLD", "confidence": 0.42},
        overlay={"positive_score": 0.68, "negative_score": 0.16},
        effective_entropy=0.67,
        topology_state={
            "regime": "BUST",
            "confidence": 0.22,
            "expected_beta": 0.65,
            "damage_memory": 0.76,
            "recovery_impulse": 0.28,
            "repair_persistence": 0.39,
            "bust_pressure": 0.40,
            "bullish_divergence": 0.15,
            "recovery_prob_delta": 0.012,
            "recovery_prob_acceleration": 0.005,
        },
        quality_audit=_quality(erp_quality=0.4, capex_quality=0.4),
        base_reentry_signal=0.56,
        target_beta=0.65,
    )

    assert decision.reason_code == "LEFT_SIDE_PROBE"
    assert decision.regime_specific_override["clusters"]["bubble_unwind_exhaustion"] is True
    assert decision.regime_specific_override["clusters"]["credit_crisis_repair"] is False


def test_credit_crisis_repair_cluster_can_authorize_left_side_probe():
    evaluator = QLDPermissionEvaluator()

    context = _context().assign(
        credit_spread_bps=[780.0 - (1.9 * i) for i in range(260)],
        real_yield_10y_pct=[0.020 - (0.00018 * i) for i in range(260)],
        breadth_proxy=[0.18 + (0.0015 * i) for i in range(260)],
    )
    decision = evaluator.evaluate(
        context_df=context,
        baseline_result=_baseline(tractor_prob=0.10, sidecar_prob=0.14),
        resonance_result={"action": "HOLD", "confidence": 0.40},
        overlay={"positive_score": 0.74, "negative_score": 0.18},
        effective_entropy=0.65,
        topology_state={
            "regime": "BUST",
            "confidence": 0.24,
            "expected_beta": 0.66,
            "damage_memory": 0.80,
            "recovery_impulse": 0.32,
            "repair_persistence": 0.44,
            "bust_pressure": 0.28,
            "bullish_divergence": 0.13,
            "recovery_prob_delta": 0.016,
            "recovery_prob_acceleration": 0.007,
        },
        quality_audit=_quality(erp_quality=0.4, capex_quality=0.4),
        base_reentry_signal=0.58,
        target_beta=0.66,
    )

    assert decision.reason_code == "LEFT_SIDE_PROBE"
    assert decision.regime_specific_override["clusters"]["credit_crisis_repair"] is True
    assert decision.regime_specific_override["clusters"]["bubble_unwind_exhaustion"] is False


def test_confirmed_recovery_keeps_expansion_path_not_left_side_probe():
    evaluator = QLDPermissionEvaluator()

    decision = evaluator.evaluate(
        context_df=_context(),
        baseline_result=_baseline(),
        resonance_result={"action": "BUY_QLD", "confidence": 0.92},
        overlay={"positive_score": 0.86, "negative_score": 0.05},
        effective_entropy=0.32,
        topology_state={
            "regime": "RECOVERY",
            "confidence": 0.84,
            "expected_beta": 0.88,
            "damage_memory": 0.40,
            "recovery_impulse": 0.24,
            "repair_persistence": 0.55,
            "bust_pressure": 0.22,
            "recovery_prob_delta": 0.018,
            "recovery_prob_acceleration": 0.007,
        },
        quality_audit=_quality(),
        base_reentry_signal=0.76,
        target_beta=0.74,
    )

    assert decision.allow_sub1x_qld is True
    assert decision.entry_mode == "RECOVERY_EXPANSION"
    assert decision.reason_code in {"SUB1X_QLD_AUTHORIZED", "FUNDAMENTAL_OVERRIDE_RELEASE"}
