"""PIT-safe macro-cycle benchmark built from trailing QQQ price and volume structure."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.regime_topology import ACTIVE_REGIME_ORDER

_REGIME_BETA_MAP: dict[str, float] = {
    "MID_CYCLE": 1.05,
    "LATE_CYCLE": 0.80,
    "BUST": 0.50,
    "RECOVERY": 0.95,
}


def build_worldview_benchmark(price_frame: pd.DataFrame) -> pd.DataFrame:
    """Build a soft 4-regime benchmark from trailing market structure only.

    The benchmark is evaluation-only. It uses rolling price/volume features that are
    available at each timestamp and deliberately avoids any future-looking label logic.
    """

    frame = _normalize_price_frame(price_frame)
    close = frame["Close"]
    volume = frame["Volume"]
    daily_rsi = _rsi(close, 14)
    weekly_rsi = _resampled_indicator(close, "W-FRI", lambda s: _rsi(s, 14))
    monthly_rsi = _resampled_indicator(close, "ME", lambda s: _rsi(s, 14))

    ma_50 = close.rolling(50, min_periods=20).mean()
    ma_200 = close.rolling(200, min_periods=50).mean()
    ma_gap = _safe_ratio(ma_50, ma_200) - 1.0
    ma_gap_momentum = ma_gap.diff(21).fillna(0.0)
    ma_50_slope = ma_50.pct_change(21).fillna(0.0)

    short_momentum = close.pct_change(21).fillna(0.0)
    long_momentum = close.pct_change(126).fillna(0.0)
    drawdown = _safe_ratio(close, close.cummax()) - 1.0
    recent_drawdown_depth = (-drawdown).rolling(126, min_periods=20).max().fillna(0.0)
    rebound_from_trough = (
        _safe_ratio(close, close.rolling(63, min_periods=20).min()) - 1.0
    ).fillna(0.0)

    volume_short = volume.rolling(20, min_periods=5).mean()
    volume_long = volume.rolling(60, min_periods=20).mean()
    volume_ratio = (_safe_ratio(volume_short, volume_long) - 1.0).fillna(0.0)
    overextension = (_safe_ratio(close, ma_200) - 1.0).fillna(0.0)

    trend_up = _positive(_bounded(ma_gap, 0.04))
    trend_down = _positive(_bounded(-ma_gap, 0.04))
    momentum_up = _positive(_bounded(long_momentum, 0.15))
    momentum_down = _positive(_bounded(-long_momentum, 0.12))
    short_up = _positive(_bounded(short_momentum, 0.08))
    short_down = _positive(_bounded(-short_momentum, 0.08))
    slope_up = _positive(_bounded(ma_50_slope, 0.05))
    deep_drawdown = _positive(_bounded((-drawdown) - 0.10, 0.15))
    recent_damage = _positive(_bounded(recent_drawdown_depth - 0.12, 0.20))
    recovery_rebound = _positive(_bounded(rebound_from_trough - 0.12, 0.18)) * recent_damage
    volume_dry_up = _positive(_bounded(-volume_ratio, 0.18))
    volume_dry_up_change = _positive(_bounded((-volume_ratio).diff(5).fillna(0.0), 0.05))
    volume_dry_up_pressure = (((-volume_ratio) - 0.02) / 0.10).clip(lower=0.0, upper=2.0)
    selloff_volume = _positive(_bounded(volume_ratio, 0.18)) * short_down
    divergence = short_up * volume_dry_up
    trend_drying = trend_up * volume_dry_up
    late_tail_hazard = trend_up * volume_dry_up_pressure.pow(2)
    gap_improving = _positive(_bounded(ma_gap_momentum, 0.03))
    gap_worsening = _positive(_bounded(-ma_gap_momentum, 0.03))
    overextended = _positive(_bounded(overextension - 0.10, 0.10))
    weekly_rsi_change = weekly_rsi.diff(21).fillna(0.0)
    monthly_rsi_change = monthly_rsi.diff(21).fillna(0.0)
    bearish_rsi_divergence = (
        short_up
        * _positive(_bounded(weekly_rsi - 60.0, 10.0))
        * _positive(_bounded(-weekly_rsi_change, 4.0))
    )
    bullish_rsi_divergence = (
        recent_damage
        * _positive(_bounded(45.0 - weekly_rsi, 10.0))
        * _positive(_bounded(weekly_rsi_change, 4.0))
    )
    monthly_rollover = (
        _positive(_bounded(monthly_rsi - 62.0, 10.0))
        * _positive(_bounded(-monthly_rsi_change, 3.0))
    )
    monthly_repair = (
        recent_damage
        * _positive(_bounded(52.0 - monthly_rsi, 12.0))
        * _positive(_bounded(monthly_rsi_change, 3.0))
    )
    transition_tension = (
        0.45 * divergence
        + 0.35 * bearish_rsi_divergence
        + 0.25 * bullish_rsi_divergence
        + 0.30 * monthly_rollover
        + 0.20 * monthly_repair
    ).clip(lower=0.0, upper=1.5)

    raw_scores = pd.DataFrame(
        {
            "MID_CYCLE": (
                1.00
                + 1.60 * trend_up
                + 1.20 * momentum_up
                + 0.80 * slope_up
                - 1.00 * recent_damage
                - 1.30 * divergence
                - 0.65 * volume_dry_up
                - 0.45 * volume_dry_up_pressure
                - 0.90 * trend_drying
                - 0.30 * late_tail_hazard
                - 0.50 * volume_dry_up_change
                - 0.80 * bearish_rsi_divergence
                - 0.60 * monthly_rollover
                - 1.20 * trend_down
            ),
            "LATE_CYCLE": (
                0.75
                + 0.80 * trend_up
                + 1.40 * divergence
                + 1.60 * trend_drying
                + 0.85 * volume_dry_up_change
                + 0.90 * volume_dry_up_pressure
                + 0.65 * late_tail_hazard
                + 0.20 * gap_worsening
                + 0.20 * overextended
                + 1.10 * volume_dry_up
                + 0.40 * short_up
                + 0.85 * bearish_rsi_divergence
                + 0.55 * monthly_rollover
                - 0.60 * trend_down
                - 0.50 * recovery_rebound
            ),
            "BUST": (
                0.60
                + 1.80 * trend_down
                + 1.30 * momentum_down
                + 1.10 * short_down
                + 1.30 * deep_drawdown
                + 0.90 * selloff_volume
                + 0.50 * gap_worsening
                + 0.25 * monthly_rollover
                - 0.50 * recovery_rebound
            ),
            "RECOVERY": (
                0.70
                + 1.40 * recent_damage
                + 1.40 * recovery_rebound
                + 1.00 * short_up
                + 0.90 * gap_improving
                + 0.60 * slope_up
                + 0.90 * bullish_rsi_divergence
                + 0.60 * monthly_repair
                - 0.70 * trend_down
                - 0.50 * deep_drawdown
                - 0.40 * divergence
            ),
        },
        index=frame.index,
    ).clip(lower=0.01)

    probabilities = raw_scores.div(raw_scores.sum(axis=1), axis=0)
    sorted_probs = np.sort(probabilities.to_numpy(), axis=1)
    margin = pd.Series(sorted_probs[:, -1] - sorted_probs[:, -2], index=frame.index)
    transition_intensity = (
        ((0.18 - margin) / 0.18).clip(lower=0.0, upper=1.0)
        + (0.25 * transition_tension.clip(lower=0.0, upper=1.0))
    ).clip(lower=0.0, upper=1.0)
    benchmark = frame.copy()
    for regime in ACTIVE_REGIME_ORDER:
        benchmark[f"benchmark_prob_{regime}"] = probabilities[regime]
        benchmark[f"benchmark_prob_delta_{regime}"] = probabilities[regime].diff().fillna(0.0)
        benchmark[f"benchmark_prob_acceleration_{regime}"] = (
            benchmark[f"benchmark_prob_delta_{regime}"].diff().fillna(0.0)
        )
        prob_band = 0.08 + (0.20 * transition_intensity)
        delta_band = 0.02 + (0.06 * transition_intensity)
        acc_band = 0.015 + (0.04 * transition_intensity)
        benchmark[f"benchmark_prob_lower_{regime}"] = (
            benchmark[f"benchmark_prob_{regime}"] - prob_band
        ).clip(lower=0.0)
        benchmark[f"benchmark_prob_upper_{regime}"] = (
            benchmark[f"benchmark_prob_{regime}"] + prob_band
        ).clip(upper=1.0)
        benchmark[f"benchmark_prob_delta_lower_{regime}"] = benchmark[f"benchmark_prob_delta_{regime}"] - delta_band
        benchmark[f"benchmark_prob_delta_upper_{regime}"] = benchmark[f"benchmark_prob_delta_{regime}"] + delta_band
        benchmark[f"benchmark_prob_acceleration_lower_{regime}"] = (
            benchmark[f"benchmark_prob_acceleration_{regime}"] - acc_band
        )
        benchmark[f"benchmark_prob_acceleration_upper_{regime}"] = (
            benchmark[f"benchmark_prob_acceleration_{regime}"] + acc_band
        )

    benchmark["benchmark_regime"] = probabilities.idxmax(axis=1)
    benchmark["benchmark_expected_beta"] = sum(
        probabilities[regime] * beta for regime, beta in _REGIME_BETA_MAP.items()
    )

    benchmark["benchmark_ma_gap"] = ma_gap.fillna(0.0)
    benchmark["benchmark_drawdown"] = drawdown.fillna(0.0)
    benchmark["benchmark_recent_drawdown_depth"] = recent_drawdown_depth
    benchmark["benchmark_rebound_from_trough"] = rebound_from_trough
    benchmark["benchmark_price_volume_divergence"] = divergence
    benchmark["benchmark_volume_ratio"] = volume_ratio
    benchmark["benchmark_daily_rsi"] = daily_rsi.fillna(50.0)
    benchmark["benchmark_weekly_rsi"] = weekly_rsi.fillna(50.0)
    benchmark["benchmark_monthly_rsi"] = monthly_rsi.fillna(50.0)
    benchmark["benchmark_bearish_rsi_divergence"] = bearish_rsi_divergence
    benchmark["benchmark_bullish_rsi_divergence"] = bullish_rsi_divergence
    benchmark["benchmark_transition_intensity"] = transition_intensity
    return benchmark


def _normalize_price_frame(price_frame: pd.DataFrame) -> pd.DataFrame:
    if price_frame is None or price_frame.empty:
        raise ValueError("price_frame is required")
    if "Close" not in price_frame.columns:
        raise ValueError("price_frame must include a `Close` column")

    frame = price_frame.copy()
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        if frame["date"].isna().any():
            raise ValueError("price_frame contains invalid `date` values")
        frame = frame.set_index("date")
    elif not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError("price_frame must be indexed by date or include a `date` column")

    frame.index = pd.to_datetime(frame.index, errors="coerce")
    if frame.index.isna().any():
        raise ValueError("price_frame contains invalid index dates")

    frame = frame.sort_index()
    frame["Close"] = pd.to_numeric(frame["Close"], errors="coerce")
    if frame["Close"].isna().any():
        raise ValueError("price_frame contains invalid `Close` values")

    if "Volume" not in frame.columns:
        frame["Volume"] = 1.0
    frame["Volume"] = pd.to_numeric(frame["Volume"], errors="coerce").fillna(1.0).clip(lower=1.0)
    return frame


def _bounded(series: pd.Series, scale: float) -> pd.Series:
    return pd.Series(np.tanh(pd.to_numeric(series, errors="coerce").fillna(0.0) / scale), index=series.index)


def _positive(series: pd.Series) -> pd.Series:
    return pd.Series(np.clip(pd.to_numeric(series, errors="coerce").fillna(0.0), 0.0, None), index=series.index)


def _safe_ratio(left: pd.Series, right: pd.Series) -> pd.Series:
    numerator = pd.to_numeric(left, errors="coerce")
    denominator = pd.to_numeric(right, errors="coerce")
    safe_denominator = denominator.where(denominator.abs() > 1e-12)
    ratio = numerator / safe_denominator
    return ratio.replace([np.inf, -np.inf], np.nan).ffill().fillna(1.0)


def _rsi(series: pd.Series, window: int) -> pd.Series:
    delta = pd.to_numeric(series, errors="coerce").diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def _resampled_indicator(
    series: pd.Series,
    rule: str,
    indicator_builder,
) -> pd.Series:
    resampled = pd.to_numeric(series, errors="coerce").resample(rule).last().dropna()
    if resampled.empty:
        return pd.Series(50.0, index=series.index)
    indicator = indicator_builder(resampled)
    return indicator.reindex(series.index, method="ffill").fillna(50.0)
