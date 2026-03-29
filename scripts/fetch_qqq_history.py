import os

import yfinance as yf

START_DATE = "1999-03-10"
END_DATE = "2026-03-23"
CACHE_PATH = "data/qqq_history_cache.csv"

def fetch():
    print(f"Downloading QQQ history from {START_DATE} to {END_DATE}...")
    os.makedirs("data", exist_ok=True)

    # Using a Ticker object with a specific period to be explicit
    ticker = yf.Ticker("QQQ")
    df = ticker.history(start=START_DATE, end=END_DATE)

    if not df.empty:
        df.to_csv(CACHE_PATH)
        print(f"Successfully saved {len(df)} rows to {CACHE_PATH}")
    else:
        print("Error: Downloaded dataframe is empty.")

if __name__ == "__main__":
    fetch()
