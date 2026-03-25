"""v7.0 Deployment Controller — decides new cash deployment pace."""
from __future__ import annotations

from dataclasses import dataclass

from src.engine.feature_pipeline import FeatureSnapshot
from src.engine.risk_controller import RiskDecision
from src.models.deployment import DeploymentState
from src.models.risk import RiskState

_CAPITULATION_FAST_THRESHOLD = 30    # min capitulation score for DEPLOY_FAST
_STRESS_PAUSE_THRESHOLD = 70         # tactical stress score above which → DEPLOY_PAUSE
_PRICE_CHASING_THRESHOLD = 70        # tactical stress score for price-chasing pause


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
    RiskState.RISK_REDUCED: DeploymentState.DEPLOY_SLOW,
    RiskState.RISK_DEFENSE: DeploymentState.DEPLOY_PAUSE,
    RiskState.RISK_EXIT: DeploymentState.DEPLOY_PAUSE,
}

_DEPLOY_RANK = {
    DeploymentState.DEPLOY_FAST: 4,
    DeploymentState.DEPLOY_RECOVER: 3,
    DeploymentState.DEPLOY_BASE: 2,
    DeploymentState.DEPLOY_SLOW: 1,
    DeploymentState.DEPLOY_PAUSE: 0,
}


def _cap_to_risk_ceiling(
    proposed: DeploymentState,
    ceiling: DeploymentState,
    reasons: list,
) -> DeploymentState:
    """Lower deployment state if it exceeds the risk-imposed ceiling."""
    if _DEPLOY_RANK[proposed] > _DEPLOY_RANK[ceiling]:
        reasons.append({"rule": "risk_ceiling", "proposed": proposed.value, "ceiling": ceiling.value})
        return ceiling
    return proposed


def decide_deployment_state(
    snapshot: FeatureSnapshot,
    risk_decision: RiskDecision,
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

    # ── 1. Hard risk ceiling block ────────────────────────────────────────────
    if risk_decision.risk_state in {RiskState.RISK_DEFENSE, RiskState.RISK_EXIT}:
        reasons.append({"rule": "risk_ceiling", "risk_state": risk_decision.risk_state.value})
        return DeploymentDecision(
            deployment_state=DeploymentState.DEPLOY_PAUSE,
            dca_multiplier=0.0,
            pause_new_cash=True,
            reasons=tuple(reasons),
        )

    tactical_stress = v.get("tactical_stress_score", 0) or 0
    capitulation = v.get("capitulation_score", 0) or 0

    # ── 2. High tactical stress or price chasing → PAUSE ─────────────────────
    if tactical_stress >= _STRESS_PAUSE_THRESHOLD:
        proposed = DeploymentState.DEPLOY_PAUSE
        final = _cap_to_risk_ceiling(proposed, risk_ceiling, reasons)
        reasons.append({"rule": "tactical_stress_pause", "stress_score": tactical_stress})
        return DeploymentDecision(
            deployment_state=final,
            dca_multiplier=0.0,
            pause_new_cash=True,
            reasons=tuple(reasons),
        )

    # ── 3. Capitulation / oversold → FAST (only under RISK_ON / RISK_NEUTRAL) ─
    if (
        capitulation >= _CAPITULATION_FAST_THRESHOLD
        and risk_decision.risk_state in {RiskState.RISK_ON, RiskState.RISK_NEUTRAL}
    ):
        proposed = DeploymentState.DEPLOY_FAST
        final = _cap_to_risk_ceiling(proposed, risk_ceiling, reasons)
        reasons.append({"rule": "capitulation_fast", "capitulation_score": capitulation})
        return DeploymentDecision(
            deployment_state=final,
            dca_multiplier=2.0 if final == DeploymentState.DEPLOY_FAST else 0.5,
            pause_new_cash=False,
            reasons=tuple(reasons),
        )

    # ── 4. RISK_REDUCED → SLOW ────────────────────────────────────────────────
    if risk_decision.risk_state == RiskState.RISK_REDUCED:
        reasons.append({"rule": "risk_reduced_slow"})
        return DeploymentDecision(
            deployment_state=DeploymentState.DEPLOY_SLOW,
            dca_multiplier=0.5,
            pause_new_cash=False,
            reasons=tuple(reasons),
        )

    # ── 5. Default BASE ───────────────────────────────────────────────────────
    reasons.append({"rule": "default_base"})
    return DeploymentDecision(
        deployment_state=DeploymentState.DEPLOY_BASE,
        dca_multiplier=1.0,
        pause_new_cash=False,
        reasons=tuple(reasons),
    )
