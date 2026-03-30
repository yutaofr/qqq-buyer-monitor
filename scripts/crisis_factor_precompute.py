import pandas as pd
import numpy as np
import os
from datetime import datetime

# Paths
MACRO_DATA = "/app/data/macro_historical_dump.csv"
QQQ_DATA = "/app/data/qqq_history_cache.csv"
OUTPUT_DATA = "/app/data/factor_derivative_momentum_audit.csv"

def precompute_factors():
    print("Loading datasets...")
    macro = pd.read_csv(MACRO_DATA, parse_dates=["observation_date"])
    qqq = pd.read_csv(QQQ_DATA, parse_dates=["Date"])
    
    macro = macro.sort_values("observation_date").set_index("observation_date")
    qqq = qqq.sort_values("Date").set_index("Date")
    
    macro.index = pd.to_datetime(macro.index, utc=True).tz_convert(None).normalize()
    qqq.index = pd.to_datetime(qqq.index, utc=True).tz_convert(None).normalize()
    
    print(f"Macro range: {macro.index.min()} to {macro.index.max()}")
    print(f"QQQ range: {qqq.index.min()} to {qqq.index.max()}")

    # 1. Calculate Vectorized Derivatives
    print("Calculating derivatives...")
    # Credit Spread (bps)
    macro["credit_momentum_21d"] = macro["credit_spread_bps"].diff(21)
    macro["credit_accel_21d"] = macro["credit_momentum_21d"].diff(21)
    
    # Net Liquidity (USD BN)
    macro["liq_momentum_4w"] = macro["net_liquidity_usd_bn"].diff(20) # Approx 4 weeks
    macro["liq_accel_4w"] = macro["liq_momentum_4w"].diff(20)
    
    print(f"Macro non-NaN accel count: {macro['credit_accel_21d'].count()}")

    # 2. Identify QQQ Drawdowns > 15%
    print("Identifying drawdowns...")
    qqq["peak"] = qqq["Close"].expanding().max()
    qqq["drawdown"] = (qqq["Close"] / qqq["peak"]) - 1
    
    # Labeling Stress Nodes
    qqq["is_stress"] = qqq["drawdown"] < -0.15
    
    # 3. Correlation: Derivative -> Future Drawdown (60d)
    print("Correlating factors...")
    joined = qqq[["Close", "drawdown"]].join(macro[["credit_momentum_21d", "credit_accel_21d", "liq_momentum_4w", "liq_accel_4w"]], how="left").ffill()
    
    print(f"Joined non-NaN accel count: {joined['credit_accel_21d'].count()}")
    
    # Look-ahead labels for correlation (Absolute Max Drawdown in next 60 days)
    # Forward-looking rolling windows need to be careful with indexing
    joined["fwd_max_dd_60d"] = joined["drawdown"].rolling(window=60, min_periods=1).min().shift(-60)
    
    # Masking for valid periods
    valid_mask = joined["credit_accel_21d"].notna() & joined["fwd_max_dd_60d"].notna()
    correlation_matrix = joined[valid_mask][["credit_momentum_21d", "credit_accel_21d", "liq_momentum_4w", "fwd_max_dd_60d"]].corr()
    
    print("\n--- Factor Momentum Correlation with Fwd Max Drawdown (60d) ---")
    print(correlation_matrix["fwd_max_dd_60d"].sort_values())
    
    # 4. Stress Node Analysis
    stress_events = [
        ("Dot-com", "2000-03-01", "2002-10-31"),
        ("GFC", "2007-10-01", "2009-03-31"),
        ("2011 Crisis", "2011-07-01", "2011-10-31"),
        ("2018 QT", "2018-10-01", "2018-12-31"),
        ("COVID-19", "2020-02-01", "2020-04-30"),
        ("2022 Inflation", "2022-01-01", "2022-10-31")
    ]
    
    results = []
    for name, start, end in stress_events:
        node_data = joined.loc[start:end]
        if node_data.empty: continue
        
        peak_idx = node_data["Close"].idxmax()
        peak_date = peak_idx
        
        # Leading Signal Assessment: Acceleration 20 days BEFORE peak
        pre_peak = joined.loc[:peak_date].iloc[-21:-1]
        avg_accel = pre_peak["credit_accel_21d"].mean()
        
        results.append({
            "Crisis": name,
            "Peak Date": peak_date,
            "Pre-Peak Credit Accel": avg_accel,
            "Max Drawdown": node_data["drawdown"].min()
        })
    
    summary_df = pd.DataFrame(results)
    print("\n--- Crisis Node Signal Lead Analysis ---")
    print(summary_df)
    
    # Export for Phase 2 implementation
    joined.to_csv(OUTPUT_DATA)
    print(f"\nAudit data exported to {OUTPUT_DATA}")

if __name__ == "__main__":
    precompute_factors()
