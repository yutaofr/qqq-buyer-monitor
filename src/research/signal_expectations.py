"""Build realistic expectation matrices for signal-alignment backtests."""
from __future__ import annotations

import pandas as pd

from src.backtest import BASE_WEEKLY_DCA_UNITS
from src.collector.historical_macro_seeder import HistoricalMacroSeeder
from src.models.deployment import DeploymentState
from src.research.data_contracts import validate_signal_expectation_frame

_BETA_FLOOR = 0.50
_BETA_NEUTRAL = 1.00
_BETA_MAX = 1.20
_DRAWDOWN_WINDOW = 252
_CREDIT_SPREAD_STRESS = 500.0
_CREDIT_SPREAD_CRISIS = 650.0
_CREDIT_SPREAD_RISK_ON = 450.0
_CREDIT_ACCEL_STRESS = 15.0
_LIQUIDITY_STRESS = -5.0


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
    rolling_drawdown: float,
) -> float:
    """
    Independent target-beta expectation surface.

    The surface intentionally stays coarse:
    - `0.5` when risk containment should dominate
    - `1.0` in normal conditions
    - `1.2` only when credit is tight and the market is not under stress
    """
    if credit_spread is None:
        return _BETA_FLOOR
    if credit_spread >= _CREDIT_SPREAD_CRISIS or rolling_drawdown >= 0.25:
        return _BETA_FLOOR
    if (
        credit_spread >= _CREDIT_SPREAD_STRESS
        or credit_accel > _CREDIT_ACCEL_STRESS
        or liquidity_roc <= _LIQUIDITY_STRESS
        or rolling_drawdown >= 0.15
        or (funding_stress and rolling_drawdown >= 0.10)
    ):
        return _BETA_FLOOR
    if (
        credit_spread < _CREDIT_SPREAD_RISK_ON
        and credit_accel <= 0.0
        and liquidity_roc > _LIQUIDITY_STRESS
        and not funding_stress
        and rolling_drawdown < 0.20
    ):
        return _BETA_MAX
    return _BETA_NEUTRAL


def _expected_deployment_state(
    *,
    credit_spread: float | None,
    credit_accel: float,
    liquidity_roc: float,
    funding_stress: bool,
    rolling_drawdown: float,
    five_day_return: float,
    twenty_day_return: float,
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
        credit_spread = features.get("credit_spread")
        credit_accel = float(features.get("credit_accel") or 0.0)
        liquidity_roc = float(features.get("liquidity_roc") or 0.0)
        funding_stress = bool(features.get("is_funding_stressed"))

        rows.append(
            {
                "date": dt,
                "expected_target_beta": _expected_target_beta(
                    credit_spread=None if credit_spread is None else float(credit_spread),
                    credit_accel=credit_accel,
                    liquidity_roc=liquidity_roc,
                    funding_stress=funding_stress,
                    rolling_drawdown=rolling_drawdown,
                ),
                "expected_deployment_state": _expected_deployment_state(
                    credit_spread=None if credit_spread is None else float(credit_spread),
                    credit_accel=credit_accel,
                    liquidity_roc=liquidity_roc,
                    funding_stress=funding_stress,
                    rolling_drawdown=rolling_drawdown,
                    five_day_return=float(five_day_return.iloc[loc]),
                    twenty_day_return=float(twenty_day_return.iloc[loc]),
                ),
                "rolling_drawdown": rolling_drawdown,
                "available_new_cash": BASE_WEEKLY_DCA_UNITS * float(prices.iloc[loc]),
                "erp": features.get("erp"),
                "capitulation_score": _derive_capitulation_score(price_drawdown),
                "tactical_stress_score": _derive_tactical_stress_score(prices, loc),
            }
        )

    frame = pd.DataFrame(rows)
    validate_signal_expectation_frame(frame)
    return frame
