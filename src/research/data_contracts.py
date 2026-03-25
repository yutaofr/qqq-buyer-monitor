"""Canonical data contract for v7.0 Class A historical macro research inputs."""
from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

REQUIRED_HISTORICAL_MACRO_COLUMNS: tuple[str, ...] = (
    "observation_date",
    "effective_date",
    "credit_spread_bps",
    "credit_acceleration_pct_10d",
    "real_yield_10y_pct",
    "net_liquidity_usd_bn",
    "liquidity_roc_pct_4w",
    "funding_stress_flag",
    "source_credit_spread",
    "source_real_yield",
    "source_net_liquidity",
    "source_funding_stress",
    "build_version",
)

_NUMERIC_COLUMNS: tuple[str, ...] = (
    "credit_spread_bps",
    "credit_acceleration_pct_10d",
    "real_yield_10y_pct",
    "net_liquidity_usd_bn",
    "liquidity_roc_pct_4w",
)

_ALLOWED_FUNDING_FLAGS = {0, 1, True, False}


def _require_columns(df: pd.DataFrame, required: Sequence[str]) -> None:
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required historical macro columns: {', '.join(missing)}")


def _parse_datetime_column(df: pd.DataFrame, column: str) -> pd.Series:
    parsed = pd.to_datetime(df[column], errors="coerce")
    if parsed.isna().any():
        bad_rows = df.index[parsed.isna()].tolist()
        raise ValueError(f"Invalid datetime values in {column}: rows {bad_rows}")
    return parsed


def _validate_numeric_column(df: pd.DataFrame, column: str) -> None:
    series = df[column]
    for idx, value in series.items():
        if pd.isna(value):
            continue
        if isinstance(value, bool):
            raise ValueError(f"Invalid numeric value in {column}: row {idx}")
    coerced = pd.to_numeric(series, errors="coerce")
    invalid_mask = series.notna() & coerced.isna()
    if invalid_mask.any():
        bad_rows = df.index[invalid_mask].tolist()
        raise ValueError(f"Invalid numeric values in {column}: rows {bad_rows}")


def _validate_funding_stress_flag(df: pd.DataFrame) -> None:
    series = df["funding_stress_flag"]
    invalid = series.dropna().map(lambda value: value not in _ALLOWED_FUNDING_FLAGS)
    if invalid.any():
        bad_rows = series.index[series.notna() & invalid].tolist()
        raise ValueError(f"Invalid funding_stress_flag values: rows {bad_rows}")


def validate_historical_macro_frame(df: pd.DataFrame) -> None:
    """Validate the canonical historical macro research dataset."""
    if df is None:
        raise ValueError("historical macro frame is required")

    _require_columns(df, REQUIRED_HISTORICAL_MACRO_COLUMNS)

    observation_date = _parse_datetime_column(df, "observation_date")
    effective_date = _parse_datetime_column(df, "effective_date")

    invalid_order = effective_date < observation_date
    if invalid_order.any():
        bad_rows = df.index[invalid_order].tolist()
        raise ValueError(f"effective_date must be >= observation_date: rows {bad_rows}")

    for column in _NUMERIC_COLUMNS:
        _validate_numeric_column(df, column)

    _validate_funding_stress_flag(df)


def summarize_historical_macro_coverage(df: pd.DataFrame) -> dict[str, object]:
    """Return basic coverage metrics for the canonical historical macro dataset."""
    validate_historical_macro_frame(df)

    observation_date = pd.to_datetime(df["observation_date"], errors="coerce")
    coverage = {
        column: float(df[column].notna().mean())
        for column in REQUIRED_HISTORICAL_MACRO_COLUMNS
    }
    return {
        "rows": int(len(df)),
        "first_observation_date": observation_date.min() if not observation_date.empty else None,
        "last_observation_date": observation_date.max() if not observation_date.empty else None,
        "coverage": coverage,
    }
