import logging
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.engine.baseline.data_loader import load_all_baseline_data
from src.engine.baseline.execution import calculate_baseline_oos_series
from src.engine.baseline.sidecar import generate_sidecar_target
from src.engine.baseline.validation import generate_baseline_target
from src.engine.v11.conductor import V11Conductor
from src.engine.v14.tail_risk_radar import TailRiskRadar
from src.regime_topology import ACTIVE_REGIME_ORDER, REGIME_HEX_COLORS

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def _get_close_series(df: pd.DataFrame) -> pd.Series:
    """Helper to extract a clean Close series from yfinance MultiIndex or Flat frame."""
    if df.empty:
        return pd.Series(dtype=float)
    if isinstance(df.columns, pd.MultiIndex):
        if "Close" in df.columns.get_level_values(0):
            ser = df["Close"]
        else:
            ser = df.iloc[:, 0]
    else:
        close_col = next((c for c in ["Close", "Adj Close"] if c in df.columns), df.columns[0])
        ser = df[close_col]
    if isinstance(ser, pd.DataFrame):
        ser = ser.iloc[:, 0]
    ser.index = pd.to_datetime(ser.index).tz_localize(None)
    return ser

def run_panorama_visualization(oos_start="2018-01-01", oos_end=None):
    logger.info(f"Starting Panorama Visualization from {oos_start} to {oos_end or 'Latest'}...")

    # 1. Initialize Engines
    conductor = V11Conductor()
    radar = TailRiskRadar()

    # AC-0/V12-FIX: Force reset high_entropy_streak for clean backtest/forensic report
    conductor.high_entropy_streak = 0
    # Industrial Hardening: Ensure conductor uses the same shared DNA loader instead of its own files
    # This prevents 'Source Drift' between backtest loop and JIT training.
    conductor.macro_data_path = "data/macro_historical_dump.csv"

    # 2. Load Data
    data = load_all_baseline_data(timeout=30)
    if data.empty:
        raise ValueError("Macro data empty.")

    # Filter by date range
    if oos_end:
        data = data[data.index <= oos_end]

    # Simulate Price History
    import yfinance as yf
    # Download enough data for the targets
    dl_end = (pd.to_datetime(oos_end) + pd.Timedelta(days=10)).strftime("%Y-%m-%d") if oos_end else None
    spy_raw = yf.download("SPY", start="2010-01-01", end=dl_end, progress=False)
    qqq_raw = yf.download("QQQ", start="2010-01-01", end=dl_end, progress=False)

    spy_close = _get_close_series(spy_raw).tz_localize(None)
    qqq_close = _get_close_series(qqq_raw).tz_localize(None)

    qqq_close = _get_close_series(qqq_raw).tz_localize(None)

    vix = data["stress_vix"]
    vxn = data.get("stress_vxn", pd.Series(np.nan, index=data.index))

    target_spy = generate_baseline_target(spy_close, vix)
    target_qqq = generate_sidecar_target(qqq_close, vxn)

    # 3. Run Baseline (The "Percentages" shown in UI)
    logger.info("Executing Baseline OOS (UI Percentages)...")
    baseline_results = calculate_baseline_oos_series(
        data, target_spy, target_qqq, start_date=oos_start
    )
    if oos_end:
        baseline_results = baseline_results[baseline_results.index <= oos_end]

    # 4. Run Bayesian 4-Regime & Tail Risk Radar
    logger.info("Executing Bayesian 4-Regime & Tail Risk Radar Loop...")
    dates = data.index[(data.index >= oos_start)]
    if oos_end:
        dates = dates[dates <= oos_end]
    dates = dates.unique()

    regime_probs = []
    radar_spy = []
    radar_qqq = []

    # V14-FIX: Removing the mock nonexistent path to allow conductor to access ground-truth context
    # if it fails to receive sufficient rolling history from the daily_run slice.

    for dt in dates:
        # T+0 snapshot for conductor
        # Bayesian 4-Regime
        try:
            # FORCE RESET STREAK FOR FORENSIC BACKTEST
            conductor.high_entropy_streak = 0

            # Pass only the context up to DT
            runtime = conductor.daily_run(data.loc[:dt])
            probs = runtime["probabilities"]

            # Check for fallback
            if "bayesian_diagnostics" in runtime and not runtime["bayesian_diagnostics"].get("level_contributions"):
                 # This usually flags a fallback to priors
                 pass

            regime_probs.append({r: probs.get(r, 0.0) for r in ACTIVE_REGIME_ORDER})
        except Exception as e:
            logger.warning(f"Conductor failed at {dt}: {e}")
            regime_probs.append({r: 0.0 for r in ACTIVE_REGIME_ORDER})

        # Tail Risk Radar
        diag = conductor.seeder.latest_diagnostics()
        if not diag.empty:
            zscores = diag.iloc[-1].to_dict()
            spy_radar_res = radar.compute(zscores)
            radar_spy.append({k: v["probability"] for k, v in spy_radar_res.items()})
            radar_qqq.append({k: v["probability"] for k, v in spy_radar_res.items()})
        else:
            radar_spy.append({k: 0.0 for k in radar.SCENARIOS})
            radar_qqq.append({k: 0.0 for k in radar.SCENARIOS})

    # Conductor path restored implicitly by removing temporary change

    # Combine results
    df_regime = pd.DataFrame(regime_probs, index=dates)
    df_radar_spy = pd.DataFrame(radar_spy, index=dates)
    df_radar_qqq = pd.DataFrame(radar_qqq, index=dates)

    # 5. Plotting
    logger.info("Generating multi-panel visualization...")
    fig, axes = plt.subplots(4, 1, figsize=(18, 24), sharex=True, gridspec_kw={'height_ratios': [1, 0.8, 1, 1]})
    plt.subplots_adjust(hspace=0.4)

    # Common X-axis dates
    plot_dates = df_regime.index

    # Panel A: 4-Regime Stacked Area
    colors = [REGIME_HEX_COLORS.get(r, "#cccccc") for r in ACTIVE_REGIME_ORDER]
    axes[0].stackplot(plot_dates, df_regime.values.T, labels=ACTIVE_REGIME_ORDER, colors=colors, alpha=0.8)

    # Overlay Ground Truth (SPY Crisis)
    y_target = target_spy.reindex(plot_dates).ffill().fillna(0)
    axes[0].fill_between(plot_dates, 0, 1, where=(y_target > 0.5), color='black', alpha=0.15, label='Actual Crisis (SPY)')
    axes[0].set_title("Panel A: 4-Regime Posterior Probabilities (MID/LATE/BUST/RECOVERY)", fontsize=16, fontweight='bold')
    axes[0].set_ylim(0, 1)
    axes[0].legend(loc='upper left', ncol=5, frameon=True)
    axes[0].grid(axis='y', linestyle='--', alpha=0.3)

    # Panel B: UI Diagnostic Percentages
    # Reindex baseline results to match plot_dates
    bl_aligned = baseline_results.reindex(plot_dates).ffill()
    axes[1].plot(plot_dates, bl_aligned["tractor_prob"], label="Mud Tractor (SPY %)", color="#e74c3c", linewidth=2.5)
    axes[1].plot(plot_dates, bl_aligned["sidecar_prob"], label="QQQ Sidecar (%)", color="#3498db", linewidth=2, linestyle='--')
    axes[1].axhline(0.20, color="#e74c3c", linestyle=":", alpha=0.6, label="Tractor Threshold (0.20)")
    axes[1].axhline(0.15, color="#3498db", linestyle=":", alpha=0.6, label="Sidecar Threshold (0.15)")
    axes[1].set_title("Panel B: Aggregate Crisis Probabilities (UI Percentages)", fontsize=16, fontweight='bold')
    axes[1].set_ylim(0, 1)
    axes[1].legend(loc='upper left', frameon=True)
    axes[1].grid(linestyle='--', alpha=0.3)

    # Helper for Heatmaps
    def plot_heatmap(ax, df, title, cmap):
        # Transpose data: columns become Y, index becomes X
        data = df.values.T
        y_labels = df.columns

        # pcolormesh with shading='auto' or 'nearest'
        Y = np.arange(len(y_labels))
        mesh = ax.pcolormesh(plot_dates, Y, data, cmap=cmap, shading='auto', vmin=0, vmax=0.8)

        ax.set_yticks(np.arange(len(y_labels)) + 0.5)
        ax.set_yticklabels(y_labels)
        ax.set_title(title, fontsize=16, fontweight='bold')
        fig.colorbar(mesh, ax=ax, label='Intensity', pad=0.01)
        return mesh

    # Panel C: Fat-Tail Radar (Mud Tractor)
    plot_heatmap(axes[2], df_radar_spy, "Panel C: Fat-Tail Radar Intensity (Mud Tractor - Macro)", "YlOrRd")

    # Panel D: Fat-Tail Radar (QQQ Sidecar)
    plot_heatmap(axes[3], df_radar_qqq, "Panel D: Fat-Tail Radar Intensity (QQQ Sidecar - Tech Tech)", "YlOrBr")

    # Format X-axis with nice dates
    import matplotlib.dates as mdates
    if len(plot_dates) > 500:
        axes[3].xaxis.set_major_locator(mdates.YearLocator())
        axes[3].xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    else:
        axes[3].xaxis.set_major_locator(mdates.MonthLocator())
        axes[3].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

    for ax in axes:
        ax.set_xlabel("Timeline")
        ax.tick_params(labelsize=12)

    output_path = "artifacts/regime_backtest_panorama.png"
    os.makedirs("artifacts", exist_ok=True)
    plt.savefig(output_path, bbox_inches='tight', dpi=120)
    logger.info(f"Panorama updated at {output_path}")

    # Export data for forensic report
    trace_df = pd.concat([df_regime, bl_aligned, df_radar_spy.add_prefix("radar_")], axis=1)
    trace_df.to_csv("artifacts/panorama_trace.csv")

if __name__ == "__main__":
    import sys
    start_date = sys.argv[1] if len(sys.argv) > 1 else "2018-01-01"
    end_date = sys.argv[2] if len(sys.argv) > 2 else None
    run_panorama_visualization(start_date, end_date)
