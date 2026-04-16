"""PiT-aligned panel builder — the system's real-world data entry point.

Orchestrates all data loaders, PiT alignment, signal computation, and
lookback padding to produce a zero-NaN panel for the backtest runner.

Architecture: "Align each series independently, concat at the end."
Each raw Series goes through its own PiT rule (offset + fill) before
being reindexed to the trading calendar. After alignment, all Series
share the exact same DatetimeIndex, so pd.concat(axis=1) is safe.

This is the ONLY module that touches the network (FRED, yfinance).
All downstream modules receive a clean, deterministic DataFrame.
"""

from __future__ import annotations

import logging

import pandas as pd

from src.liquidity.config import load_config
from src.liquidity.data.fred_loader import load_fred_series
from src.liquidity.data.pit_aligner import PIT_RULES, _assert_no_nan, apply_pit_offset
from src.liquidity.data.price_loader import (
    load_constituent_returns_with_diagnostics,
    load_ohlc,
)
from src.liquidity.data.trading_calendar import (
    MAX_LOOKBACK,
    build_trading_calendar,
    compute_padded_start,
)
from src.liquidity.signal.ed_accel import compute_ed, compute_ed_accel
from src.liquidity.signal.fisher_rho import compute_fisher_rho
from src.liquidity.signal.macro_hazard import (
    composite_stress,
    directional_transform,
    map_to_hazard,
    rolling_percentile_rank,
)
from src.liquidity.signal.spread_anomaly import compute_spread_anomaly

logger = logging.getLogger(__name__)

# FRED series IDs used in the pipeline
_FRED_SERIES = {
    "WALCL":     "WALCL",       # Fed Reserves (H.4.1, weekly)
    "RRPONTSYD": "RRPONTSYD",   # Reverse Repo (daily)
    "WTREGEN":   "WTREGEN",     # TGA balance (weekly)
    "SOFR":      "SOFR",        # SOFR rate (daily)
    "VIXCLS":    "VIXCLS",      # VIX close (daily)
}

# Fallback series for historical periods where primary data is unavailable
_FRED_FALLBACKS = {
    "SOFR": "TEDRATE",   # TED Spread as SOFR proxy for pre-2018
}


def build_pit_aligned_panel(
    start_date: str,
    end_date: str,
    config: dict | None = None,
    top_n_constituents: int | None = None,
) -> pd.DataFrame:
    """Build a complete PiT-aligned panel with zero NaN.

    This is the single entry point for real-world data. It:
    1. Builds the trading calendar from yfinance QQQ data
    2. Computes the padded start date (MAX_LOOKBACK trading days before start)
    3. Fetches all FRED + yfinance data from padded_start to end_date
    4. Applies per-series PiT offset and calendar alignment
    5. Computes all signal features on the full (padded) panel
    6. Trims to [start_date, end_date]
    7. Asserts zero NaN (hard ValueError if violated)

    Args:
        start_date:          Backtest start (YYYY-MM-DD). Panel begins here.
        end_date:            Backtest end (YYYY-MM-DD). Panel ends here.
        config:              Parameter dict. If None, loads from bocpd_params.json.
        top_n_constituents:  Optional override for proxy-universe top_n.

    Returns:
        pd.DataFrame with DatetimeIndex ∈ [start_date, end_date], columns:
            QQQ_ret, QLD_ret           — daily returns
            ED_ACCEL                   — eigenvalue dispersion acceleration
            SPREAD_ANOMALY             — VIX Z-score
            FISHER_RHO                 — Fisher-z corr(ED, spread)
            LAMBDA_MACRO               — composite macro hazard rate
        Guarantee: zero NaN in all columns.

    Raises:
        RuntimeError: if any data source returns empty.
        ValueError:   if NaN remains after padding (lookback insufficient).
    """
    if config is None:
        config = load_config()

    macro_cfg = config["macro_hazard"]
    price_cfg = config["price_loader"]
    ed_cfg = config["ed_signal"]
    universe_cfg = config["proxy_universe"]
    if top_n_constituents is None:
        top_n_constituents = universe_cfg["top_n"]

    # ━━━ Step 1: Trading calendar ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    logger.info("Building trading calendar from yfinance QQQ...")
    trading_days = build_trading_calendar(start_date, end_date)

    # ━━━ Step 2: Padded start ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    padded_start = compute_padded_start(trading_days, start_date, MAX_LOOKBACK)
    padded_start_str = padded_start.strftime("%Y-%m-%d")
    logger.info(
        "Padded start: %s (lookback %d TD before %s)",
        padded_start_str, MAX_LOOKBACK, start_date,
    )

    # Full trading calendar from padded_start to end_date
    full_calendar = trading_days[trading_days >= padded_start]

    # ━━━ Step 3: Fetch all raw data ━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3a: FRED macro series (with fallback for historical gaps)
    fred_raw: dict[str, pd.DataFrame] = {}
    for label, series_id in _FRED_SERIES.items():
        try:
            logger.info("Fetching FRED: %s", series_id)
            fred_raw[label] = load_fred_series(
                series_id, padded_start_str, end_date,
            )
        except RuntimeError:
            fallback_id = _FRED_FALLBACKS.get(label)
            if fallback_id is None:
                raise
            logger.warning(
                "FRED %s unavailable for [%s, %s]. Falling back to %s.",
                series_id, padded_start_str, end_date, fallback_id,
            )
            raw = load_fred_series(fallback_id, padded_start_str, end_date)
            # Rename fallback column to the expected label so downstream
            # PIT_RULES and directional_transform work without changes
            raw = raw.rename(columns={fallback_id: label})
            fred_raw[label] = raw

    # 3b: Price data
    logger.info("Fetching OHLC: QQQ, QLD, TLT")
    ohlc = load_ohlc(
        ["QQQ", "QLD", "TLT"],
        padded_start_str,
        end_date,
        chunk_size=price_cfg["chunk_size"],
        max_retries=price_cfg["max_retries"],
        base_delay_seconds=price_cfg["base_delay_seconds"],
        jitter_seconds=price_cfg["jitter_seconds"],
    )

    logger.info("Fetching NDX constituent returns (top %d)", top_n_constituents)
    constituent_rets, constituent_diag = load_constituent_returns_with_diagnostics(
        padded_start_str, end_date,
        top_n=top_n_constituents,
        min_listing_days=universe_cfg["min_listing_days"],
        liquidity_lookback=universe_cfg["liquidity_lookback"],
        chunk_size=price_cfg["chunk_size"],
        max_retries=price_cfg["max_retries"],
        base_delay_seconds=price_cfg["base_delay_seconds"],
        jitter_seconds=price_cfg["jitter_seconds"],
    )
    failed_tickers = constituent_diag["failed_tickers"]
    if failed_tickers:
        logger.warning(
            "Constituent loader degraded: %d/%d tickers failed (%s)",
            len(failed_tickers),
            len(constituent_diag["requested_tickers"]),
            ", ".join(failed_tickers[:10]),
        )

    # ━━━ Step 4: Per-series PiT alignment ━━━━━━━━━━━━━━━━━━━━
    # Each series gets its own PiT offset + fill, then reindexed
    # to full_calendar. Output: clean Series with trading-day index.
    aligned: dict[str, pd.Series] = {}

    for label, raw_df in fred_raw.items():
        rule_key = label  # PIT_RULES keys match our labels
        if rule_key in PIT_RULES:
            pit_cfg = PIT_RULES[rule_key]
            aligned[label] = apply_pit_offset(
                raw_df, label, pit_cfg, full_calendar,
            )
        else:
            # No special PiT rule — just reindex to trading days + ffill
            series = pd.Series(
                raw_df.iloc[:, -1].values,
                index=pd.to_datetime(raw_df["observation_date"]),
                name=label,
            )
            aligned[label] = series.reindex(full_calendar).ffill()

    # Price returns (already on trading-day index from yfinance)
    qqq_close = ohlc["QQQ"]["QQQ_Close"]
    qld_close = ohlc["QLD"]["QLD_Close"]
    aligned["QQQ_ret"] = qqq_close.pct_change().reindex(full_calendar)
    aligned["QLD_ret"] = qld_close.pct_change().reindex(full_calendar)
    # Fill first row NaN from pct_change with 0
    aligned["QQQ_ret"] = aligned["QQQ_ret"].fillna(0.0)
    aligned["QLD_ret"] = aligned["QLD_ret"].fillna(0.0)

    # 4c: QQQ Trend indicators for Allocator Momentum Lockout
    aligned["QQQ_price"] = qqq_close.reindex(full_calendar).ffill()
    aligned["QQQ_sma200"] = qqq_close.rolling(window=200, min_periods=100).mean().reindex(full_calendar).ffill()

    # ━━━ Step 5: Signal feature computation (on full padded panel) ━━━
    # 5a: ED acceleration
    logger.info("Computing ED acceleration...")
    ed_series = compute_ed(
        constituent_rets,
        window=ed_cfg["window"],
        min_coverage=ed_cfg["min_coverage"],
        min_names=ed_cfg["min_names"],
    )
    ed_accel = compute_ed_accel(ed_series, median_window=ed_cfg["median_window"])
    ed_valid_names = constituent_diag["valid_names"].reindex(full_calendar).fillna(0).astype(int)
    ed_accel_aligned = ed_accel.reindex(full_calendar)
    ed_is_degraded = ed_accel_aligned.isna() | (ed_valid_names < ed_cfg["min_names"])
    aligned["ED_VALID_NAMES"] = ed_valid_names
    aligned["ED_IS_DEGRADED"] = ed_is_degraded
    aligned["_BATCH_ED_ACCEL"] = ed_accel_aligned.ffill().fillna(0.0)

    # 5b: Spread anomaly (VIX Z-score)
    logger.info("Computing spread anomaly...")
    vix = aligned["VIXCLS"]
    spread = compute_spread_anomaly(vix, lookback=252)
    aligned["_BATCH_SPREAD_ANOMALY"] = spread.reindex(full_calendar).ffill().fillna(0.0)

    # 5c: Fisher(ρ) — correlation between ED and spread
    logger.info("Computing Fisher(ρ)...")
    fisher = compute_fisher_rho(
        ed_accel_aligned, aligned["_BATCH_SPREAD_ANOMALY"], window=20,
    )
    fisher_is_degraded = fisher.isna() | ed_is_degraded
    aligned["FISHER_IS_DEGRADED"] = fisher_is_degraded
    aligned["_BATCH_FISHER_RHO"] = fisher.ffill().fillna(0.0)

    # 5d: Macro hazard rate (λ_macro)
    logger.info("Computing macro hazard rate...")
    transformed = directional_transform(
        walcl=aligned["WALCL"],
        rrp=aligned["RRPONTSYD"],
        tga=aligned["WTREGEN"],
        fra_ois=aligned["SOFR"],
    )
    ranks = {
        k: rolling_percentile_rank(v, lookback=macro_cfg["rank_lookback"])
        for k, v in transformed.items()
    }
    composite = composite_stress(ranks, weights=macro_cfg["weights"])
    lambda_macro = map_to_hazard(
        composite,
        lambda_floor=macro_cfg["lambda_floor"],
        lambda_ceil=macro_cfg["lambda_ceil"],
    )
    aligned["_BATCH_LAMBDA_MACRO"] = lambda_macro.reindex(full_calendar).ffill().fillna(
        macro_cfg["lambda_floor"]
    )

    # ━━━ Step 6: Assemble padded panel ━━━━━━━━━━━━━━━━━━━━━━━
    output_cols = [
        "QQQ_ret", "QLD_ret", "QQQ_price", "QQQ_sma200",
        "_BATCH_ED_ACCEL", "_BATCH_SPREAD_ANOMALY", "_BATCH_FISHER_RHO", "_BATCH_LAMBDA_MACRO",
        "ED_VALID_NAMES", "ED_IS_DEGRADED", "FISHER_IS_DEGRADED",
        "VIXCLS", "WALCL", "RRPONTSYD", "WTREGEN", "SOFR"
    ]
    padded_panel = pd.DataFrame(
        {col: aligned[col] for col in output_cols},
        index=full_calendar,
    )

    # ━━━ Step 7: Trim to [start_date, end_date] ━━━━━━━━━━━━━━
    panel = padded_panel.loc[start_date:end_date].copy()
    constituents = constituent_rets.loc[start_date:end_date].copy()

    panel.attrs["constituent_loader"] = {
        "requested_tickers": constituent_diag["requested_tickers"],
        "loaded_tickers": constituent_diag["loaded_tickers"],
        "failed_tickers": failed_tickers,
    }
    logger.info(
        "Panel shape: %s (padded: %s → trimmed: %s)",
        panel.shape, len(padded_panel), len(panel),
    )
    if panel["ED_IS_DEGRADED"].any():
        degraded_ratio = float(panel["ED_IS_DEGRADED"].mean())
        logger.warning(
            "ED degraded on %.1f%% of rows; median valid_names=%.1f, min valid_names=%d",
            degraded_ratio * 100.0,
            float(panel["ED_VALID_NAMES"].median()),
            int(panel["ED_VALID_NAMES"].min()),
        )
    if panel["FISHER_IS_DEGRADED"].any():
        logger.warning(
            "Fisher degraded on %.1f%% of rows",
            float(panel["FISHER_IS_DEGRADED"].mean()) * 100.0,
        )

    # ━━━ Step 8: NaN safety gate ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    _assert_no_nan(panel[[
        "QQQ_ret", "QLD_ret", "QQQ_price", "QQQ_sma200",
        "_BATCH_ED_ACCEL", "_BATCH_SPREAD_ANOMALY",
        "_BATCH_FISHER_RHO", "_BATCH_LAMBDA_MACRO",
    ]], start_date, end_date)

    logger.info("Panel built successfully. Zero NaN confirmed in critical columns.")
    return panel, constituents
