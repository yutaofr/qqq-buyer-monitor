#!/usr/bin/env python3
"""Fetch VIX3M history to support Term Structure Kill-Switch verification."""
import logging
from datetime import date

import pandas as pd
import yfinance as yf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_vix3m_data():
    start_date = "1995-01-01"
    end_date = date.today().isoformat()

    logger.info("Fetching VIX3M (^VIX3M) history...")

    vix3m_df = yf.download("^VIX3M", start=start_date, end=end_date)

    if isinstance(vix3m_df.columns, pd.MultiIndex):
        vix3m = vix3m_df["Close"].iloc[:, 0]
    else:
        vix3m = vix3m_df["Close"]

    vix3m.name = "vix3m"

    # Merge with existing VIX/Price data
    existing_df = pd.read_csv("data/v11_price_vix_history.csv")
    existing_df["observation_date"] = pd.to_datetime(existing_df["observation_date"])

    vix3m_df_clean = vix3m.reset_index()
    vix3m_df_clean["Date"] = pd.to_datetime(vix3m_df_clean["Date"])

    merged = pd.merge(existing_df, vix3m_df_clean, left_on="observation_date", right_on="Date", how="left")
    merged = merged.drop(columns=["Date"])

    output_path = "data/v11_full_evidence_history.csv"
    merged.to_csv(output_path, index=False)
    logger.info(f"Full evidence history saved to {output_path}")

if __name__ == "__main__":
    fetch_vix3m_data()
