import logging

logger = logging.getLogger(__name__)


class FullPanoramaAggregator:
    """
    v14.8 terminal coordination layer for QQQ Monitor.
    Synthesizes signals from all 4 pipelines into actionable implementation options.
    Enforces 'System Laws': Beta Floor = 0.5, Beta Ceiling = 1.25 (Aggressive).
    """

    BETA_FLOOR = 0.50
    BETA_CEILING_AGGRESSIVE = 1.25
    TRACTOR_RISK_THRESHOLD = 0.25
    SIDECAR_RISK_THRESHOLD = 0.20
    CALM_THRESHOLD = 0.10

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
        t_prob = float(baseline_result.get("tractor", {}).get("prob", 0.0))
        s_prob = float(baseline_result.get("sidecar", {}).get("prob", 0.0))

        # 3. Indicator 2: Protective (S4)
        # S4 is standard unless risk triggers, then it's the Floor law (0.50)
        risk_triggered = t_prob > cls.TRACTOR_RISK_THRESHOLD or s_prob > cls.SIDECAR_RISK_THRESHOLD
        protective_beta = cls.BETA_FLOOR if risk_triggered else standard_beta
        # Safety enforcement of the system law
        protective_beta = max(cls.BETA_FLOOR, protective_beta)

        # 4. Indicator 3: Aggressive (S5)
        # S5 is Standard with ceiling unlocked if calm, but respects the S4 protective logic if risk exists
        is_calm = t_prob < cls.CALM_THRESHOLD and s_prob < cls.CALM_THRESHOLD
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
        }
