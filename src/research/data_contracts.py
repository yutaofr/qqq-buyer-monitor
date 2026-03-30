"""Canonical data contract for v11.10 Class A historical macro research inputs."""
from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from src.models.deployment import DeploymentState

REQUIRED_HISTORICAL_MACRO_COLUMNS: tuple[str, ...] = (
    "observation_date",
    "effective_date",
    "credit_spread_bps",
    "credit_acceleration_pct_10d",
    "forward_pe",
    "erp_pct",
    "real_yield_10y_pct",
    "net_liquidity_usd_bn",
    "liquidity_roc_pct_4w",
    "funding_stress_flag",
    "source_credit_spread",
    "source_forward_pe",
    "source_erp",
    "source_real_yield",
    "source_net_liquidity",
    "source_funding_stress",
    "build_version",
)

SIGNAL_EXPECTATION_REQUIRED_COLUMNS: tuple[str, ...] = ("date",)
SIGNAL_EXPECTATION_EXPECTED_COLUMNS: tuple[str, ...] = (
    "expected_target_beta",
    "expected_deployment_state",
)
SIGNAL_EXPECTATION_OPTIONAL_NUMERIC_COLUMNS: tuple[str, ...] = (
    "expected_deployment_multiplier",
    "expected_deployment_cash",
    "rolling_drawdown",
    "available_new_cash",
    "erp",
    "capitulation_score",
    "tactical_stress_score",
    "five_day_return",
    "twenty_day_return",
)
_ALLOWED_DEPLOYMENT_STATES = {state.value for state in DeploymentState}

_NUMERIC_COLUMNS: tuple[str, ...] = (
    "credit_spread_bps",
    "credit_acceleration_pct_10d",
    "forward_pe",
    "erp_pct",
    "real_yield_10y_pct",
    "net_liquidity_usd_bn",
    "liquidity_roc_pct_4w",
)

_ALLOWED_FUNDING_FLAGS = {0, 1}


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


def _normalize_date_column(series: pd.Series, *, column_name: str) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    if getattr(parsed.dt, "tz", None) is not None:
        parsed = parsed.dt.tz_convert(None)
    if parsed.isna().any():
        bad_rows = series.index[parsed.isna()].tolist()
        raise ValueError(f"Invalid datetime values in {column_name}: rows {bad_rows}")
    return parsed


def _normalize_signal_expectation_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df is None:
        raise ValueError("signal expectation frame is required")

    frame = df.copy()
    if "date" not in frame.columns:
        if isinstance(frame.index, pd.DatetimeIndex):
            frame = frame.reset_index().rename(columns={"index": "date"})
        else:
            raise ValueError("Signal expectation frame must include a `date` column")

    _require_columns(frame, SIGNAL_EXPECTATION_REQUIRED_COLUMNS)
    frame["date"] = _normalize_date_column(frame["date"], column_name="date")

    duplicate_rows = frame.index[frame["date"].duplicated()].tolist()
    if duplicate_rows:
        raise ValueError(f"Duplicate date values in signal expectation frame: rows {duplicate_rows}")

    return frame


def validate_historical_macro_frame(df: pd.DataFrame) -> None:
    """Validate the canonical historical macro research dataset."""
    if df is None:
        raise ValueError("historical macro frame is required")

    _require_columns(df, REQUIRED_HISTORICAL_MACRO_COLUMNS)

    observation_date = _parse_datetime_column(df, "observation_date")
    effective_date = _parse_datetime_column(df, "effective_date")

    duplicate_effective_dates = df.index[effective_date.duplicated()].tolist()
    if duplicate_effective_dates:
        raise ValueError(
            "Duplicate effective_date values in historical macro dataset: "
            f"rows {duplicate_effective_dates}"
        )

    invalid_order = effective_date < observation_date
    if invalid_order.any():
        bad_rows = df.index[invalid_order].tolist()
        raise ValueError(f"effective_date must be >= observation_date: rows {bad_rows}")

    for column in _NUMERIC_COLUMNS:
        _validate_numeric_column(df, column)

    _validate_funding_stress_flag(df)


def validate_signal_expectation_frame(df: pd.DataFrame) -> None:
    """Validate the expectation matrix used by signal-alignment backtests."""
    frame = _normalize_signal_expectation_frame(df)

    if not any(column in frame.columns for column in SIGNAL_EXPECTATION_EXPECTED_COLUMNS):
        raise ValueError(
            "Signal expectation frame must include at least one of "
            "`expected_target_beta` or `expected_deployment_state`"
        )

    if "expected_target_beta" in frame.columns:
        _validate_numeric_column(frame, "expected_target_beta")
        beta = pd.to_numeric(frame["expected_target_beta"], errors="coerce")
        invalid = beta.notna() & ((beta < 0.5) | (beta > 1.2))
        if invalid.any():
            bad_rows = frame.index[invalid].tolist()
            raise ValueError(f"expected_target_beta must be between 0.5 and 1.2: rows {bad_rows}")

    if "expected_deployment_multiplier" in frame.columns:
        multiplier = pd.to_numeric(frame["expected_deployment_multiplier"], errors="coerce")
        invalid = multiplier.notna() & ((multiplier < 0.0) | (multiplier > 2.0))
        if invalid.any():
            bad_rows = frame.index[invalid].tolist()
            raise ValueError(f"expected_deployment_multiplier must be between 0.0 and 2.0: rows {bad_rows}")

    for column in SIGNAL_EXPECTATION_OPTIONAL_NUMERIC_COLUMNS:
        if column in frame.columns:
            _validate_numeric_column(frame, column)

    if "expected_deployment_state" in frame.columns:
        invalid = frame["expected_deployment_state"].dropna().map(lambda value: str(value) not in _ALLOWED_DEPLOYMENT_STATES)
        if invalid.any():
            bad_rows = frame["expected_deployment_state"].dropna().index[invalid].tolist()
            raise ValueError(f"Unknown deployment state values: rows {bad_rows}")


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


def summarize_signal_expectation_coverage(df: pd.DataFrame) -> dict[str, object]:
    """Return basic coverage metrics for the signal expectation matrix."""
    frame = _normalize_signal_expectation_frame(df)
    validate_signal_expectation_frame(frame)

    coverage_columns = tuple(
        column
        for column in SIGNAL_EXPECTATION_EXPECTED_COLUMNS + SIGNAL_EXPECTATION_OPTIONAL_NUMERIC_COLUMNS
        if column in frame.columns
    )
    coverage = {
        column: float(frame[column].notna().mean())
        for column in coverage_columns
    }
    return {
        "rows": int(len(frame)),
        "first_date": frame["date"].min() if not frame.empty else None,
        "last_date": frame["date"].max() if not frame.empty else None,
        "coverage": coverage,
    }
