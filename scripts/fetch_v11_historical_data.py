#!/usr/bin/env python3
"""Fetch VIX and Price history for v11 POC starting from 1995."""

import logging
from datetime import date

import pandas as pd
import yfinance as yf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_v11_data():
    start_date = "1995-01-01"
    end_date = date.today().isoformat()

    logger.info(f"Fetching VIX (^VIX) and QQQ history from {start_date} to {end_date}...")

    # Fetch data as a single DataFrame to ensure alignment
    # yfinance version 0.2.x returns multi-index columns if multiple tickers,
    # but even with one it might have structure.

    vix_df = yf.download("^VIX", start=start_date, end=end_date)
    qqq_df = yf.download("QQQ", start=start_date, end=end_date)
    qqew_df = yf.download("QQEW", start=start_date, end=end_date)

    # Flatten or select Close
    def get_close(df):
        if isinstance(df.columns, pd.MultiIndex):
            return df["Close"].iloc[:, 0]
        return df["Close"]

    vix = get_close(vix_df)
    vix.name = "vix"

    qqq = get_close(qqq_df)
    qqq.name = "qqq_close"

    qqew = get_close(qqew_df)
    qqew.name = "qqew_close"

    # Combine
    df = pd.concat([vix, qqq, qqew], axis=1)
    df.index.name = "observation_date"
    df = df.sort_index()

    # Calculate Drawdown
    df["qqq_hwm"] = df["qqq_close"].expanding().max()
    df["drawdown_pct"] = (df["qqq_close"] - df["qqq_hwm"]) / df["qqq_hwm"] * 100.0

    # Calculate Breadth Proxy (QQQ/QQEW Relative Strength)
    # QQEW started in 2006. For earlier periods we might use a dummy or proxy.
    df["breadth_proxy"] = (df["qqq_close"] / df["qqew_close"]).pct_change(
        20
    )  # 20d momentum of relative strength

    output_path = "data/v11_price_vix_history.csv"
    df.to_csv(output_path)
    logger.info(f"Saved {len(df)} rows to {output_path}")


if __name__ == "__main__":
    fetch_v11_data()
