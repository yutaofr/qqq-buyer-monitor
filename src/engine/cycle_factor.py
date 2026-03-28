"""v10.0 cycle factor classifier."""
from __future__ import annotations

from src.engine.feature_pipeline import FeatureSnapshot
from src.models.cycle import CycleDecision, CycleRegime

_LOW_ERP_THRESHOLD = 2.5
_RECOVERY_ERP_THRESHOLD = 3.5
_CAPITULATION_ERP_THRESHOLD = 4.5
_LATE_CREDIT_SPREAD_THRESHOLD = 450.0
_BUST_CREDIT_SPREAD_THRESHOLD = 650.0
_CAPITULATION_CREDIT_SPREAD_THRESHOLD = 600.0
_CREDIT_ACCEL_STRESS_THRESHOLD = 15.0
_WEAK_BREADTH_THRESHOLD = 0.40
_SEVERE_BREADTH_THRESHOLD = 0.30
_TREND_BREAK_THRESHOLD = -0.02
_SEVERE_TREND_BREAK_THRESHOLD = -0.08
_CAPITULATION_DRAWDOWN_THRESHOLD = 0.18


def decide_cycle_state(snapshot: FeatureSnapshot) -> CycleDecision:
    """Classify the macro/market cycle for QQQ vs QLD eligibility."""
    v = snapshot.values
    spread = v.get("credit_spread")
    accel = v.get("credit_acceleration")
    liq_roc = v.get("liquidity_roc")
    funding_stress = bool(v.get("funding_stress") or False)
    breadth = v.get("breadth")
    trend = v.get("price_vs_ma200")
    drawdown = v.get("rolling_drawdown")
    erp = v.get("erp")

    missing = [
        name
        for name in ("credit_spread", "breadth", "price_vs_ma200", "erp")
        if v.get(name) is None
    ]
    if missing:
        return CycleDecision(
            cycle_regime=CycleRegime.UNQUALIFIED,
            target_exposure_ceiling=0.80,
            qld_share_ceiling=0.0,
            reasons=({"rule": "missing_cycle_inputs", "missing": missing},),
        )

    reasons: list[dict] = []

    if (
        float(spread) >= _BUST_CREDIT_SPREAD_THRESHOLD
        or (
            accel is not None
            and float(accel) >= _CREDIT_ACCEL_STRESS_THRESHOLD
            and (
                (liq_roc is not None and float(liq_roc) <= -5.0)
                or funding_stress
            )
            and (
                float(breadth) <= _WEAK_BREADTH_THRESHOLD
                or float(trend) <= _TREND_BREAK_THRESHOLD
            )
        )
    ):
        reasons.append({"rule": "bust", "spread": spread, "accel": accel})
        return CycleDecision(CycleRegime.BUST, 0.50, 0.0, tuple(reasons))

    if (
        float(spread) >= _CAPITULATION_CREDIT_SPREAD_THRESHOLD
        and float(erp) >= _CAPITULATION_ERP_THRESHOLD
        and (
            float(breadth) <= _WEAK_BREADTH_THRESHOLD
            or (drawdown is not None and float(drawdown) >= _CAPITULATION_DRAWDOWN_THRESHOLD)
        )
        and float(trend) <= _TREND_BREAK_THRESHOLD
        and (accel is None or float(accel) <= 0.0)
    ):
        reasons.append({"rule": "capitulation", "spread": spread, "erp": erp})
        return CycleDecision(CycleRegime.CAPITULATION, 1.20, 0.25, tuple(reasons))

    if (
        float(erp) < _LOW_ERP_THRESHOLD
        and (
            float(spread) >= _LATE_CREDIT_SPREAD_THRESHOLD
            or (accel is not None and float(accel) > 0.0)
            or float(breadth) <= _WEAK_BREADTH_THRESHOLD
            or float(trend) <= _TREND_BREAK_THRESHOLD
        )
    ):
        reasons.append({"rule": "late_cycle", "spread": spread, "erp": erp})
        return CycleDecision(CycleRegime.LATE_CYCLE, 0.80, 0.0, tuple(reasons))

    if (
        float(erp) >= _RECOVERY_ERP_THRESHOLD
        and float(spread) <= 500.0
        and (accel is None or float(accel) <= 0.0)
        and (
            float(breadth) > _WEAK_BREADTH_THRESHOLD
            or float(trend) > _TREND_BREAK_THRESHOLD
        )
    ):
        reasons.append({"rule": "recovery", "spread": spread, "erp": erp})
        return CycleDecision(CycleRegime.RECOVERY, 1.00, 0.10, tuple(reasons))

    reasons.append({"rule": "mid_cycle", "spread": spread, "erp": erp})
    return CycleDecision(CycleRegime.MID_CYCLE, 0.90, 0.0, tuple(reasons))
