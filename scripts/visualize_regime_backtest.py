import logging
import os

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

from src.engine.v11.conductor import V11Conductor
from src.engine.v14.tail_risk_radar import TailRiskRadar
from src.regime_topology import ACTIVE_REGIME_ORDER, REGIME_HEX_COLORS

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def _get_close_series(df: pd.DataFrame) -> pd.Series:
    if df.empty: return pd.Series(dtype=float)
    if isinstance(df.columns, pd.MultiIndex):
        ser = df["Close"] if "Close" in df.columns.get_level_values(0) else df.iloc[:, 0]
    else:
        close_col = next((c for c in ["Close", "Adj Close"] if c in df.columns), df.columns[0])
        ser = df[close_col]
    if isinstance(ser, pd.DataFrame): ser = ser.iloc[:, 0]
    ser.index = pd.to_datetime(ser.index).tz_localize(None)
    return ser

def render_full_panorama(df_regime, df_radar_spy, df_radar_qqq, series_entropy, df_betas, df_signals, baseline_results, qqq_close, spy_close, output_path="artifacts/regime_backtest_panorama.png"):
    logger.info(f"V20-ULTIMATE: Rendering High-Fidelity Panorama to {output_path}...")
    plot_dates = df_regime.index

    # DISABLE sharex for absolute label independence
    fig, axes = plt.subplots(10, 1, figsize=(20, 65), sharex=False,
                             gridspec_kw={'height_ratios': [0.8, 1, 0.8, 1, 1, 0.8, 1, 0.7, 0.7, 0.7]})
    plt.subplots_adjust(hspace=1.5)

    PRICE_COLOR = "#00d2ff"
    qqq_aligned = qqq_close.reindex(plot_dates).ffill()
    spy_aligned = spy_close.reindex(plot_dates).ffill()

    def add_price_overlay(ax, series):
        axp = ax.twinx()
        axp.plot(series.index, series.values, color=PRICE_COLOR, alpha=0.3, linewidth=1.0)
        axp.tick_params(axis='y', labelsize=8)

    # Panel 0: Price
    axes[0].plot(plot_dates, qqq_aligned, color="#2c3e50", linewidth=3, label="QQQ Raw")
    axes[0].set_title("Panel 0: QQQ Price Momentum", fontsize=18, fontweight='bold')

    # Panel 1: Regimes
    cols = [c for c in ACTIVE_REGIME_ORDER if c in df_regime.columns]
    colors = [REGIME_HEX_COLORS.get(c, "#cccccc") for c in cols]
    axes[1].stackplot(plot_dates, df_regime[cols].values.T, labels=cols, colors=colors, alpha=0.8)
    axes[1].set_title("Panel 1: 4-Regime Probabilities", fontsize=18, fontweight='bold')
    axes[1].legend(loc='upper left', ncol=4, fontsize=12)

    # Panel 2: Crisis
    if "tractor_prob" in baseline_results.columns:
        axes[2].plot(plot_dates, baseline_results["tractor_prob"], color="#e74c3c", label="Tractor")
        axes[2].plot(plot_dates, baseline_results["sidecar_prob"], color="#3498db", linestyle="--", label="Sidecar")
    axes[2].set_title("Panel 2: Crisis Probabilities", fontsize=18, fontweight='bold')

    # Panel 3 & 4: Radar
    def plot_radar(ax, df, tit, cm):
        if df.empty:
            # Fallback if no radar columns found
            dummy_cols = ["melt_up", "growth_bust", "credit_crisis", "liquidity_drain"]
            df = pd.DataFrame(0, index=plot_dates, columns=dummy_cols)

        ax.pcolormesh(plot_dates, np.arange(len(df.columns)), df.values.T, cmap=cm, shading='auto', vmin=0, vmax=0.8)
        ax.set_yticks(np.arange(len(df.columns)) + 0.5)
        ax.set_yticklabels(df.columns)
        ax.set_title(tit, fontsize=18, fontweight='bold')

    plot_radar(axes[3], df_radar_spy, "Panel 3: Fat-Tail Radar (Macro)", "YlOrRd")
    plot_radar(axes[4], df_radar_qqq, "Panel 4: Fat-Tail Radar (Tech)", "YlOrBr")

    # Panel 5: Entropy
    axes[5].plot(plot_dates, series_entropy, color="#9b59b6", linewidth=2.5)
    axes[5].axhline(0.8, color="#e74c3c", linestyle="--")
    axes[5].set_title("Panel 5: Info Entropy", fontsize=18, fontweight='bold')

    # Panel 6: Beta
    axes[6].plot(plot_dates, df_betas["raw"], color="#bdc3c7", linestyle="--", alpha=0.6, label="Raw Bayesian Beta")
    axes[6].plot(plot_dates, df_betas["target"], color="#2c3e50", linewidth=3, label="Final Target Beta")
    axes[6].set_title("Panel 6: Beta Surface Dynamics (Strategic De-risking)", fontsize=18, fontweight='bold')
    axes[6].legend(loc='upper left', fontsize=12)
    axes[6].axhline(1.0, color='gray', linestyle=':', alpha=0.5)
    axes[6].axhline(0.5, color='#e74c3c', linestyle=':', alpha=0.5, label="Floor (0.5)")

    # Panel 7: Signals
    axes[7].step(plot_dates, df_signals["res_action"], color="#27ae60", where='post', linewidth=2.5)
    axes[7].set_title("Panel 7: QLD Resonance Signals", fontsize=18, fontweight='bold')

    # Panel 8: Tactical
    sm = {"DEPLOY_PAUSE": 0, "DEPLOY_SLOW": 1, "DEPLOY_BASE": 2, "DEPLOY_FAST": 3}
    num_states = df_signals["deployment_state"].map(sm).fillna(0).values
    axes[8].step(plot_dates, num_states, where='post', color="#2980b9", linewidth=2.5)
    axes[8].set_yticks([0, 1, 2, 3])
    axes[8].set_yticklabels(["STOP", "SLOW", "DCA", "FAST"])
    axes[8].set_title("Panel 8: Tactical Commands", fontsize=18, fontweight='bold')

    # Panel 9: Kelly
    axes[9].plot(plot_dates, df_signals["cdr"], color="#d35400", linewidth=2.5)
    axes[9].set_title("Panel 9: Bayesian Kelly", fontsize=18, fontweight='bold')

    # FORCED AXIS AUDIT
    for i, ax in enumerate(axes):
        add_price_overlay(ax, qqq_aligned)
        ax.set_xlim(plot_dates.min(), plot_dates.max())
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        plt.setp(ax.get_xticklabels(), visible=True, rotation=45, ha='right', fontsize=12)
        ax.tick_params(axis='x', which='both', labelbottom=True, length=6, color='black')
        ax.set_xlabel("Timeline", fontsize=10, color='gray')
        ax.grid(True, linestyle='--', alpha=0.3)

    plt.savefig(output_path, bbox_inches='tight', dpi=130)
    logger.info(f"V20 Panorama EXPORTED to {output_path}")

def run_backtest_simulation(start_date="2018-01-01", end_date="2026-04-09"):
    logger.info(f"V22-ULTIMATE: Running full 8-year forensic simulation from {start_date} to {end_date}...")

    # Initialize Conductor ONCE to preserve state (Resonance Detector timers, etc.)
    conductor = V11Conductor(
        macro_data_path="data/macro_historical_dump.csv",
        regime_data_path="data/v11_poc_phase1_results.csv",
        prior_state_path="artifacts/v11_prior_state_backtest.json",
        price_history_path="data/qqq_history_cache.csv",
        allow_prior_bootstrap_drift=True
    )

    # Clear previous backtest state if exists
    if os.path.exists("artifacts/v11_prior_state_backtest.json"):
        os.remove("artifacts/v11_prior_state_backtest.json")

    regime_df = pd.read_csv("data/v11_poc_phase1_results.csv", parse_dates=["observation_date"]).set_index("observation_date")
    macro_df = pd.read_csv("data/macro_historical_dump.csv", parse_dates=["observation_date"]).set_index("observation_date")

    test_dates = regime_df[(regime_df.index >= start_date) & (regime_df.index <= end_date)].index
    test_dates = [d for d in test_dates if d in macro_df.index]

    # Action Mapping: BUY_QLD=1, HOLD=0, SELL_QLD=-1
    action_map = {"BUY_QLD": 1.0, "HOLD": 0.0, "SELL_QLD": -1.0}

    trace_rows = []
    for dt in test_dates:
        # Update training cutoff for realistic walk-forward
        conductor.training_cutoff = dt - pd.offsets.BDay(20)

        t0_data = macro_df.loc[[dt]]
        try:
            runtime = conductor.daily_run(t0_data)

            res_action_str = runtime.get("signal", {}).get("resonance", {}).get("action", "HOLD")

            # 2. Crisis Inference via TailRiskRadar
            # Mapping Layer: Conductor Z-scores -> TailRiskRadar naming
            raw_z = runtime.get("v13_4_diagnostics", {}).get("z_scores", {})
            if not raw_z:
                raw_z = {k: v for k, v in runtime.get("feature_values", {}).items() if isinstance(v, (int, float))}

            # Map V11 features to V14 Radar expected factor keys
            z_scores = {
                "spread_21d": raw_z.get("credit_acceleration", 0.0),
                "spread_absolute": raw_z.get("spread_absolute", 0.0),
                "liquidity_252d": raw_z.get("liquidity_velocity", 0.0),
                "erp_absolute": raw_z.get("erp_absolute", 0.0),
                "move_21d": raw_z.get("move_21d_raw_z", 0.0),
                "real_yield_structural_z": raw_z.get("real_yield", 0.0),
                "breakeven_accel": raw_z.get("breakeven", 0.0),
                "core_capex_momentum": raw_z.get("core_capex", 0.0),
                "usdjpy_roc_126d": raw_z.get("usdjpy", 0.0),
            }

            radar_results = TailRiskRadar.compute(z_scores)

            # Map Scenarios to Tractor/Sidecar for Subplot 2
            # Tractor (Main Risk): Deflationary Bust, Credit Crisis, Growth Bust, Valuation Compression
            tractor_val = max(
                radar_results.get("deflationary_bust", {}).get("probability", 0.0),
                radar_results.get("credit_crisis", {}).get("probability", 0.0),
                radar_results.get("growth_bust", {}).get("probability", 0.0),
                radar_results.get("valuation_compression", {}).get("probability", 0.0)
            )
            # Sidecar (Supporting Risk): Carry Unwind, Liquidity Drain, Treasury Dislocation
            sidecar_val = max(
                radar_results.get("carry_unwind", {}).get("probability", 0.0),
                radar_results.get("liquidity_drain", {}).get("probability", 0.0),
                radar_results.get("treasury_dislocation", {}).get("probability", 0.0)
            )

            row = {
                "date": dt,
                "entropy": runtime["entropy"],
                "raw_target_beta": runtime["raw_target_beta"],
                "target_beta": runtime["target_beta"],
                "res_action": action_map.get(res_action_str, 0.0),
                "deployment_state": runtime["deployment"]["deployment_state"],
                "cdr": runtime.get("cdr_sharpe", 0.0),
                "tractor_prob": tractor_val,
                "sidecar_prob": sidecar_val
            }

            # Add Radar Individual Probabilities for Panel 3/4
            for scenario, res in radar_results.items():
                row[f"radar_{scenario}"] = res.get("probability", 0.0)

            # Add Posteriors (Panel 1) - RESTORED
            for r in ACTIVE_REGIME_ORDER:
                row[r] = runtime["probabilities"].get(r, 0.0)

            trace_rows.append(row)
            if len(trace_rows) % 100 == 0:
                logger.info(f"Simulated {len(trace_rows)} days...")
        except Exception as e:
            logger.warning(f"Error at {dt}: {e}")
            import traceback
            logger.debug(traceback.format_exc())

    df_trace = pd.DataFrame(trace_rows).set_index("date")
    df_trace.to_csv("artifacts/panorama_trace.csv")
    logger.info("Trace REGENERATED.")
    return df_trace

def run_panorama_visualization(force_simulation=False):
    output_png = "artifacts/regime_backtest_panorama.png"
    trace_path = "artifacts/panorama_trace.csv"

    if force_simulation or not os.path.exists(trace_path) or os.getenv("PLOT_ONLY") != "1":
        df = run_backtest_simulation()
    else:
        logger.info("Loading trace from cache.")
        df = pd.read_csv(trace_path, index_col=0, parse_dates=True)

    df_regime = df[[c for c in ACTIVE_REGIME_ORDER if c in df.columns]]
    df_radar = df[[c for c in df.columns if "radar_" in c]].rename(columns=lambda x: x.replace("radar_", ""))
    series_entropy = df["entropy"]

    df_betas = pd.DataFrame({
        "raw": df["raw_target_beta"],
        "target": df["target_beta"]
    }, index=df.index)

    # Check for missing res_action if loading from old trace
    if "res_action" not in df.columns:
        df["res_action"] = 0.0

    df_signals = df[["res_action", "deployment_state", "cdr"]]
    baseline_results = df[["tractor_prob", "sidecar_prob"]]

    qqq_raw = yf.download("QQQ", start=df.index.min().strftime("%Y-%m-%d"), progress=False)
    spy_raw = yf.download("SPY", start=df.index.min().strftime("%Y-%m-%d"), progress=False)

    render_full_panorama(
        df_regime, df_radar, df_radar, series_entropy, df_betas,
        df_signals, baseline_results,
        _get_close_series(qqq_raw), _get_close_series(spy_raw),
        output_path=output_png
    )

if __name__ == "__main__":
    import sys
    force = len(sys.argv) > 1 or os.getenv("PLOT_ONLY") != "1"
    run_panorama_visualization(force_simulation=force)
