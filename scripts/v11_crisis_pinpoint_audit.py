#!/usr/bin/env python3
"""v11 Research: Crisis & Recovery Pinpoint Audit.
Evaluates Risk Control (Escape) and Bottom Fishing (Recovery) performance.
Focuses on 2025-2026 recent stress periods.
"""
import pandas as pd
import numpy as np
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_v11_5_signals(df):
    """Implementing v11.5 Registry Windows."""
    # Class A: Macro Anchors
    df["sig_yield"] = -df["real_yield_10y_pct"].ewm(span=252).mean().diff(252)
    # Class B: Tactical Pacing
    df["sig_vix"] = df["vix"].ewm(span=126).mean().diff(126)
    # Class C: Structural Drift
    df["sig_breadth"] = -df["breadth_proxy"].ewm(span=252).mean().diff(252)
    
    # Normalization
    for c in ["sig_yield", "sig_vix", "sig_breadth"]:
        df[c] = (df[c] - df[c].rolling(252).mean()) / df[c].rolling(252).std()
    
    # 200-day Trend Line
    df["ma200"] = df["qqq_close"].rolling(200).mean()
    df["below_ma200"] = (df["qqq_close"] < df["ma200"]).astype(int)
    
    return df

def run_simulation(df):
    """v11.5 Probabilistic Logic Simulation."""
    # Composite Stress Score
    df["stress_score"] = (df["sig_yield"].fillna(0) * 0.4 + 
                          df["sig_vix"].fillna(0) * 0.4 + 
                          df["sig_breadth"].fillna(0) * 0.2)
    
    # Beta Decision
    df["target_beta"] = 1.0
    # De-risking
    df.loc[df["stress_score"] > 1.0, "target_beta"] = 0.5
    df.loc[df["stress_score"] > 2.0, "target_beta"] = 0.0
    # Recovery: Faster recovery if VIX (sig_vix) starts cooling and MA200 is reclaimed
    df.loc[(df["stress_score"] < 0.5) & (df["sig_vix"] < 0), "target_beta"] = 1.0
    
    # Calculate Drawdown
    df["hwm"] = df["qqq_close"].expanding().max()
    df["dd"] = (df["qqq_close"] / df["hwm"] - 1.0)
    
    return df

def audit_window(df, name, start, end):
    w = df[(df["observation_date"] >= start) & (df["observation_date"] <= end)].copy()
    if w.empty: return None
    
    max_dd = w["dd"].min()
    bottom_idx = w["qqq_close"].idxmin()
    bottom_date = w.loc[bottom_idx, "observation_date"]
    bottom_beta = w.loc[bottom_idx, "target_beta"]
    
    # Escape Lead
    crash_thresh_idx = w[w["dd"] < -0.15].index
    if not crash_thresh_idx.empty:
        crash_date = w.loc[crash_thresh_idx[0], "observation_date"]
        escape_candidates = w[w["target_beta"] < 1.0].index
        if not escape_candidates.empty:
            escape_date = w.loc[escape_candidates[0], "observation_date"]
            escape_lead = (crash_date - escape_date).days
        else:
            escape_lead = -99 # Missed
    else:
        escape_lead = 0
        
    # Recovery Lead
    recovery_candidates = w[(w["observation_date"] > bottom_date) & (w["target_beta"] >= 0.9)].index
    if not recovery_candidates.empty:
        recovery_date = w.loc[recovery_candidates[0], "observation_date"]
        recovery_lead = (recovery_date - bottom_date).days
    else:
        recovery_lead = -99
        
    return {
        "Name": name,
        "Max DD": f"{max_dd:.1%}",
        "Escape Lead": f"{escape_lead}d",
        "Bottom Beta": f"{bottom_beta:.1f}",
        "Recovery Lead": f"{recovery_lead}d",
        "Below MA200": "YES" if w["below_ma200"].any() else "NO"
    }

def run_audit():
    # Load Data
    df = pd.read_csv("data/v11_poc_phase1_results.csv")
    macro = pd.read_csv("data/macro_historical_dump.csv")
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    macro["observation_date"] = pd.to_datetime(macro["observation_date"])
    
    # Enrich
    df = pd.merge(df, macro[["observation_date", "real_yield_10y_pct", "vix"]], on="observation_date", how="left")
    df = df.sort_values("observation_date")
    
    # Process
    df = get_v11_5_signals(df)
    df = run_simulation(df)
    
    crises = [
        ("2020 COVID", "2020-01-01", "2020-06-30"),
        ("2022 QT Bear", "2021-12-01", "2022-12-31"),
        ("2025 Mar-Apr Flash", "2025-02-15", "2025-05-30"),
        ("2025 Oct-2026 Mar", "2025-10-01", "2026-03-30")
    ]
    
    results = []
    for name, s, e in crises:
        res = audit_window(df, name, s, e)
        if res: results.append(res)
        
    audit_df = pd.DataFrame(results)
    print("\n" + "="*90)
    print(f"{'Crisis Event':<20} | {'Max DD':<8} | {'Escape':<8} | {'Btm Beta':<8} | {'Recovery':<10} | {'MA200'}")
    print("-" * 90)
    for _, r in audit_df.iterrows():
        print(f"{r['Name']:<20} | {r['Max DD']:>8} | {r['Escape']:>8} | {r['Bottom Beta']:>8} | {r['Recovery']:>10} | {r['MA200']}")
    print("="*90)
    print("Metrics: Escape (Lead to -15% DD), Bottom Beta (Beta at low), Recovery (Days after bottom to Beta 1.0)")

if __name__ == "__main__":
    run_audit()
