import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def plot_full_analysis():
    trace_path = "/Users/weizhang/w/backtests/artifacts/v13_matrix/full/full_audit.csv"
    if not os.path.exists(trace_path):
         print("File not found.")
         return

    df = pd.read_csv(trace_path, parse_dates=["date"])
    
    tractor_prob_col = 'tractor_prob'
    sidecar_prob_col = 'sidecar_prob'
    
    if tractor_prob_col not in df.columns:
        if os.path.exists("/Users/weizhang/w/backtests/artifacts/v14_panorama/baseline_oos_trace.csv"):
            baseline = pd.read_csv("/Users/weizhang/w/backtests/artifacts/v14_panorama/baseline_oos_trace.csv")
            baseline.rename(columns={baseline.columns[0]: "date"}, inplace=True)
            baseline['date'] = pd.to_datetime(baseline['date'])
            df = pd.merge(df, baseline, on="date", how="left")
            df[tractor_prob_col] = pd.to_numeric(df.get(tractor_prob_col, 0), errors="coerce").fillna(0)
            df[sidecar_prob_col] = pd.to_numeric(df.get(sidecar_prob_col, 0), errors="coerce").fillna(0)
        else:
            df[tractor_prob_col] = 0
            df[sidecar_prob_col] = 0

    
    # 4 Subplots needed: Regime Area, Entropy, Risks, Price Trend
    fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(16, 22), sharex=True)
    
    # 1. 总体趋势图 (Area chart of probabilities)
    ax1.stackplot(df["date"], 
                  df["prob_RECOVERY"], 
                  df["prob_MID_CYCLE"], 
                  df["prob_LATE_CYCLE"], 
                  df["prob_BUST"], 
                  labels=["RECOVERY (Green)", "MID_CYCLE (Blue)", "LATE_CYCLE (Yellow)", "BUST (Red)"],
                  colors=["green", "blue", "yellow", "red"], alpha=0.7)
    ax1.set_title("1. 8-Year Full History Regime Probabilities Area Chart")
    ax1.legend(loc="upper left")
    ax1.grid(True)
    
    # 2. Entropy
    ax2.plot(df["date"], df["entropy"], label="System Entropy", color="purple")
    ax2.set_title("2. System Entropy Evolution (8 Years)")
    ax2.legend(loc="upper left")
    ax2.grid(True)

    # 3. Tractor and Sidecar Left Tail Risk
    ax3.plot(df["date"], df[tractor_prob_col], label="Tractor Left-Tail Risk Prob", color="orange")
    ax3.plot(df["date"], df[sidecar_prob_col], label="QQQ Sidecar Risk Prob", color="cyan")
    ax3.set_title("3. Left-Tail Risk Probabilities (Tractor & Sidecar) (8 Years)")
    ax3.legend(loc="upper left")
    ax3.grid(True)

    # 4. QQQ Price 
    ax4.plot(df["date"], df["close"], color="black", label="QQQ Price")
    ax4.set_title("4. QQQ Price Overlay (8 Years)")
    ax4.legend(loc="upper left")
    ax4.grid(True)
    
    plt.tight_layout()
    os.makedirs("/Users/weizhang/w/backtests/artifacts/analysis", exist_ok=True)
    plt.savefig("/Users/weizhang/w/backtests/artifacts/analysis/full_8yr_trend_plot_detailed.png")
    print("Saved to /Users/weizhang/w/backtests/artifacts/analysis/full_8yr_trend_plot_detailed.png")

if __name__ == "__main__":
    plot_full_analysis()
