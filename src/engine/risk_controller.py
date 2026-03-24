"""v7.0 Risk Controller — decides risk state from Class A macro features."""
from __future__ import annotations

from dataclasses import dataclass

from src.engine.feature_pipeline import _CLASS_A, FeatureSnapshot
from src.models import CurrentPortfolioState
from src.models.risk import RiskState


@dataclass(frozen=True)
class RiskDecision:
    """Output of the Risk Controller for one market day."""
    risk_state: RiskState
    target_exposure_ceiling: float   # max effective exposure allowed (e.g. 0.90)
    target_cash_floor: float         # minimum cash allocation (e.g. 0.10)
    reasons: tuple                   # immutable sequence of evidence dicts


# Risk threshold constants (Class A hard rules)
_CREDIT_SPREAD_WARN = 400.0          # bps – elevated but not critical
_CREDIT_SPREAD_DANGER = 500.0        # bps – danger zone
_CREDIT_ACCEL_THRESHOLD = 15.0       # bps/week acceleration
_LIQUIDITY_ROC_THRESHOLD = -2.0      # % weekly change (negative = contraction)
_DRAWDOWN_WARN = 0.20
_DRAWDOWN_DEFENSE = 0.25
_DRAWDOWN_EXIT = 0.30


def _count_missing_class_a(snapshot: FeatureSnapshot) -> int:
    """Count how many Class A features are None / unusable."""
    return sum(
        1 for name in _CLASS_A
        if name in snapshot.values and (
            snapshot.values[name] is None
            or not snapshot.quality.get(name, {}).get("usable", True)
        )
    )


def decide_risk_state(
    snapshot: FeatureSnapshot,
    portfolio: CurrentPortfolioState,
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

    # ── 1. Missing Class A guard (SRD §8.2) ─────────────────────────────────
    n_missing = _count_missing_class_a(snapshot)
    if n_missing >= 2:
        reasons.append({"rule": "class_a_missing", "missing_count": n_missing})
        return RiskDecision(
            risk_state=RiskState.RISK_REDUCED,
            target_exposure_ceiling=0.60,
            target_cash_floor=0.40,
            reasons=tuple(reasons),
        )

    # ── 2. Drawdown budget hard constraint ───────────────────────────────────
    portfolio_drawdown = getattr(portfolio, "rolling_drawdown", getattr(portfolio, "_rolling_drawdown", None))
    if portfolio_drawdown is not None:
        if portfolio_drawdown >= drawdown_budget:
            reasons.append({"rule": "drawdown_budget_breached", "drawdown": portfolio_drawdown})
            return RiskDecision(
                risk_state=RiskState.RISK_EXIT,
                target_exposure_ceiling=0.25,
                target_cash_floor=0.75,
                reasons=tuple(reasons),
            )
        if portfolio_drawdown >= _DRAWDOWN_DEFENSE:
            reasons.append({"rule": "drawdown_defense_band", "drawdown": portfolio_drawdown})

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
            target_exposure_ceiling=0.25,
            target_cash_floor=0.75,
            reasons=tuple(reasons),
        )

    # ── 4. Dual stress → RISK_DEFENSE ────────────────────────────────────────
    stress_count = sum([accel_danger, liq_danger, stress_flag, credit_danger])
    if stress_count >= 2:
        reasons.append({"rule": "dual_stress", "stress_count": stress_count})
        return RiskDecision(
            risk_state=RiskState.RISK_DEFENSE,
            target_exposure_ceiling=0.50,
            target_cash_floor=0.50,
            reasons=tuple(reasons),
        )

    # ── 5. Single-side deterioration → RISK_REDUCED ──────────────────────────
    if stress_count == 1 or credit_warn:
        reasons.append({"rule": "single_stress", "stress_count": stress_count})
        return RiskDecision(
            risk_state=RiskState.RISK_REDUCED,
            target_exposure_ceiling=0.75,
            target_cash_floor=0.25,
            reasons=tuple(reasons),
        )

    # ── 6. Clean environment ──────────────────────────────────────────────────
    reasons.append({"rule": "clean_macro"})
    return RiskDecision(
        risk_state=RiskState.RISK_NEUTRAL,
        target_exposure_ceiling=0.90,
        target_cash_floor=0.10,
        reasons=tuple(reasons),
    )
