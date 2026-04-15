"""PiT (Point-in-Time) alignment engine.

SRD v1.2 Chapter 5 — No-Lookahead Data Pipeline:
Every macro variable has a publication lag. Using the released value on the
very day it is *observed* (rather than *published*) introduces lookahead bias —
a cardinal sin in quantitative research.

PiT alignment enforces: available_at(data) >= decision_time

PiT offset rules per series:
    WALCL:    +1 TD (H.4.1 published Thursday afternoon; safe from Friday)
    RRPONTSYD: 0 TD (published same business day ~16:30 ET; use at close)
    WTREGEN:  +1 TD (TGA reported next business day at 15:00 ET)
    SOFR:     +1 TD (published next business day morning)
    VIXCLS:   0 TD (published at market close, useable same-day close)

Fill methods:
    ffill:     standard forward-fill for daily series
    staircase: H.4.1 specific — new value on release date, holds until next
               release. Equivalent to ffill but structured to make the
               weekly-to-daily fan-out explicit and auditable.

NaN gate: _assert_no_nan is a hard physical safety valve.
Any NaN reaching the BOCPD engine means the Lookback Padding failed.
It must raise, not warn — silent NaN propagation destroys engine state.
"""

from __future__ import annotations

from typing import TypedDict

import pandas as pd

# ─────────────────────────────────────────────────────────────
# Type and Rule Definitions
# ─────────────────────────────────────────────────────────────


class PiTConfig(TypedDict):
    offset_days: int      # number of trading days to shift right (publication lag)
    fill_method: str      # "ffill" | "staircase"


PIT_RULES: dict[str, PiTConfig] = {
    "WALCL": {
        "offset_days": 1,          # H.4.1 published Thursday ~16:30 ET → useable Fri
        "fill_method": "staircase", # weekly fan-out: holds until next Thursday release
    },
    "RRPONTSYD": {
        "offset_days": 0,          # RRP published same business day
        "fill_method": "ffill",
    },
    "WTREGEN": {
        "offset_days": 1,          # TGA balance published next business day
        "fill_method": "staircase",
    },
    "SOFR": {
        "offset_days": 1,          # SOFR reference rate published next morning
        "fill_method": "ffill",
    },
    "VIXCLS": {
        "offset_days": 0,          # VIX close available at market close
        "fill_method": "ffill",
    },
}


# ─────────────────────────────────────────────────────────────
# Core alignment function
# ─────────────────────────────────────────────────────────────


def apply_pit_offset(
    raw_df: pd.DataFrame,
    series_id: str,
    config: PiTConfig,
    trading_calendar: pd.DatetimeIndex,
) -> pd.Series:
    """Align a raw FRED series to the trading calendar with the correct PiT offset.

    Steps:
        1. Extract (observation_date, value) pairs from raw_df.
        2. Apply offset: shift each observation_date forward by offset_days TDs.
        3. Reindex to trading_calendar.
        4. Apply fill method (ffill or staircase).

    Args:
        raw_df:           DataFrame with columns ['observation_date', series_id].
        series_id:        Column name for the value in raw_df.
        config:           PiTConfig with offset_days and fill_method.
        trading_calendar: DatetimeIndex of valid trading days (from build_trading_calendar).

    Returns:
        pd.Series indexed on trading_calendar, dtype float64.
    """
    # Step 1: build a clean (date → value) mapping
    obs = raw_df[["observation_date", series_id]].copy()
    obs["observation_date"] = pd.to_datetime(obs["observation_date"])
    obs = obs.set_index("observation_date")[series_id].sort_index()

    # Step 2: shift observation dates by offset_days trading days
    if config["offset_days"] > 0:
        shifted_index = _shift_by_trading_days(
            obs.index, config["offset_days"], trading_calendar
        )
        obs = pd.Series(obs.values, index=shifted_index, name=series_id)

    # Step 3: reindex to trading calendar (creates NaN gaps between releases)
    # Deduplicate first: shifted dates may alias to the same trading day
    obs = obs[~obs.index.duplicated(keep="last")]
    aligned = obs.reindex(trading_calendar)

    # Step 4: fill gaps
    if config["fill_method"] in ("ffill", "staircase"):
        aligned = aligned.ffill()

    aligned.name = series_id
    return aligned


def _shift_by_trading_days(
    dates: pd.DatetimeIndex,
    n: int,
    trading_calendar: pd.DatetimeIndex,
) -> pd.DatetimeIndex:
    """Shift each date in `dates` forward by exactly n trading days.

    Uses searchsorted for O(log N) per date — no loops over the calendar.
    Dates that fall after the calendar end are silently dropped (returned as NaT).
    """
    cal = trading_calendar.sort_values()
    shifted = []
    for d in dates:
        pos = cal.searchsorted(d, side="left")  # position of d in calendar
        new_pos = pos + n
        if new_pos < len(cal):
            shifted.append(cal[new_pos])
        else:
            shifted.append(pd.NaT)
    return pd.DatetimeIndex(shifted)


# ─────────────────────────────────────────────────────────────
# NaN gate — physical safety valve
# ─────────────────────────────────────────────────────────────


def _assert_no_nan(
    panel: pd.DataFrame,
    start_date: str,
    end_date: str,
) -> None:
    """Hard NaN assertion gate — must raise ValueError, not warn.

    Called on the trimmed panel [start_date, end_date] before it is passed
    to the BOCPD runner. Any NaN here means Lookback Padding was insufficient
    or a data source has structural gaps. Both conditions are fatal.

    Args:
        panel:      DataFrame with DatetimeIndex (may be wider than [start, end]).
        start_date: ISO string — trim start.
        end_date:   ISO string — trim end.

    Raises:
        ValueError: if any NaN exists within [start_date, end_date].
    """
    from src.liquidity.data.trading_calendar import MAX_LOOKBACK

    trimmed = panel.loc[start_date:end_date]
    nan_cols = trimmed.columns[trimmed.isna().any()].tolist()

    if nan_cols:
        nan_counts = trimmed[nan_cols].isna().sum().to_dict()
        raise ValueError(
            f"NaN contamination in panel after padding! "
            f"Affected columns and counts: {nan_counts}. "
            f"This means MAX_LOOKBACK={MAX_LOOKBACK} is insufficient "
            f"or the data source has gaps in [{start_date}, {end_date}]. "
            f"First NaN row: {trimmed[nan_cols].isna().any(axis=1).idxmax()}"
        )
