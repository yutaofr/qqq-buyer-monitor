"""v7.0 Risk Controller — decides risk state from Class A macro features."""
from __future__ import annotations

from src.engine.feature_pipeline import FeatureSnapshot
from src.models.risk import RiskDecision, RiskState

# Risk threshold constants (Class A hard rules)
_MISSING_GUARD_FEATURES = (
    "credit_spread",
    "credit_acceleration",
    "liquidity_roc",
    "funding_stress",
)
_CREDIT_SPREAD_WARN = 500.0          # bps – elevated but still recoverable
_CREDIT_SPREAD_DANGER = 650.0        # bps – true danger zone
_CREDIT_ACCEL_THRESHOLD = 15.0       # % over 10d acceleration window
_LIQUIDITY_ROC_THRESHOLD = -5.0      # % 4w change (negative = contraction)
_RISK_ON_CREDIT_SPREAD_THRESHOLD = 450.0
_DRAWDOWN_WARN = 0.20
_DRAWDOWN_DEFENSE = 0.25
_DRAWDOWN_EXIT = 0.30


def _count_missing_class_a(snapshot: FeatureSnapshot) -> int:
    """Count how many hard-decision inputs are None / unusable / absent."""
    return sum(
        1 for name in _MISSING_GUARD_FEATURES
        if name not in snapshot.values
        or snapshot.values[name] is None
        or not snapshot.quality.get(name, {}).get("usable", True)
    )


def decide_risk_state(
    snapshot: FeatureSnapshot,
    rolling_drawdown: float | None = None,
    tier0_regime: str = "NEUTRAL",
    drawdown_budget: float = 0.30,
) -> RiskDecision:
    """
    Determine risk state from Class A features only (SRD §10.1–10.2, AC-5).

    Decision order (SRD §6.1):
      1. Missing Class A data → conservative degradation
      2. Hard drawdown budget breach
      3. Triple-stress: credit_accel + liq_roc + funding_stress
      4. Dual-stress combinations
      5. Single-side deterioration
      6. Clean → RISK_NEUTRAL / RISK_ON
    """
    v = snapshot.values
    reasons = []

    # ── 0. Tier-0 hard constraint (v8.1) ────────────────────────────────────
    if tier0_regime == "CRISIS":
        reasons.append({"rule": "tier0_crisis", "tier0_regime": tier0_regime})
        return RiskDecision(
            risk_state=RiskState.RISK_EXIT,
            target_exposure_ceiling=0.50,
            target_cash_floor=0.50,
            reasons=tuple(reasons),
            tier0_applied=True,
        )

    if tier0_regime == "RICH_TIGHTENING":
        reasons.append({"rule": "tier0_rich_tightening", "tier0_regime": tier0_regime})
        return RiskDecision(
            risk_state=RiskState.RISK_REDUCED,
            target_exposure_ceiling=0.80,
            target_cash_floor=0.20,
            reasons=tuple(reasons),
            tier0_applied=True,
        )

    if tier0_regime == "TRANSITION_STRESS":
        reasons.append({"rule": "tier0_transition_stress", "tier0_regime": tier0_regime})
        return RiskDecision(
            risk_state=RiskState.RISK_DEFENSE,
            target_exposure_ceiling=0.70,
            target_cash_floor=0.30,
            reasons=tuple(reasons),
            tier0_applied=True,
        )

    # ── 1. Missing Class A guard (SRD §8.2) ─────────────────────────────────
    n_missing = _count_missing_class_a(snapshot)
    if snapshot.values.get("credit_spread") is None:
        reasons.append({"rule": "class_a_missing", "missing_count": n_missing, "missing_core": "credit_spread"})
        return RiskDecision(
            risk_state=RiskState.RISK_REDUCED,
            target_exposure_ceiling=0.80,
            target_cash_floor=0.20,
            reasons=tuple(reasons),
        )
    if n_missing >= 2:
        reasons.append({"rule": "class_a_missing", "missing_count": n_missing})
        return RiskDecision(
            risk_state=RiskState.RISK_REDUCED,
            target_exposure_ceiling=0.80,
            target_cash_floor=0.20,
            reasons=tuple(reasons),
        )

    # ── 2. Drawdown budget hard constraint ───────────────────────────────────
    if rolling_drawdown is not None:
        if rolling_drawdown >= drawdown_budget:
            reasons.append({"rule": "drawdown_budget_breached", "drawdown": rolling_drawdown})
            return RiskDecision(
                risk_state=RiskState.RISK_EXIT,
                target_exposure_ceiling=0.50,
                target_cash_floor=0.50,
                reasons=tuple(reasons),
            )
        if rolling_drawdown >= _DRAWDOWN_DEFENSE:
            reasons.append({"rule": "drawdown_defense_band", "drawdown": rolling_drawdown})
            return RiskDecision(
                risk_state=RiskState.RISK_DEFENSE,
                target_exposure_ceiling=0.70,
                target_cash_floor=0.30,
                reasons=tuple(reasons),
            )
        if rolling_drawdown >= _DRAWDOWN_WARN:
            reasons.append({"rule": "drawdown_warn_band", "drawdown": rolling_drawdown})
            return RiskDecision(
                risk_state=RiskState.RISK_REDUCED,
                target_exposure_ceiling=0.80,
                target_cash_floor=0.20,
                reasons=tuple(reasons),
            )

    # ── Extract Class A signals ──────────────────────────────────────────────
    credit_spread = v.get("credit_spread")
    credit_accel = v.get("credit_acceleration")
    liq_roc = v.get("liquidity_roc")
    funding_stress = v.get("funding_stress")

    # Boolean stress flags per signal
    credit_danger = (credit_spread is not None and credit_spread >= _CREDIT_SPREAD_DANGER)
    credit_warn = (credit_spread is not None and credit_spread >= _CREDIT_SPREAD_WARN)
    accel_danger = (credit_accel is not None and credit_accel > _CREDIT_ACCEL_THRESHOLD)
    liq_danger = (liq_roc is not None and liq_roc < _LIQUIDITY_ROC_THRESHOLD)
    stress_flag = bool(funding_stress)

    # ── 3. Triple stress → RISK_EXIT ────────────────────────────────────────
    if accel_danger and liq_danger and stress_flag:
        reasons.append({"rule": "triple_stress", "credit_accel": credit_accel,
                        "liq_roc": liq_roc, "funding_stress": funding_stress})
        return RiskDecision(
            risk_state=RiskState.RISK_EXIT,
            target_exposure_ceiling=0.50,
            target_cash_floor=0.50,
            reasons=tuple(reasons),
        )

    # ── 4. Dual stress → RISK_DEFENSE ────────────────────────────────────────
    stress_count = sum([accel_danger, liq_danger, credit_danger])
    stress_overlay = stress_flag and (credit_warn or accel_danger or liq_danger)
    if stress_count >= 2 or stress_overlay:
        reasons.append({"rule": "dual_stress", "stress_count": stress_count})
        return RiskDecision(
            risk_state=RiskState.RISK_DEFENSE,
            target_exposure_ceiling=0.70,
            target_cash_floor=0.30,
            reasons=tuple(reasons),
        )

    # ── 5. Single-side deterioration → RISK_REDUCED ──────────────────────────
    if stress_count == 1 or credit_warn:
        reasons.append({"rule": "single_stress", "stress_count": stress_count})
        return RiskDecision(
            risk_state=RiskState.RISK_REDUCED,
            target_exposure_ceiling=0.85,
            target_cash_floor=0.15,
            reasons=tuple(reasons),
        )

    # ── 6. Clean environment ──────────────────────────────────────────────────
    reasons.append({"rule": "clean_macro"})

    tight_credit_bull = (
        tier0_regime == "NEUTRAL"
        and credit_spread is not None
        and credit_spread < _RISK_ON_CREDIT_SPREAD_THRESHOLD
        and (credit_accel is None or credit_accel <= 0.0)
        and (liq_roc is None or liq_roc >= _LIQUIDITY_ROC_THRESHOLD)
        and not stress_flag
        and (rolling_drawdown is None or rolling_drawdown < _DRAWDOWN_WARN)
    )
    risk_state = (
        RiskState.RISK_ON
        if tier0_regime == "EUPHORIC" or tight_credit_bull
        else RiskState.RISK_NEUTRAL
    )
    ceiling = 1.2 if risk_state == RiskState.RISK_ON else 1.0
    cash_floor = max(0.0, 1.0 - ceiling)

    return RiskDecision(
        risk_state=risk_state,
        target_exposure_ceiling=ceiling,
        target_cash_floor=cash_floor,
        reasons=tuple(reasons),
    )
