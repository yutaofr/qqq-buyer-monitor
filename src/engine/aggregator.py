import logging
import math

logger = logging.getLogger(__name__)


class FullPanoramaAggregator:
    """
    v14.8 terminal coordination layer for QQQ Monitor.
    Synthesizes signals from all 4 pipelines into actionable implementation options.
    Enforces 'System Laws': Beta Floor = 0.5, Beta Ceiling = 1.25 (Aggressive).
    """

    BETA_FLOOR = 0.50
    BETA_CEILING_AGGRESSIVE = 1.25
    TRACTOR_RISK_THRESHOLD = 0.20
    SIDECAR_RISK_THRESHOLD = 0.15
    CALM_THRESHOLD = 0.05

    @staticmethod
    def _coerce_prob(result: dict | None) -> float:
        try:
            probability = float((result or {}).get("prob", 0.0))
        except (TypeError, ValueError):
            return 0.0
        return probability if math.isfinite(probability) else 0.0

    @staticmethod
    def _probe_valid(result: dict | None) -> bool:
        status = str((result or {}).get("status", "unknown"))
        return status.startswith("success")

    @classmethod
    def aggregate(cls, bayesian_runtime: dict, baseline_result: dict) -> dict:
        """
        Input:
            bayesian_runtime: results from V11Conductor.daily_run()
            baseline_result: results from run_baseline_inference()
        """
        # 1. Official Standard (The decision made by Bayesian + Overlay)
        standard_beta = float(bayesian_runtime.get("target_beta", 1.0))

        # 2. Extract Diagnostic Probes
        tractor_result = baseline_result.get("tractor", {})
        sidecar_result = baseline_result.get("sidecar", {})

        t_prob = cls._coerce_prob(tractor_result)
        s_prob = cls._coerce_prob(sidecar_result)
        tractor_valid = cls._probe_valid(tractor_result)
        sidecar_valid = cls._probe_valid(sidecar_result)
        calm_eligible = tractor_valid and sidecar_valid

        # 3. Indicator 2: Protective (S4)
        # S4 is standard unless risk triggers, then it's the Floor law (0.50)
        risk_triggered = t_prob > cls.TRACTOR_RISK_THRESHOLD or s_prob > cls.SIDECAR_RISK_THRESHOLD
        protective_beta = cls.BETA_FLOOR if risk_triggered else standard_beta
        # Safety enforcement of the system law
        protective_beta = max(cls.BETA_FLOOR, protective_beta)

        # 4. Indicator 3: Aggressive (S5)
        # S5 is Standard with ceiling unlocked if calm, but respects the S4 protective logic if risk exists
        is_calm = calm_eligible and t_prob < cls.CALM_THRESHOLD and s_prob < cls.CALM_THRESHOLD
        if risk_triggered:
            aggressive_beta = protective_beta  # Risk-override
        elif is_calm:
            aggressive_beta = max(standard_beta, cls.BETA_CEILING_AGGRESSIVE)
        else:
            aggressive_beta = standard_beta
        # Safety enforcement
        aggressive_beta = max(cls.BETA_FLOOR, aggressive_beta)

        # 5. Ensemble Verdict & Divergence Detection
        # Check if Bayesian thinks "Recovery" but Sidecar thinks "Risk"
        overlay_floor_active = bayesian_runtime.get("is_floor_active", False)

        if risk_triggered:
            verdict = "PROTECTIVE"
            verdict_label = "🚨 PROTECT (GUARD at 0.5)"
        elif is_calm:
            verdict = "AGGRESSIVE"
            verdict_label = "🚀 AGGRESSIVE (S5 Suggestion)"
        elif not calm_eligible:
            verdict = "NEUTRAL"
            verdict_label = "⚠️ NEUTRAL (Diagnostics Incomplete)"
        elif overlay_floor_active and not risk_triggered:
            verdict = "DIVERGENT"
            verdict_label = "⚠️ DIVERGENT (Overlay Active / Diagnostics Calm)"
        else:
            verdict = "NEUTRAL"
            verdict_label = "⚖️ NEUTRAL (Standard Pipeline)"

        return {
            "standard_beta": round(standard_beta, 3),
            "s4_protective_beta": round(protective_beta, 3),
            "s5_aggressive_beta": round(aggressive_beta, 3),
            "ensemble_verdict": verdict,
            "ensemble_verdict_label": verdict_label,
            "risk_triggered": risk_triggered,
            "is_calm": is_calm,
            "tractor_valid": tractor_valid,
            "sidecar_valid": sidecar_valid,
            "calm_eligible": calm_eligible,
        }
