"""Build realistic expectation matrices for signal-alignment backtests."""
from __future__ import annotations

import pandas as pd

from src.backtest import BASE_WEEKLY_DCA_UNITS
from src.collector.historical_macro_seeder import HistoricalMacroSeeder
from src.models.deployment import DeploymentState, deployment_multiplier_for_state
from src.research.data_contracts import validate_signal_expectation_frame

_BETA_FLOOR = 0.50
_BETA_DEFENSE = 0.70
_BETA_REDUCED = 0.80
_BETA_MID_CYCLE = 0.90
_BETA_NEUTRAL = 1.00
_BETA_MAX = 1.20
_DRAWDOWN_WINDOW = 252
_CREDIT_SPREAD_STRESS = 500.0
_CREDIT_SPREAD_CRISIS = 650.0
_CREDIT_SPREAD_RISK_ON = 450.0
_CREDIT_ACCEL_STRESS = 15.0
_LIQUIDITY_STRESS = -5.0
_BLOOD_CHIP_CRISIS_DRAWDOWN = 0.15
_BLOOD_CHIP_LIQUIDITY_ROC = 0.5
_BLOOD_CHIP_TWENTY_DAY_RETURN = -0.08
_STRESS_PAUSE_THRESHOLD = 70
_LOW_ERP_THRESHOLD = 2.5
_RECOVERY_ERP_THRESHOLD = 3.5
_CAPITULATION_ERP_THRESHOLD = 4.5
_LATE_CREDIT_SPREAD_THRESHOLD = 450.0
_CAPITULATION_CREDIT_SPREAD_THRESHOLD = 600.0
_WEAK_BREADTH_THRESHOLD = 0.40
_TREND_BREAK_THRESHOLD = -0.02
_CAPITULATION_DRAWDOWN_THRESHOLD = 0.18
_CRISIS_ERP_THRESHOLD = 1.0
_EUPHORIC_CREDIT_SPREAD_THRESHOLD = 250.0
_EUPHORIC_ERP_THRESHOLD = 5.0
_TRANSITION_STRESS_SPREAD_THRESHOLD = 550.0
_TRANSITION_STRESS_CROSSOVER = 500.0


def _price_vs_ma_proxy(prices: pd.Series, loc: int, *, window: int = 200) -> float:
    start = max(0, loc - window + 1)
    trailing = prices.iloc[start : loc + 1]
    baseline = float(trailing.mean()) if not trailing.empty else float(prices.iloc[loc])
    if baseline <= 0:
        return 0.0
    return float(prices.iloc[loc]) / baseline - 1.0


def _breadth_proxy(prices: pd.Series, loc: int) -> float:
    current = float(prices.iloc[loc])
    prior_20 = float(prices.iloc[max(0, loc - 20)])
    prior_60 = float(prices.iloc[max(0, loc - 60)])
    ret_20 = 0.0 if prior_20 <= 0 else current / prior_20 - 1.0
    ret_60 = 0.0 if prior_60 <= 0 else current / prior_60 - 1.0
    proxy = 0.5 + ret_20 * 1.25 + ret_60 * 0.75
    return float(max(0.0, min(1.0, proxy)))


def _expected_structural_regime(
    *,
    credit_spread: float | None,
    erp: float | None,
) -> str:
    if credit_spread is None and erp is None:
        return "NEUTRAL"
    if (
        (credit_spread is not None and credit_spread >= _CREDIT_SPREAD_CRISIS)
        or (erp is not None and erp < _CRISIS_ERP_THRESHOLD)
    ):
        return "CRISIS"
    if (
        credit_spread is not None
        and credit_spread < _EUPHORIC_CREDIT_SPREAD_THRESHOLD
        and erp is not None
        and erp >= _EUPHORIC_ERP_THRESHOLD
    ):
        return "EUPHORIC"
    if (
        (credit_spread is not None and credit_spread >= _TRANSITION_STRESS_SPREAD_THRESHOLD)
        or (
            credit_spread is not None
            and credit_spread >= _TRANSITION_STRESS_CROSSOVER
            and erp is not None
            and erp < _LOW_ERP_THRESHOLD
        )
    ):
        return "TRANSITION_STRESS"
    if (
        (credit_spread is not None and credit_spread >= _LATE_CREDIT_SPREAD_THRESHOLD)
        or (erp is not None and erp < _LOW_ERP_THRESHOLD)
    ):
        return "RICH_TIGHTENING"
    return "NEUTRAL"


def _expected_cycle_state(
    *,
    credit_spread: float | None,
    credit_accel: float,
    liquidity_roc: float,
    funding_stress: bool,
    erp: float | None,
    breadth: float,
    price_vs_ma200: float,
    rolling_drawdown: float,
) -> tuple[str, float]:
    if credit_spread is None or erp is None:
        return "UNQUALIFIED", _BETA_REDUCED

    if (
        credit_spread >= _CREDIT_SPREAD_CRISIS
        or (
            credit_accel >= _CREDIT_ACCEL_STRESS
            and (liquidity_roc <= _LIQUIDITY_STRESS or funding_stress)
            and (breadth <= _WEAK_BREADTH_THRESHOLD or price_vs_ma200 <= _TREND_BREAK_THRESHOLD)
        )
    ):
        return "BUST", _BETA_FLOOR

    if (
        credit_spread >= _CAPITULATION_CREDIT_SPREAD_THRESHOLD
        and erp >= _CAPITULATION_ERP_THRESHOLD
        and (
            breadth <= _WEAK_BREADTH_THRESHOLD
            or rolling_drawdown >= _CAPITULATION_DRAWDOWN_THRESHOLD
        )
        and price_vs_ma200 <= _TREND_BREAK_THRESHOLD
        and credit_accel <= 0.0
    ):
        return "CAPITULATION", _BETA_MAX

    if (
        erp < _LOW_ERP_THRESHOLD
        and (
            credit_spread >= _LATE_CREDIT_SPREAD_THRESHOLD
            or credit_accel > 0.0
            or breadth <= _WEAK_BREADTH_THRESHOLD
            or price_vs_ma200 <= _TREND_BREAK_THRESHOLD
        )
    ):
        return "LATE_CYCLE", _BETA_REDUCED

    if (
        erp >= _RECOVERY_ERP_THRESHOLD
        and credit_spread <= _CREDIT_SPREAD_STRESS
        and credit_accel <= 0.0
        and (breadth > _WEAK_BREADTH_THRESHOLD or price_vs_ma200 > _TREND_BREAK_THRESHOLD)
    ):
        return "RECOVERY", _BETA_NEUTRAL

    return "MID_CYCLE", _BETA_MID_CYCLE


def _rolling_market_drawdown(prices: pd.Series, loc: int, *, window: int = _DRAWDOWN_WINDOW) -> float:
    """Return drawdown vs the trailing-window high as a negative number."""
    start = max(0, loc - window + 1)
    trailing_peak = float(prices.iloc[start : loc + 1].max())
    current = float(prices.iloc[loc])
    if trailing_peak <= 0:
        return 0.0
    return current / trailing_peak - 1.0


def _derive_capitulation_score(drawdown: float) -> int:
    if drawdown <= -0.20:
        return 80
    if drawdown <= -0.15:
        return 70
    if drawdown <= -0.10:
        return 40
    if drawdown <= -0.05:
        return 20
    return 0


def _derive_tactical_stress_score(prices: pd.Series, loc: int) -> int:
    if loc < 4:
        return 10
    current = float(prices.iloc[loc])
    recent = float(prices.iloc[max(0, loc - 4)])
    if recent <= 0:
        return 10
    rally = current / recent - 1.0
    if rally >= 0.12:
        return 80
    if rally >= 0.08:
        return 60
    return 10


def _expected_target_beta(
    *,
    credit_spread: float | None,
    credit_accel: float,
    liquidity_roc: float,
    funding_stress: bool,
    erp: float | None,
    breadth: float,
    price_vs_ma200: float,
    rolling_drawdown: float,
) -> float:
    """Independent v10-style target-beta expectation surface."""
    cycle_regime, cycle_ceiling = _expected_cycle_state(
        credit_spread=credit_spread,
        credit_accel=credit_accel,
        liquidity_roc=liquidity_roc,
        funding_stress=funding_stress,
        erp=erp,
        breadth=breadth,
        price_vs_ma200=price_vs_ma200,
        rolling_drawdown=rolling_drawdown,
    )
    structural_regime = _expected_structural_regime(
        credit_spread=credit_spread,
        erp=erp,
    )

    if cycle_regime == "CAPITULATION":
        return _BETA_MAX
    if structural_regime == "CRISIS" or rolling_drawdown >= 0.30 or cycle_regime == "BUST":
        return _BETA_FLOOR
    if credit_spread is None:
        return _BETA_REDUCED
    if rolling_drawdown >= 0.25:
        return _BETA_DEFENSE if cycle_regime == "RECOVERY" else _BETA_FLOOR
    if structural_regime == "TRANSITION_STRESS":
        return _BETA_DEFENSE if cycle_regime == "RECOVERY" else _BETA_FLOOR

    credit_warn = credit_spread >= _CREDIT_SPREAD_STRESS
    credit_danger = credit_spread >= _CREDIT_SPREAD_CRISIS
    accel_danger = credit_accel > _CREDIT_ACCEL_STRESS
    liq_danger = liquidity_roc <= _LIQUIDITY_STRESS
    stress_overlay = funding_stress and (credit_warn or accel_danger or liq_danger)
    stress_count = sum((credit_danger, accel_danger, liq_danger))

    if structural_regime == "RICH_TIGHTENING" or rolling_drawdown >= 0.20 or credit_warn:
        return min(_BETA_REDUCED, cycle_ceiling)
    if stress_count >= 2 or stress_overlay:
        return _BETA_DEFENSE if cycle_regime == "RECOVERY" else _BETA_FLOOR
    if stress_count == 1:
        return min(_BETA_REDUCED, cycle_ceiling)
    if cycle_regime == "RECOVERY":
        return _BETA_NEUTRAL
    return cycle_ceiling


def _expected_deployment_state(
    *,
    credit_spread: float | None,
    credit_accel: float,
    liquidity_roc: float,
    funding_stress: bool,
    rolling_drawdown: float,
    five_day_return: float,
    twenty_day_return: float,
    capitulation_score: int,
    tactical_stress_score: int,
) -> str:
    """
    Independent incremental-cash expectation surface.

    - `DEPLOY_PAUSE` in crisis or deep drawdown
    - `DEPLOY_SLOW` in stressed but still investable tape
    - `DEPLOY_FAST` only for controlled left-side weakness
    - `DEPLOY_BASE` otherwise
    """
    if credit_spread is None:
        return DeploymentState.DEPLOY_PAUSE.value
    if tactical_stress_score >= _STRESS_PAUSE_THRESHOLD:
        return DeploymentState.DEPLOY_PAUSE.value
    if (
        credit_spread >= _CREDIT_SPREAD_CRISIS
        and rolling_drawdown >= _BLOOD_CHIP_CRISIS_DRAWDOWN
        and liquidity_roc > _BLOOD_CHIP_LIQUIDITY_ROC
        and credit_accel <= 0.0
        and twenty_day_return <= _BLOOD_CHIP_TWENTY_DAY_RETURN
    ):
        return DeploymentState.DEPLOY_FAST.value
    if credit_spread >= _CREDIT_SPREAD_CRISIS or rolling_drawdown >= 0.25:
        return DeploymentState.DEPLOY_PAUSE.value
    if rolling_drawdown >= 0.12 and twenty_day_return <= -0.08 and credit_spread < _CREDIT_SPREAD_CRISIS:
        return DeploymentState.DEPLOY_FAST.value
    if (
        credit_spread >= _CREDIT_SPREAD_STRESS
        or credit_accel > _CREDIT_ACCEL_STRESS
        or liquidity_roc <= _LIQUIDITY_STRESS
        or rolling_drawdown >= 0.15
        or (funding_stress and rolling_drawdown >= 0.10)
    ):
        return DeploymentState.DEPLOY_SLOW.value
    if rolling_drawdown >= 0.08 and five_day_return <= 0.0:
        return DeploymentState.DEPLOY_FAST.value
    return DeploymentState.DEPLOY_BASE.value


def build_market_expectation_matrix(
    ohlcv: pd.DataFrame,
    *,
    macro_seeder: HistoricalMacroSeeder | None = None,
) -> pd.DataFrame:
    """
    Build a realistic market-date expectation matrix for signal audits.

    The matrix is intentionally derived from raw market conditions instead of
    replaying the production decision tree. It can therefore serve as a stable
    acceptance surface for:
    1. stock-of-assets `target_beta`
    2. incremental-cash `deployment_state`
    """
    prices = ohlcv["Close"].dropna().astype(float)
    if prices.empty:
        raise ValueError("Empty price data")

    five_day_return = prices.pct_change(5).fillna(0.0)
    twenty_day_return = prices.pct_change(20).fillna(0.0)
    rows: list[dict[str, object]] = []

    for loc, dt in enumerate(prices.index):
        current_date = pd.Timestamp(dt).date()
        features = {
            "credit_spread": None,
            "credit_accel": 0.0,
            "liquidity_roc": 0.0,
            "erp": None,
            "is_funding_stressed": False,
        }
        if macro_seeder is not None:
            features.update(macro_seeder.get_features_for_date(current_date))

        price_drawdown = _rolling_market_drawdown(prices, loc)
        rolling_drawdown = max(0.0, -price_drawdown)
        breadth_proxy = _breadth_proxy(prices, loc)
        trend_proxy = _price_vs_ma_proxy(prices, loc)
        credit_spread = features.get("credit_spread")
        credit_accel = float(features.get("credit_accel") or 0.0)
        liquidity_roc = float(features.get("liquidity_roc") or 0.0)
        erp = features.get("erp")
        funding_stress = bool(features.get("is_funding_stressed"))
        funding_event = loc % 5 == 0
        available_new_cash = BASE_WEEKLY_DCA_UNITS * float(prices.iloc[loc]) if funding_event else 0.0
        expected_deployment_state = _expected_deployment_state(
            credit_spread=None if credit_spread is None else float(credit_spread),
            credit_accel=credit_accel,
            liquidity_roc=liquidity_roc,
            funding_stress=funding_stress,
            rolling_drawdown=rolling_drawdown,
            five_day_return=float(five_day_return.iloc[loc]),
            twenty_day_return=float(twenty_day_return.iloc[loc]),
            capitulation_score=_derive_capitulation_score(price_drawdown),
            tactical_stress_score=_derive_tactical_stress_score(prices, loc),
        )
        expected_deployment_multiplier = (
            float(deployment_multiplier_for_state(expected_deployment_state) or 0.0)
        )

        rows.append(
            {
                "date": dt,
                "expected_target_beta": _expected_target_beta(
                    credit_spread=None if credit_spread is None else float(credit_spread),
                    credit_accel=credit_accel,
                    liquidity_roc=liquidity_roc,
                    funding_stress=funding_stress,
                    erp=None if erp is None else float(erp),
                    breadth=breadth_proxy,
                    price_vs_ma200=trend_proxy,
                    rolling_drawdown=rolling_drawdown,
                ),
                "expected_deployment_state": expected_deployment_state,
                "expected_deployment_multiplier": expected_deployment_multiplier,
                "rolling_drawdown": rolling_drawdown,
                "available_new_cash": available_new_cash,
                "expected_deployment_cash": available_new_cash * expected_deployment_multiplier,
                "funding_event": funding_event,
                "erp": erp,
                "capitulation_score": _derive_capitulation_score(price_drawdown),
                "tactical_stress_score": _derive_tactical_stress_score(prices, loc),
                "five_day_return": float(five_day_return.iloc[loc]),
                "twenty_day_return": float(twenty_day_return.iloc[loc]),
            }
        )

    frame = pd.DataFrame(rows)
    validate_signal_expectation_frame(frame)
    return frame
