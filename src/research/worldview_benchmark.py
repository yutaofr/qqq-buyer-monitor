"""PIT-safe macro-cycle benchmark built from trailing QQQ price and volume structure.

Modern `LATE_CYCLE` includes grind-higher tape: price near highs, RSI above 70,
and fading volume can be a passive-flow regime rather than a direct `BUST`
precursor. The benchmark keeps that evidence in the late-cycle bucket unless
trend damage or selloff volume appears.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.regime_topology import ACTIVE_REGIME_ORDER

_REGIME_BETA_MAP: dict[str, float] = {
    "MID_CYCLE": 1.00,
    "LATE_CYCLE": 0.80,
    "BUST": 0.50,
    "RECOVERY": 1.10,
}


def build_worldview_benchmark(
    price_frame: pd.DataFrame,
    *,
    trend_window: int = 1,
) -> pd.DataFrame:
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
    rolling_high = close.rolling(252, min_periods=50).max()

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
    near_price_high = _positive(_bounded(_safe_ratio(close, rolling_high) - 0.98, 0.02))
    daily_rsi_hot = _positive(_bounded(daily_rsi - 70.0, 10.0))
    grind_higher_pressure = trend_up * volume_dry_up * near_price_high * daily_rsi_hot
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
    monthly_rollover = _positive(_bounded(monthly_rsi - 62.0, 10.0)) * _positive(
        _bounded(-monthly_rsi_change, 3.0)
    )
    monthly_repair = (
        recent_damage
        * _positive(_bounded(52.0 - monthly_rsi, 12.0))
        * _positive(_bounded(monthly_rsi_change, 3.0))
    )
    recovery_impulse = (
        0.35 * recovery_rebound
        + 0.20 * gap_improving
        + 0.15 * short_up
        + 0.20 * bullish_rsi_divergence
        + 0.10 * monthly_repair
    ).clip(lower=0.0, upper=1.5)
    bust_pressure = (
        0.32 * trend_down
        + 0.20 * momentum_down
        + 0.18 * deep_drawdown
        + 0.12 * selloff_volume
        + 0.10 * gap_worsening
        + 0.08 * monthly_rollover
    ).clip(lower=0.0, upper=1.5)
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
                + 0.75 * grind_higher_pressure
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
    if trend_window > 1:
        probabilities = probabilities.rolling(trend_window, min_periods=1).mean()
        probabilities = probabilities.div(probabilities.sum(axis=1), axis=0)
    sorted_probs = np.sort(probabilities.to_numpy(), axis=1)
    margin = pd.Series(sorted_probs[:, -1] - sorted_probs[:, -2], index=frame.index)
    conviction = probabilities.max(axis=1)
    transition_intensity = (
        ((0.18 - margin) / 0.18).clip(lower=0.0, upper=1.0)
        + (0.25 * transition_tension.clip(lower=0.0, upper=1.0))
    ).clip(lower=0.0, upper=1.0)
    benchmark = frame.copy()
    benchmark_regime = probabilities.idxmax(axis=1)
    benchmark_entropy = _regime_conditioned_entropy(
        probabilities=probabilities,
        benchmark_regime=benchmark_regime,
        transition_intensity=transition_intensity,
        conviction=conviction,
        trend_up=trend_up,
        momentum_up=momentum_up,
        slope_up=slope_up,
        gap_improving=gap_improving,
        short_up=short_up,
        recent_damage=recent_damage,
        recovery_impulse=recovery_impulse,
        bust_pressure=bust_pressure,
        transition_tension=transition_tension,
        divergence=divergence,
        trend_drying=trend_drying,
        volume_dry_up_pressure=volume_dry_up_pressure,
        bearish_rsi_divergence=bearish_rsi_divergence,
        selloff_volume=selloff_volume,
        gap_worsening=gap_worsening,
        monthly_rollover=monthly_rollover,
        monthly_repair=monthly_repair,
        bullish_rsi_divergence=bullish_rsi_divergence,
        trend_down=trend_down,
        deep_drawdown=deep_drawdown,
    )
    benchmark_uncertainty = (1.0 - conviction).clip(lower=0.0, upper=1.0)
    benchmark_trend_strength = pd.concat(
        [
            (0.55 * trend_up + 0.25 * momentum_up + 0.20 * slope_up)
            .clip(0.0, 1.0)
            .rename("mid_trend"),
            (0.60 * bust_pressure + 0.20 * trend_down + 0.20 * short_down)
            .clip(0.0, 1.0)
            .rename("bust_trend"),
            (0.55 * recovery_impulse + 0.20 * gap_improving + 0.15 * short_up)
            .clip(0.0, 1.0)
            .rename("recovery_trend"),
            (0.50 * trend_drying + 0.25 * divergence + 0.25 * volume_dry_up_pressure.clip(0.0, 1.0))
            .clip(0.0, 1.0)
            .rename("late_trend"),
        ],
        axis=1,
    ).max(axis=1)
    benchmark_conflict_score = (
        0.28 * transition_tension.clip(0.0, 1.0)
        + 0.18 * divergence.clip(0.0, 1.0)
        + 0.12 * bearish_rsi_divergence.clip(0.0, 1.0)
        + 0.10 * bullish_rsi_divergence.clip(0.0, 1.0)
        + 0.14 * benchmark_uncertainty
        + 0.10 * recent_damage.clip(0.0, 1.0)
        + 0.08 * selloff_volume.clip(0.0, 1.0)
    ).clip(lower=0.0, upper=1.0)
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
        benchmark[f"benchmark_prob_delta_lower_{regime}"] = (
            benchmark[f"benchmark_prob_delta_{regime}"] - delta_band
        )
        benchmark[f"benchmark_prob_delta_upper_{regime}"] = (
            benchmark[f"benchmark_prob_delta_{regime}"] + delta_band
        )
        benchmark[f"benchmark_prob_acceleration_lower_{regime}"] = (
            benchmark[f"benchmark_prob_acceleration_{regime}"] - acc_band
        )
        benchmark[f"benchmark_prob_acceleration_upper_{regime}"] = (
            benchmark[f"benchmark_prob_acceleration_{regime}"] + acc_band
        )

    benchmark["benchmark_regime"] = benchmark_regime
    benchmark["benchmark_expected_beta"] = sum(
        probabilities[regime] * beta for regime, beta in _REGIME_BETA_MAP.items()
    )
    entropy_band = (0.05 + (0.20 * transition_intensity) + (0.06 * transition_tension)).clip(
        lower=0.05,
        upper=0.30,
    )
    benchmark["benchmark_entropy"] = benchmark_entropy
    benchmark["benchmark_entropy_lower"] = (benchmark_entropy - entropy_band).clip(lower=0.0)
    benchmark["benchmark_entropy_upper"] = (benchmark_entropy + entropy_band).clip(upper=1.0)

    benchmark["benchmark_ma_gap"] = ma_gap.fillna(0.0)
    benchmark["benchmark_drawdown"] = drawdown.fillna(0.0)
    benchmark["benchmark_recent_drawdown_depth"] = recent_drawdown_depth
    benchmark["benchmark_rebound_from_trough"] = rebound_from_trough
    benchmark["benchmark_price_volume_divergence"] = divergence
    benchmark["benchmark_volume_ratio"] = volume_ratio
    benchmark["benchmark_grind_higher_pressure"] = grind_higher_pressure
    benchmark["benchmark_daily_rsi"] = daily_rsi.fillna(50.0)
    benchmark["benchmark_weekly_rsi"] = weekly_rsi.fillna(50.0)
    benchmark["benchmark_monthly_rsi"] = monthly_rsi.fillna(50.0)
    benchmark["benchmark_bearish_rsi_divergence"] = bearish_rsi_divergence
    benchmark["benchmark_bullish_rsi_divergence"] = bullish_rsi_divergence
    benchmark["benchmark_recent_damage"] = recent_damage
    benchmark["benchmark_recovery_impulse"] = recovery_impulse
    benchmark["benchmark_bust_pressure"] = bust_pressure
    benchmark["benchmark_transition_tension"] = transition_tension
    benchmark["benchmark_transition_intensity"] = transition_intensity
    benchmark["benchmark_uncertainty"] = benchmark_uncertainty
    benchmark["benchmark_trend_strength"] = benchmark_trend_strength
    benchmark["benchmark_conflict_score"] = benchmark_conflict_score
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


def _normalized_entropy(probabilities: pd.DataFrame) -> pd.Series:
    safe = probabilities.clip(lower=1e-12)
    entropy = -(safe * np.log(safe)).sum(axis=1)
    max_entropy = np.log(len(probabilities.columns))
    if max_entropy <= 0.0:
        return pd.Series(0.0, index=probabilities.index)
    return (entropy / max_entropy).clip(lower=0.0, upper=1.0)


def _regime_conditioned_entropy(
    *,
    probabilities: pd.DataFrame,
    benchmark_regime: pd.Series,
    transition_intensity: pd.Series,
    conviction: pd.Series,
    trend_up: pd.Series,
    momentum_up: pd.Series,
    slope_up: pd.Series,
    gap_improving: pd.Series,
    short_up: pd.Series,
    recent_damage: pd.Series,
    recovery_impulse: pd.Series,
    bust_pressure: pd.Series,
    transition_tension: pd.Series,
    divergence: pd.Series,
    trend_drying: pd.Series,
    volume_dry_up_pressure: pd.Series,
    bearish_rsi_divergence: pd.Series,
    selloff_volume: pd.Series,
    gap_worsening: pd.Series,
    monthly_rollover: pd.Series,
    monthly_repair: pd.Series,
    bullish_rsi_divergence: pd.Series,
    trend_down: pd.Series,
    deep_drawdown: pd.Series,
) -> pd.Series:
    base_entropy = _normalized_entropy(probabilities)
    uncertainty = (1.0 - conviction).clip(lower=0.0, upper=1.0)

    mid_confirmation = (
        0.40 * trend_up
        + 0.22 * momentum_up
        + 0.18 * slope_up
        + 0.12 * gap_improving
        - 0.18 * transition_tension
        - 0.15 * volume_dry_up_pressure
        - 0.12 * bearish_rsi_divergence
    ).clip(lower=0.0, upper=1.0)
    recovery_confirmation = (
        0.34 * recovery_impulse
        + 0.18 * gap_improving
        + 0.14 * short_up
        + 0.12 * monthly_repair
        + 0.12 * bullish_rsi_divergence
        - 0.12 * trend_down
        - 0.10 * deep_drawdown
    ).clip(lower=0.0, upper=1.0)
    late_noise = (
        0.28 * divergence
        + 0.24 * trend_drying
        + 0.20 * volume_dry_up_pressure
        + 0.16 * bearish_rsi_divergence
        + 0.12 * transition_tension
    ).clip(lower=0.0, upper=1.0)
    bust_noise = (
        0.24 * selloff_volume
        + 0.20 * gap_worsening
        + 0.18 * monthly_rollover
        + 0.16 * bust_pressure
        + 0.14 * recent_damage
        + 0.10 * transition_tension
    ).clip(lower=0.0, upper=1.0)

    entropy = (
        0.10
        + 0.16 * base_entropy
        + 0.26 * transition_intensity
        + 0.12 * transition_tension
        + 0.10 * uncertainty
    )
    mid_transition_allowance = (
        0.24 * transition_intensity + 0.10 * transition_tension + 0.08 * uncertainty
    ).clip(lower=0.0, upper=0.36)
    recovery_transition_allowance = (
        0.22 * transition_intensity + 0.10 * recent_damage + 0.08 * uncertainty
    ).clip(lower=0.0, upper=0.34)
    stable_factor = (1.0 - transition_intensity).clip(lower=0.0, upper=1.0)
    mid_stable_noise_allowance = (
        stable_factor * (0.14 * uncertainty + 0.05 * transition_tension + 0.03 * recent_damage)
    ).clip(lower=0.0, upper=0.16)
    recovery_stable_noise_allowance = (
        stable_factor
        * (
            0.16 * uncertainty
            + 0.06 * transition_tension
            + 0.05 * recent_damage
            + 0.04 * bullish_rsi_divergence
        )
    ).clip(lower=0.0, upper=0.20)
    late_stable_noise_allowance = (
        stable_factor
        * (
            0.12 * uncertainty
            + 0.08 * transition_tension
            + 0.07 * divergence
            + 0.06 * volume_dry_up_pressure.clip(0.0, 1.0)
        )
    ).clip(lower=0.0, upper=0.18)
    bust_stable_noise_allowance = (
        stable_factor
        * (
            0.12 * uncertainty
            + 0.08 * recent_damage
            + 0.08 * selloff_volume
            + 0.06 * monthly_rollover
        )
    ).clip(lower=0.0, upper=0.20)

    entropy += np.where(
        benchmark_regime.eq("LATE_CYCLE"),
        0.10 + 0.14 * late_noise + late_stable_noise_allowance,
        0.0,
    )
    entropy += np.where(
        benchmark_regime.eq("BUST"),
        0.14 + 0.16 * bust_noise + bust_stable_noise_allowance,
        0.0,
    )
    entropy += np.where(
        benchmark_regime.eq("MID_CYCLE"),
        -0.22 * mid_confirmation + mid_transition_allowance + mid_stable_noise_allowance,
        0.0,
    )
    entropy += np.where(
        benchmark_regime.eq("RECOVERY"),
        -0.20 * recovery_confirmation
        + recovery_transition_allowance
        + recovery_stable_noise_allowance,
        0.0,
    )

    return pd.Series(entropy, index=probabilities.index).clip(lower=0.06, upper=0.95)


def _bounded(series: pd.Series, scale: float) -> pd.Series:
    return pd.Series(
        np.tanh(pd.to_numeric(series, errors="coerce").fillna(0.0) / scale), index=series.index
    )


def _positive(series: pd.Series) -> pd.Series:
    return pd.Series(
        np.clip(pd.to_numeric(series, errors="coerce").fillna(0.0), 0.0, None), index=series.index
    )


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
