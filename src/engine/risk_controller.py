"""v7.0 Risk Controller — decides risk state from Class A macro features."""
from __future__ import annotations

from src.engine.feature_pipeline import FeatureSnapshot
from src.models.cycle import CycleDecision, CycleRegime
from src.models.risk import RiskDecision, RiskState

_MISSING_GUARD_FEATURES = (
    "credit_spread",
    "credit_acceleration",
    "liquidity_roc",
    "funding_stress",
)
_CREDIT_SPREAD_WARN = 500.0
_CREDIT_SPREAD_DANGER = 650.0
_CREDIT_ACCEL_THRESHOLD = 15.0
_LIQUIDITY_ROC_THRESHOLD = -5.0
_RISK_ON_CREDIT_SPREAD_THRESHOLD = 450.0
_DRAWDOWN_WARN = 0.20
_DRAWDOWN_DEFENSE = 0.25
_QDL_SHARE_CEILING = {
    RiskState.RISK_ON: 0.25,
    RiskState.RISK_NEUTRAL: 0.20,
    RiskState.RISK_REDUCED: 0.10,
    RiskState.RISK_DEFENSE: 0.05,
    RiskState.RISK_EXIT: 0.00,
}


def _qld_share_ceiling_for_state(risk_state: RiskState) -> float:
    return _QDL_SHARE_CEILING[risk_state]


def _count_missing_class_a(snapshot: FeatureSnapshot) -> int:
    return sum(
        1
        for name in _MISSING_GUARD_FEATURES
        if name not in snapshot.values
        or snapshot.values[name] is None
        or not snapshot.quality.get(name, {}).get("usable", True)
    )


def _build_decision(
    *,
    risk_state: RiskState,
    target_exposure_ceiling: float,
    target_cash_floor: float,
    reasons: tuple,
    tier0_applied: bool = False,
    cycle_decision: CycleDecision | None = None,
) -> RiskDecision:
    qld_share_ceiling = _qld_share_ceiling_for_state(risk_state)
    if cycle_decision is not None:
        target_exposure_ceiling = min(target_exposure_ceiling, cycle_decision.target_exposure_ceiling)
        target_cash_floor = max(target_cash_floor, 1.0 - target_exposure_ceiling)
        qld_share_ceiling = min(qld_share_ceiling, cycle_decision.qld_share_ceiling)
        reasons = reasons + tuple(cycle_decision.reasons)
    return RiskDecision(
        risk_state=risk_state,
        target_exposure_ceiling=target_exposure_ceiling,
        target_cash_floor=target_cash_floor,
        reasons=reasons,
        tier0_applied=tier0_applied,
        qld_share_ceiling=qld_share_ceiling,
    )


def decide_risk_state(
    snapshot: FeatureSnapshot,
    rolling_drawdown: float | None = None,
    tier0_regime: str = "NEUTRAL",
    cycle_decision: CycleDecision | None = None,
    drawdown_budget: float = 0.30,
) -> RiskDecision:
    """Determine risk state from Class A features, tier-0, and v10 cycle ceilings."""
    v = snapshot.values
    reasons: list[dict] = []

    if tier0_regime == "CRISIS":
        reasons.append({"rule": "tier0_crisis", "tier0_regime": tier0_regime})
        return _build_decision(
            risk_state=RiskState.RISK_EXIT,
            target_exposure_ceiling=0.50,
            target_cash_floor=0.50,
            reasons=tuple(reasons),
            tier0_applied=True,
            cycle_decision=cycle_decision,
        )

    n_missing = _count_missing_class_a(snapshot)
    if snapshot.values.get("credit_spread") is None:
        reasons.append(
            {"rule": "class_a_missing", "missing_count": n_missing, "missing_core": "credit_spread"}
        )
        return _build_decision(
            risk_state=RiskState.RISK_REDUCED,
            target_exposure_ceiling=0.80,
            target_cash_floor=0.20,
            reasons=tuple(reasons),
            cycle_decision=cycle_decision,
        )
    if n_missing >= 2:
        reasons.append({"rule": "class_a_missing", "missing_count": n_missing})
        return _build_decision(
            risk_state=RiskState.RISK_REDUCED,
            target_exposure_ceiling=0.80,
            target_cash_floor=0.20,
            reasons=tuple(reasons),
            cycle_decision=cycle_decision,
        )

    if rolling_drawdown is not None and rolling_drawdown >= drawdown_budget:
        reasons.append({"rule": "drawdown_budget_breached", "drawdown": rolling_drawdown})
        return _build_decision(
            risk_state=RiskState.RISK_EXIT,
            target_exposure_ceiling=0.50,
            target_cash_floor=0.50,
            reasons=tuple(reasons),
            cycle_decision=cycle_decision,
        )

    if cycle_decision is not None:
        if cycle_decision.cycle_regime == CycleRegime.CAPITULATION:
            reasons.append({"rule": "cycle_capitulation", "cycle_regime": cycle_decision.cycle_regime.value})
            return _build_decision(
                risk_state=RiskState.RISK_ON,
                target_exposure_ceiling=cycle_decision.target_exposure_ceiling,
                target_cash_floor=0.0,
                reasons=tuple(reasons),
                cycle_decision=cycle_decision,
            )

    if rolling_drawdown is not None:
        if rolling_drawdown >= _DRAWDOWN_DEFENSE:
            reasons.append({"rule": "drawdown_defense_band", "drawdown": rolling_drawdown})
            return _build_decision(
                risk_state=RiskState.RISK_DEFENSE,
                target_exposure_ceiling=0.70,
                target_cash_floor=0.30,
                reasons=tuple(reasons),
                cycle_decision=cycle_decision,
            )
        if rolling_drawdown >= _DRAWDOWN_WARN:
            reasons.append({"rule": "drawdown_warn_band", "drawdown": rolling_drawdown})
            return _build_decision(
                risk_state=RiskState.RISK_REDUCED,
                target_exposure_ceiling=0.80,
                target_cash_floor=0.20,
                reasons=tuple(reasons),
                cycle_decision=cycle_decision,
            )
        if cycle_decision.cycle_regime == CycleRegime.BUST:
            reasons.append({"rule": "cycle_bust", "cycle_regime": cycle_decision.cycle_regime.value})
            return _build_decision(
                risk_state=RiskState.RISK_EXIT,
                target_exposure_ceiling=0.50,
                target_cash_floor=0.50,
                reasons=tuple(reasons),
                cycle_decision=cycle_decision,
            )

    if tier0_regime == "RICH_TIGHTENING":
        reasons.append({"rule": "tier0_rich_tightening", "tier0_regime": tier0_regime})
        return _build_decision(
            risk_state=RiskState.RISK_REDUCED,
            target_exposure_ceiling=0.80,
            target_cash_floor=0.20,
            reasons=tuple(reasons),
            tier0_applied=True,
            cycle_decision=cycle_decision,
        )

    if tier0_regime == "TRANSITION_STRESS":
        reasons.append({"rule": "tier0_transition_stress", "tier0_regime": tier0_regime})
        return _build_decision(
            risk_state=RiskState.RISK_DEFENSE,
            target_exposure_ceiling=0.70,
            target_cash_floor=0.30,
            reasons=tuple(reasons),
            tier0_applied=True,
            cycle_decision=cycle_decision,
        )

    credit_spread = v.get("credit_spread")
    credit_accel = v.get("credit_acceleration")
    liq_roc = v.get("liquidity_roc")
    funding_stress = v.get("funding_stress")

    credit_danger = credit_spread is not None and credit_spread >= _CREDIT_SPREAD_DANGER
    credit_warn = credit_spread is not None and credit_spread >= _CREDIT_SPREAD_WARN
    accel_danger = credit_accel is not None and credit_accel > _CREDIT_ACCEL_THRESHOLD
    liq_danger = liq_roc is not None and liq_roc < _LIQUIDITY_ROC_THRESHOLD
    stress_flag = bool(funding_stress)

    if accel_danger and liq_danger and stress_flag:
        reasons.append(
            {
                "rule": "triple_stress",
                "credit_accel": credit_accel,
                "liq_roc": liq_roc,
                "funding_stress": funding_stress,
            }
        )
        return _build_decision(
            risk_state=RiskState.RISK_EXIT,
            target_exposure_ceiling=0.50,
            target_cash_floor=0.50,
            reasons=tuple(reasons),
            cycle_decision=cycle_decision,
        )

    stress_count = sum([accel_danger, liq_danger, credit_danger])
    stress_overlay = stress_flag and (credit_warn or accel_danger or liq_danger)
    if stress_count >= 2 or stress_overlay:
        reasons.append({"rule": "dual_stress", "stress_count": stress_count})
        return _build_decision(
            risk_state=RiskState.RISK_DEFENSE,
            target_exposure_ceiling=0.70,
            target_cash_floor=0.30,
            reasons=tuple(reasons),
            cycle_decision=cycle_decision,
        )

    if stress_count == 1 or credit_warn:
        reasons.append({"rule": "single_stress", "stress_count": stress_count})
        return _build_decision(
            risk_state=RiskState.RISK_REDUCED,
            target_exposure_ceiling=0.85,
            target_cash_floor=0.15,
            reasons=tuple(reasons),
            cycle_decision=cycle_decision,
        )

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
    risk_state = RiskState.RISK_ON if tier0_regime == "EUPHORIC" or tight_credit_bull else RiskState.RISK_NEUTRAL
    ceiling = 1.2 if risk_state == RiskState.RISK_ON else 1.0
    cash_floor = max(0.0, 1.0 - ceiling)
    decision = _build_decision(
        risk_state=risk_state,
        target_exposure_ceiling=ceiling,
        target_cash_floor=cash_floor,
        reasons=tuple(reasons),
        cycle_decision=cycle_decision,
    )
    if cycle_decision is None:
        return decision

    if cycle_decision.cycle_regime == CycleRegime.LATE_CYCLE:
        late_state = decision.risk_state
        if late_state in {RiskState.RISK_ON, RiskState.RISK_NEUTRAL}:
            late_state = RiskState.RISK_REDUCED
        return _build_decision(
            risk_state=late_state,
            target_exposure_ceiling=decision.target_exposure_ceiling,
            target_cash_floor=decision.target_cash_floor,
            reasons=decision.reasons,
            tier0_applied=decision.tier0_applied,
            cycle_decision=cycle_decision,
        )

    if cycle_decision.cycle_regime == CycleRegime.RECOVERY:
        recovery_state = RiskState.RISK_NEUTRAL if decision.risk_state == RiskState.RISK_ON else decision.risk_state
        return _build_decision(
            risk_state=recovery_state,
            target_exposure_ceiling=decision.target_exposure_ceiling,
            target_cash_floor=decision.target_cash_floor,
            reasons=decision.reasons,
            tier0_applied=decision.tier0_applied,
            cycle_decision=cycle_decision,
        )

    if cycle_decision.cycle_regime in {CycleRegime.MID_CYCLE, CycleRegime.UNQUALIFIED}:
        mid_state = RiskState.RISK_NEUTRAL if decision.risk_state == RiskState.RISK_ON else decision.risk_state
        return _build_decision(
            risk_state=mid_state,
            target_exposure_ceiling=decision.target_exposure_ceiling,
            target_cash_floor=decision.target_cash_floor,
            reasons=decision.reasons,
            tier0_applied=decision.tier0_applied,
            cycle_decision=cycle_decision,
        )

    return decision
