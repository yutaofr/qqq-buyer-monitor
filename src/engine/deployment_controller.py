"""v8.0 Deployment Controller — decides deployment budget pace."""
from __future__ import annotations

from dataclasses import dataclass

from src.engine.feature_pipeline import FeatureSnapshot
from src.engine.risk_controller import RiskDecision
from src.models.deployment import DeploymentState
from src.models.risk import RiskState

_CAPITULATION_FAST_THRESHOLD = 30
_STRESS_PAUSE_THRESHOLD = 70
_PRICE_CHASING_THRESHOLD = 70
_TIER0_CAPITULATION_OVERRIDE_THRESHOLD = 70
_CREDIT_SPREAD_STRESS = 500.0
_CREDIT_SPREAD_CRISIS = 650.0
_CREDIT_ACCEL_STRESS = 15.0
_LIQUIDITY_STRESS = -5.0
_FUNDING_STRESS_SLOW_THRESHOLD = 0.10
_LEFT_TAIL_FAST_DRAWDOWN_THRESHOLD = 0.12
_LEFT_TAIL_FAST_TWENTY_DAY_RETURN_THRESHOLD = -0.08
_SHALLOW_PULLBACK_FAST_DRAWDOWN_THRESHOLD = 0.08
_SHALLOW_PULLBACK_FAST_FIVE_DAY_RETURN_THRESHOLD = 0.0
_STRESS_DRAWDOWN_SLOW_THRESHOLD = 0.15
_DEEP_DRAWDOWN_PAUSE_THRESHOLD = 0.25
_SHALLOW_RICH_TIGHTENING_BASE_THRESHOLD = 0.15


@dataclass(frozen=True)
class DeploymentDecision:
    """Output of the Deployment Controller for one market day."""
    deployment_state: DeploymentState
    dca_multiplier: float            # 0.0 (pause) → 1.0 (base) → 2.0 (fast)
    pause_new_cash: bool
    reasons: tuple                   # immutable sequence of evidence dicts


# Risk state → maximum allowed deployment state (SRD §7.3)
_RISK_DEPLOYMENT_CEILING: dict[RiskState, DeploymentState] = {
    RiskState.RISK_ON: DeploymentState.DEPLOY_FAST,
    RiskState.RISK_NEUTRAL: DeploymentState.DEPLOY_FAST,
    RiskState.RISK_REDUCED: DeploymentState.DEPLOY_FAST,
    RiskState.RISK_DEFENSE: DeploymentState.DEPLOY_FAST,
    RiskState.RISK_EXIT: DeploymentState.DEPLOY_PAUSE,
}

_TIER0_DEFAULT_CEILING: dict[str, DeploymentState] = {
    "CRISIS": DeploymentState.DEPLOY_PAUSE,
    "TRANSITION_STRESS": DeploymentState.DEPLOY_SLOW,
    "RICH_TIGHTENING": DeploymentState.DEPLOY_SLOW,
    "NEUTRAL": DeploymentState.DEPLOY_FAST,
    "EUPHORIC": DeploymentState.DEPLOY_FAST,
}

_TIER0_OVERRIDE_CEILING: dict[str, DeploymentState] = {
    "CRISIS": DeploymentState.DEPLOY_PAUSE,
    "TRANSITION_STRESS": DeploymentState.DEPLOY_FAST,
    "RICH_TIGHTENING": DeploymentState.DEPLOY_FAST,
    "NEUTRAL": DeploymentState.DEPLOY_FAST,
    "EUPHORIC": DeploymentState.DEPLOY_FAST,
}

_DEPLOY_RANK = {
    DeploymentState.DEPLOY_FAST: 4,
    DeploymentState.DEPLOY_RECOVER: 3,
    DeploymentState.DEPLOY_BASE: 2,
    DeploymentState.DEPLOY_SLOW: 1,
    DeploymentState.DEPLOY_PAUSE: 0,
}


def _cap_to_ceiling(
    proposed: DeploymentState,
    ceiling: DeploymentState,
    reasons: list,
) -> DeploymentState:
    """Lower deployment state if it exceeds the imposed ceiling."""
    if _DEPLOY_RANK[proposed] > _DEPLOY_RANK[ceiling]:
        reasons.append({"rule": "risk_ceiling", "proposed": proposed.value, "ceiling": ceiling.value})
        return ceiling
    return proposed


def _combine_ceilings(
    risk_ceiling: DeploymentState,
    tier0_ceiling: DeploymentState,
) -> DeploymentState:
    """Use the stricter of the risk and tier-0 ceilings."""
    return risk_ceiling if _DEPLOY_RANK[risk_ceiling] <= _DEPLOY_RANK[tier0_ceiling] else tier0_ceiling


def _build_decision(
    deployment_state: DeploymentState,
    reasons: list[dict],
    *,
    pause_new_cash: bool = False,
) -> DeploymentDecision:
    multiplier_map = {
        DeploymentState.DEPLOY_PAUSE: 0.0,
        DeploymentState.DEPLOY_SLOW: 0.5,
        DeploymentState.DEPLOY_BASE: 1.0,
        DeploymentState.DEPLOY_RECOVER: 1.0,
        DeploymentState.DEPLOY_FAST: 2.0,
    }
    return DeploymentDecision(
        deployment_state=deployment_state,
        dca_multiplier=multiplier_map[deployment_state],
        pause_new_cash=pause_new_cash,
        reasons=tuple(reasons),
    )


def decide_deployment_state(
    snapshot: FeatureSnapshot,
    risk_decision: RiskDecision,
    tier0_regime: str = "NEUTRAL",
    available_new_cash: float = 0.0,
) -> DeploymentDecision:
    """
    Determine cash deployment pace (SRD §10.3–10.4, §7.3).

    Uses Class B data. Cannot exceed Risk Controller exposure ceiling.

    Decision order:
      1. Hard blocks: EXIT, missing macro spread, tactical stress, deep drawdown
      2. Confirmed left-tail weakness → FAST
      3. Structural stress / deep-but-not-crisis drawdown → SLOW
      4. Shallow pullback weakness → FAST
      5. Risk-state defaults (DEFENSE → SLOW, shallow RICH_TIGHTENING → BASE)
      6. Otherwise BASE
    """
    v = snapshot.values
    reasons: list[dict] = []

    risk_ceiling = _RISK_DEPLOYMENT_CEILING[risk_decision.risk_state]
    credit_spread = v.get("credit_spread")
    credit_accel = float(v.get("credit_acceleration", 0.0) or 0.0)
    liquidity_roc = float(v.get("liquidity_roc", 0.0) or 0.0)
    funding_stress = bool(v.get("funding_stress") or False)
    tactical_stress = v.get("tactical_stress_score", 0) or 0
    rolling_drawdown = v.get("rolling_drawdown")
    five_day_return = v.get("five_day_return")
    twenty_day_return = v.get("twenty_day_return")

    has_left_tail_confirmation = (
        rolling_drawdown is not None
        and rolling_drawdown >= _LEFT_TAIL_FAST_DRAWDOWN_THRESHOLD
        and twenty_day_return is not None
        and float(twenty_day_return) <= _LEFT_TAIL_FAST_TWENTY_DAY_RETURN_THRESHOLD
    )
    has_shallow_pullback_confirmation = (
        rolling_drawdown is not None
        and rolling_drawdown >= _SHALLOW_PULLBACK_FAST_DRAWDOWN_THRESHOLD
        and five_day_return is not None
        and float(five_day_return) <= _SHALLOW_PULLBACK_FAST_FIVE_DAY_RETURN_THRESHOLD
    )
    can_override_tier0 = has_left_tail_confirmation or has_shallow_pullback_confirmation
    tier0_default_ceiling = _TIER0_DEFAULT_CEILING.get(tier0_regime, DeploymentState.DEPLOY_FAST)
    tier0_override_ceiling = _TIER0_OVERRIDE_CEILING.get(tier0_regime, DeploymentState.DEPLOY_FAST)
    tier0_ceiling = tier0_override_ceiling if can_override_tier0 else tier0_default_ceiling
    effective_ceiling = _combine_ceilings(risk_ceiling, tier0_ceiling)

    # ── 1. Hard risk ceiling block ────────────────────────────────────────────
    if risk_decision.risk_state == RiskState.RISK_EXIT:
        reasons.append({"rule": "risk_ceiling", "risk_state": risk_decision.risk_state.value})
        return _build_decision(DeploymentState.DEPLOY_PAUSE, reasons, pause_new_cash=True)

    if credit_spread is None:
        reasons.append({"rule": "missing_credit_spread_pause"})
        return _build_decision(DeploymentState.DEPLOY_PAUSE, reasons, pause_new_cash=True)

    # ── 2. High tactical stress or price chasing → PAUSE ─────────────────────
    if tactical_stress >= _STRESS_PAUSE_THRESHOLD:
        proposed = DeploymentState.DEPLOY_PAUSE
        final = _cap_to_ceiling(proposed, effective_ceiling, reasons)
        reasons.append({"rule": "tactical_stress_pause", "stress_score": tactical_stress})
        return _build_decision(final, reasons, pause_new_cash=True)

    if float(credit_spread) >= _CREDIT_SPREAD_CRISIS or (
        rolling_drawdown is not None and rolling_drawdown >= _DEEP_DRAWDOWN_PAUSE_THRESHOLD
    ):
        reasons.append(
            {
                "rule": "deep_drawdown_pause",
                "credit_spread": float(credit_spread),
                "rolling_drawdown": rolling_drawdown,
            }
        )
        proposed = DeploymentState.DEPLOY_PAUSE
        final = _cap_to_ceiling(proposed, effective_ceiling, reasons)
        return _build_decision(final, reasons, pause_new_cash=True)

    # ── 3. Confirmed left-tail weakness → FAST ────────────────────────────────
    if has_left_tail_confirmation:
        proposed = DeploymentState.DEPLOY_FAST
        final = _cap_to_ceiling(proposed, effective_ceiling, reasons)
        reasons.append(
            {
                "rule": "left_tail_fast",
                "rolling_drawdown": rolling_drawdown,
                "twenty_day_return": float(twenty_day_return),
            }
        )
        return _build_decision(final, reasons, pause_new_cash=False)

    # ── 4. Structural stress still deploys slowly unless left-tail confirms ──
    if (
        float(credit_spread) >= _CREDIT_SPREAD_STRESS
        or credit_accel > _CREDIT_ACCEL_STRESS
        or liquidity_roc <= _LIQUIDITY_STRESS
        or (rolling_drawdown is not None and rolling_drawdown >= _STRESS_DRAWDOWN_SLOW_THRESHOLD)
        or (
            funding_stress
            and rolling_drawdown is not None
            and rolling_drawdown >= _FUNDING_STRESS_SLOW_THRESHOLD
        )
    ):
        reasons.append(
            {
                "rule": "stress_slow",
                "credit_spread": float(credit_spread),
                "credit_acceleration": credit_accel,
                "liquidity_roc": liquidity_roc,
                "rolling_drawdown": rolling_drawdown,
                "funding_stress": funding_stress,
            }
        )
        final = _cap_to_ceiling(DeploymentState.DEPLOY_SLOW, effective_ceiling, reasons)
        return _build_decision(final, reasons, pause_new_cash=final == DeploymentState.DEPLOY_PAUSE)

    # ── 5. Shallow pullback weakness → FAST ───────────────────────────────────
    if has_shallow_pullback_confirmation:
        proposed = DeploymentState.DEPLOY_FAST
        final = _cap_to_ceiling(proposed, effective_ceiling, reasons)
        reasons.append(
            {
                "rule": "pullback_fast",
                "rolling_drawdown": rolling_drawdown,
                "five_day_return": float(five_day_return),
            }
        )
        return _build_decision(final, reasons, pause_new_cash=False)

    # ── 6. TRANSITION_STRESS/DEFENSE defaults to SLOW, not full PAUSE ────────
    if risk_decision.risk_state == RiskState.RISK_DEFENSE:
        reasons.append({"rule": "risk_defense_slow"})
        final = _cap_to_ceiling(DeploymentState.DEPLOY_SLOW, effective_ceiling, reasons)
        return _build_decision(final, reasons, pause_new_cash=final == DeploymentState.DEPLOY_PAUSE)

    # ── 7. Shallow rich-tightening pullbacks stay investable at BASE ─────────
    if (
        risk_decision.risk_state == RiskState.RISK_REDUCED
        and tier0_regime == "RICH_TIGHTENING"
        and (rolling_drawdown is None or rolling_drawdown < _SHALLOW_RICH_TIGHTENING_BASE_THRESHOLD)
    ):
        reasons.append({"rule": "rich_tightening_base"})
        return _build_decision(DeploymentState.DEPLOY_BASE, reasons, pause_new_cash=False)

    # ── 8. RISK_REDUCED → SLOW ────────────────────────────────────────────────
    if risk_decision.risk_state == RiskState.RISK_REDUCED:
        reasons.append({"rule": "risk_reduced_slow"})
        final = _cap_to_ceiling(DeploymentState.DEPLOY_SLOW, effective_ceiling, reasons)
        return _build_decision(final, reasons, pause_new_cash=final == DeploymentState.DEPLOY_PAUSE)

    # ── 9. Default BASE ───────────────────────────────────────────────────────
    reasons.append({"rule": "default_base"})
    final = _cap_to_ceiling(DeploymentState.DEPLOY_BASE, effective_ceiling, reasons)
    return _build_decision(final, reasons, pause_new_cash=final == DeploymentState.DEPLOY_PAUSE)
