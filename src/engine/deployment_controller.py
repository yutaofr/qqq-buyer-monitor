"""v8.0 Deployment Controller — decides deployment budget pace."""
from __future__ import annotations

from dataclasses import dataclass

from src.engine.feature_pipeline import FeatureSnapshot
from src.engine.risk_controller import RiskDecision
from src.models.deployment import DeploymentState
from src.models.risk import RiskState

_CAPITULATION_FAST_THRESHOLD = 30    # min capitulation score for DEPLOY_FAST
_STRESS_PAUSE_THRESHOLD = 70         # tactical stress score above which → DEPLOY_PAUSE
_PRICE_CHASING_THRESHOLD = 70        # tactical stress score for price-chasing pause
_TIER0_CAPITULATION_OVERRIDE_THRESHOLD = 70


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
    RiskState.RISK_REDUCED: DeploymentState.DEPLOY_BASE,
    RiskState.RISK_DEFENSE: DeploymentState.DEPLOY_PAUSE,
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
    "TRANSITION_STRESS": DeploymentState.DEPLOY_BASE,
    "RICH_TIGHTENING": DeploymentState.DEPLOY_BASE,
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

    Decision order (ADD §6.2):
      1. Risk ceiling hard block (DEFENSE/EXIT → PAUSE)
      2. Price-chasing or high tactical stress → PAUSE
      3. Capitulation + structural confirmation → FAST (only if risk allows)
      4. Default → BASE
    """
    v = snapshot.values
    reasons: list[dict] = []


    risk_ceiling = _RISK_DEPLOYMENT_CEILING[risk_decision.risk_state]
    capitulation = v.get("capitulation_score", 0) or 0
    tactical_stress = v.get("tactical_stress_score", 0) or 0
    can_override_tier0 = capitulation >= _TIER0_CAPITULATION_OVERRIDE_THRESHOLD
    tier0_default_ceiling = _TIER0_DEFAULT_CEILING.get(tier0_regime, DeploymentState.DEPLOY_FAST)
    tier0_override_ceiling = _TIER0_OVERRIDE_CEILING.get(tier0_regime, DeploymentState.DEPLOY_FAST)
    tier0_ceiling = tier0_override_ceiling if can_override_tier0 else tier0_default_ceiling
    effective_ceiling = _combine_ceilings(risk_ceiling, tier0_ceiling)

    # ── 1. Hard risk ceiling block ────────────────────────────────────────────
    if risk_decision.risk_state in {RiskState.RISK_DEFENSE, RiskState.RISK_EXIT}:
        reasons.append({"rule": "risk_ceiling", "risk_state": risk_decision.risk_state.value})
        return _build_decision(DeploymentState.DEPLOY_PAUSE, reasons, pause_new_cash=True)

    # ── 2. High tactical stress or price chasing → PAUSE ─────────────────────
    if tactical_stress >= _STRESS_PAUSE_THRESHOLD:
        proposed = DeploymentState.DEPLOY_PAUSE
        final = _cap_to_ceiling(proposed, effective_ceiling, reasons)
        reasons.append({"rule": "tactical_stress_pause", "stress_score": tactical_stress})
        return _build_decision(final, reasons, pause_new_cash=True)

    # ── 3. Capitulation / oversold → FAST (only under RISK_ON / RISK_NEUTRAL) ─
    if (
        capitulation >= _CAPITULATION_FAST_THRESHOLD
        and risk_decision.risk_state in {RiskState.RISK_ON, RiskState.RISK_NEUTRAL}
    ):
        proposed = DeploymentState.DEPLOY_FAST
        final = _cap_to_ceiling(proposed, effective_ceiling, reasons)
        reasons.append({"rule": "capitulation_fast", "capitulation_score": capitulation})
        return _build_decision(final, reasons, pause_new_cash=False)

    # ── 4. Tier-0 soft override for reduced-risk left-side entries ───────────
    if (
        risk_decision.risk_state == RiskState.RISK_REDUCED
        and tier0_regime in {"RICH_TIGHTENING", "TRANSITION_STRESS"}
        and can_override_tier0
    ):
        reasons.append({"rule": "tier0_capitulation_override", "tier0_regime": tier0_regime})
        final = _cap_to_ceiling(DeploymentState.DEPLOY_BASE, effective_ceiling, reasons)
        return _build_decision(final, reasons, pause_new_cash=final == DeploymentState.DEPLOY_PAUSE)

    # ── 5. RISK_REDUCED → SLOW ────────────────────────────────────────────────
    if risk_decision.risk_state == RiskState.RISK_REDUCED:
        reasons.append({"rule": "risk_reduced_slow"})
        final = _cap_to_ceiling(DeploymentState.DEPLOY_SLOW, effective_ceiling, reasons)
        return _build_decision(final, reasons, pause_new_cash=final == DeploymentState.DEPLOY_PAUSE)

    # ── 6. Default BASE ───────────────────────────────────────────────────────
    reasons.append({"rule": "default_base"})
    final = _cap_to_ceiling(DeploymentState.DEPLOY_BASE, effective_ceiling, reasons)
    return _build_decision(final, reasons, pause_new_cash=final == DeploymentState.DEPLOY_PAUSE)
