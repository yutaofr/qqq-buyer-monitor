"""v8.0 execution policy — beta recommendation only, no amount output."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.engine.runtime_selector import RuntimeSelection
from src.models import TargetAllocationState
from src.models.risk import RiskDecision, RiskState


@dataclass(frozen=True)
class BetaRecommendation:
    """Recommend target portfolio beta and whether an adjustment is warranted."""

    target_beta: float
    recommended_qqq_pct: float
    recommended_qld_pct: float
    recommended_cash_pct: float
    should_adjust: bool
    adjustment_reason: str
    current_risk_state: RiskState
    previous_risk_state: RiskState | None


@dataclass(frozen=True)
class AdvisoryFrictionConfig:
    """Parameters that reduce churn between raw beta intent and advisory output."""

    auto_assume_executed: bool = True
    no_trade_band: float = 0.15
    min_hold_days: int = 15
    max_beta_step_down: float = 0.20
    max_beta_step_up: float = 0.10
    downshift_confirmation_days: int = 3
    upshift_confirmation_days: int = 7
    annual_rebalance_days: int = 252
    turnover_cost_rate: float = 0.015


@dataclass(frozen=True)
class AdvisoryState:
    """State used to manage advisory cadence, not real brokerage positions."""

    assumed_beta: float
    last_rebalance_date: date | str | None
    last_advised_beta: float | None
    upshift_streak_days: int = 0
    downshift_streak_days: int = 0


@dataclass(frozen=True)
class AdvisoryDecision:
    """Friction-aware advisory output layered on top of raw beta intent."""

    raw_target_beta: float
    advised_target_beta: float
    assumed_beta_before: float
    assumed_beta_after: float
    should_adjust: bool
    adjustment_reason: str
    friction_blockers: tuple[str, ...]
    estimated_turnover: float
    estimated_cost_drag: float
    next_state: AdvisoryState


def _coerce_date(value: date | str | None) -> date | None:
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(value)


def target_allocation_from_beta(target_beta: float) -> TargetAllocationState:
    """Map a continuous advisory beta to a valid QQQ/QLD/Cash allocation."""
    beta = min(max(float(target_beta), 0.0), 1.2)
    if beta <= 1.0:
        qqq = beta
        qld = 0.0
        cash = 1.0 - qqq
    else:
        qld = beta - 1.0
        qqq = 1.0 - qld
        cash = 0.0
    return TargetAllocationState(
        target_cash_pct=float(cash),
        target_qqq_pct=float(qqq),
        target_qld_pct=float(qld),
        target_beta=float(beta),
    )


def build_advisory_state_from_history(
    *,
    history: list[dict],
    current_raw_target_beta: float,
    fallback_beta: float,
) -> AdvisoryState:
    """Restore advisory state from persisted history under auto-assume-executed semantics."""
    latest = history[0] if history else {}
    assumed_beta = float(
        latest.get("assumed_beta_after")
        or latest.get("target_beta")
        or fallback_beta
    )

    last_rebalance_date = None
    for record in history:
        should_adjust = record.get("rebalance_action", {}).get("should_adjust")
        if should_adjust is None:
            should_adjust = record.get("should_adjust")
        if should_adjust:
            last_rebalance_date = record.get("date")
            break

    upshift_streak_days = 0
    downshift_streak_days = 0
    direction = current_raw_target_beta - assumed_beta
    if direction > 0:
        upshift_streak_days = 1
        for record in history:
            hist_raw = record.get("raw_target_beta", record.get("target_beta"))
            if hist_raw is None or float(hist_raw) <= assumed_beta:
                break
            upshift_streak_days += 1
    elif direction < 0:
        downshift_streak_days = 1
        for record in history:
            hist_raw = record.get("raw_target_beta", record.get("target_beta"))
            if hist_raw is None or float(hist_raw) >= assumed_beta:
                break
            downshift_streak_days += 1

    return AdvisoryState(
        assumed_beta=assumed_beta,
        last_rebalance_date=last_rebalance_date,
        last_advised_beta=latest.get("target_beta"),
        upshift_streak_days=upshift_streak_days,
        downshift_streak_days=downshift_streak_days,
    )


def build_advisory_rebalance_decision(
    *,
    raw_recommendation: BetaRecommendation,
    advisory_state: AdvisoryState,
    as_of_date: date | str,
    config: AdvisoryFrictionConfig | None = None,
    emergency_override: bool = False,
) -> AdvisoryDecision:
    """Convert raw beta intent into a lower-turnover advisory recommendation."""
    cfg = config or AdvisoryFrictionConfig()
    current_date = _coerce_date(as_of_date)
    if current_date is None:
        raise ValueError("as_of_date is required")

    assumed_beta_before = float(advisory_state.assumed_beta)
    raw_target_beta = float(raw_recommendation.target_beta)
    gap = raw_target_beta - assumed_beta_before
    abs_gap = abs(gap)
    direction = "flat"
    if gap > 0:
        direction = "up"
    elif gap < 0:
        direction = "down"

    last_rebalance_date = _coerce_date(advisory_state.last_rebalance_date)
    days_since_rebalance = None
    if last_rebalance_date is not None:
        days_since_rebalance = (current_date - last_rebalance_date).days
    annual_anchor_due = (
        days_since_rebalance is not None
        and days_since_rebalance >= cfg.annual_rebalance_days
        and abs_gap > 0
    )

    blockers: list[str] = []
    if not emergency_override:
        if abs_gap < cfg.no_trade_band and not annual_anchor_due:
            blockers.append("within_no_trade_band")
        if direction == "up" and advisory_state.upshift_streak_days < cfg.upshift_confirmation_days:
            blockers.append("upshift_confirmation")
        if direction == "down" and advisory_state.downshift_streak_days < cfg.downshift_confirmation_days:
            blockers.append("downshift_confirmation")
        if (
            days_since_rebalance is not None
            and days_since_rebalance < cfg.min_hold_days
            and direction != "flat"
            and not annual_anchor_due
        ):
            blockers.append("min_hold_days")

    if emergency_override:
        advised_target_beta = raw_target_beta
        adjustment_reason = "emergency_override"
    elif blockers or direction == "flat":
        advised_target_beta = assumed_beta_before
        adjustment_reason = blockers[0] if blockers else "already_aligned"
    elif direction == "down":
        advised_target_beta = max(raw_target_beta, assumed_beta_before - cfg.max_beta_step_down)
        adjustment_reason = "advisory_downshift"
    else:
        advised_target_beta = min(raw_target_beta, assumed_beta_before + cfg.max_beta_step_up)
        adjustment_reason = "advisory_upshift"

    should_adjust = abs(advised_target_beta - assumed_beta_before) > 1e-9
    assumed_beta_after = advised_target_beta if should_adjust and cfg.auto_assume_executed else assumed_beta_before
    estimated_turnover = abs(advised_target_beta - assumed_beta_before)
    estimated_cost_drag = estimated_turnover * cfg.turnover_cost_rate
    next_state = AdvisoryState(
        assumed_beta=assumed_beta_after,
        last_rebalance_date=current_date if should_adjust else last_rebalance_date,
        last_advised_beta=advised_target_beta if should_adjust else advisory_state.last_advised_beta,
        upshift_streak_days=0 if should_adjust else advisory_state.upshift_streak_days,
        downshift_streak_days=0 if should_adjust else advisory_state.downshift_streak_days,
    )
    return AdvisoryDecision(
        raw_target_beta=raw_target_beta,
        advised_target_beta=advised_target_beta,
        assumed_beta_before=assumed_beta_before,
        assumed_beta_after=assumed_beta_after,
        should_adjust=should_adjust,
        adjustment_reason=adjustment_reason,
        friction_blockers=tuple(blockers),
        estimated_turnover=estimated_turnover,
        estimated_cost_drag=estimated_cost_drag,
        next_state=next_state,
    )


def build_beta_recommendation(
    selection: RuntimeSelection,
    risk_decision: RiskDecision,
    previous_risk_state: RiskState | None = None,
) -> BetaRecommendation:
    """Build the v8.0 recommendation surface from runtime selection + risk state."""

    target = selection.selected_candidate
    target_exposure = target.qqq_pct + 2.0 * target.qld_pct
    risk_state_changed = (
        previous_risk_state is not None
        and previous_risk_state != risk_decision.risk_state
    )

    if risk_state_changed:
        should_adjust = True
        reason = (
            f"risk_state_changed:{previous_risk_state.value}"
            f"->{risk_decision.risk_state.value}"
        )
    else:
        should_adjust = True
        reason = "align_to_target"

    return BetaRecommendation(
        target_beta=target_exposure,
        recommended_qqq_pct=target.qqq_pct,
        recommended_qld_pct=target.qld_pct,
        recommended_cash_pct=target.cash_pct,
        should_adjust=should_adjust,
        adjustment_reason=reason,
        current_risk_state=risk_decision.risk_state,
        previous_risk_state=previous_risk_state,
    )
