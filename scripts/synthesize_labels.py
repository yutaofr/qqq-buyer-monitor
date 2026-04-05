import os

import pandas as pd


def synthesize():
    macro_path = "data/macro_historical_dump.csv"
    if not os.path.exists(macro_path):
        print(f"Error: {macro_path} not found.")
        return

    df = pd.read_csv(macro_path)
    df["observation_date"] = pd.to_datetime(df["observation_date"])

    # Labeling Window (1yr rolling)
    window = 252
    df["spread_pct"] = df["credit_spread_bps"].rolling(window, min_periods=20).rank(pct=True)
    df["erp_pct_rank"] = df["erp_ttm_pct"].rolling(window, min_periods=20).rank(pct=True)
    df["spread_20d_delta"] = df["credit_spread_bps"].diff(20)

    def label_regime(row):
        # 1. BUST: Extreme High Spread
        if row["spread_pct"] >= 0.90:
            return "BUST"

        # 2. RECOVERY: Spread mean-reverting + Liquidity Injection
        if (row["spread_pct"] >= 0.70 and row["credit_acceleration_pct_10d"] < -5) or (row["spread_20d_delta"] < -40 and row["liquidity_roc_pct_4w"] > 0):
            return "RECOVERY"

        # 3. LATE_CYCLE: Low ERP + Creeping Spreads
        if row["erp_pct_rank"] <= 0.25 and row["spread_pct"] > 0.65:
            return "LATE_CYCLE"

        # 4. DEFAULT: MID_CYCLE
        return "MID_CYCLE"

    df["regime"] = df.apply(label_regime, axis=1)

    os.makedirs("src/engine/v11/resources", exist_ok=True)
    out_path = "src/engine/v11/resources/v13_6_ex_regime_labels.csv"
    df[["observation_date", "regime"]].dropna().to_csv(out_path, index=False)

    counts = df["regime"].value_counts()
    print(f"Synthesized labels saved to {out_path}")
    print(f"Distribution:\n{counts}")

if __name__ == '__main__':
    synthesize()
