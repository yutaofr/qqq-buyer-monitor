import os

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.regime_topology import ACTIVE_REGIME_ORDER, REGIME_HEX_COLORS


def calculate_metrics(df):
    regimes = list(ACTIVE_REGIME_ORDER)

    # 1. Cross-Entropy
    # P is ground truth (1.0 for actual_regime), Q is posterior
    # H(P, Q) = -sum(P(x)log(Q(x)))
    # Since P is 1.0 for actual_regime, it's just -log(prob_actual)
    eps = 1e-15
    df["cross_entropy"] = -np.log(df["actual_regime_probability"].clip(lower=eps))
    mean_cross_entropy = df["cross_entropy"].mean()

    # 3. Transition Latency
    # Detect transition points in Ground Truth
    df["regime_change"] = df["actual_regime"] != df["actual_regime"].shift(1)
    transitions = df[df["regime_change"]].index[1:]  # Skip first

    latencies = []
    for t_idx in transitions:
        new_regime = df.loc[t_idx, "actual_regime"]
        # Find when model probability for new_regime exceeds 50% (or peaks) after t_idx
        post_window = df.loc[t_idx : t_idx + pd.Timedelta(days=30)]
        prob_col = f"prob_{new_regime}"
        caught = post_window[post_window[prob_col] > 0.5]
        if not caught.empty:
            latency = (caught.index[0] - t_idx).days
            latencies.append(latency)

    avg_latency = np.mean(latencies) if latencies else 0

    # 4. Per-regime metrics
    per_regime = {}
    for r in regimes:
        mask = df["actual_regime"] == r
        if mask.any():
            sub = df[mask]
            per_regime[r] = {
                "count": int(mask.sum()),
                "mean_brier": float(sub["brier"].mean()),
                "mean_cross_entropy": float(sub["cross_entropy"].mean()),
            }

    return {
        "mean_cross_entropy": float(mean_cross_entropy),
        "avg_transition_latency_days": float(avg_latency),
        "per_regime_stats": per_regime,
    }


def plot_regime_diagnostic(df, output_path, title_suffix=""):
    fig, axes = plt.subplots(
        3, 1, figsize=(18, 20), sharex=True, gridspec_kw={"height_ratios": [3, 0.8, 1.2]}
    )
    plt.subplots_adjust(hspace=0.1)

    plot_dates = df.index
    regimes = list(ACTIVE_REGIME_ORDER)
    colors = [REGIME_HEX_COLORS.get(r, "#cccccc") for r in regimes]

    # Panel 1: Posterior Probabilities
    probs = df[[f"prob_{r}" for r in regimes]].values.T
    axes[0].stackplot(plot_dates, probs, labels=regimes, colors=colors, alpha=0.85)
    axes[0].set_ylim(0, 1)
    axes[0].set_ylabel("Posterior Probability", fontsize=14)
    axes[0].legend(loc="upper left", ncol=4, frameon=True, fontsize=12)
    axes[0].set_title(
        f"Bayesian Regime Posterior Probabilities{title_suffix}", fontsize=18, fontweight="bold"
    )
    axes[0].grid(axis="y", linestyle="--", alpha=0.3)

    # Panel 2: Expected Regime Ribbon
    bar_width = 1.0
    if len(plot_dates) > 1:
        # Dynamically sense the average width in days
        diffs = pd.Series(plot_dates).diff().median().total_seconds() / 86400.0
        bar_width = max(1.0, diffs * 1.05)  # Add 5% padding to avoid slivers

    for i, r in enumerate(regimes):
        mask = df["actual_regime"] == r
        if mask.any():
            axes[1].bar(
                df.index[mask],
                1,
                width=bar_width,
                color=colors[i],
                align="center",
                linewidth=0,
                alpha=1.0,
            )

    axes[1].set_yticks([])
    axes[1].set_ylim(0, 1)
    axes[1].set_ylabel("Expected", fontsize=14, rotation=0, labelpad=40)

    # Panel 3: QQQ Context + Entropy
    axes[2].plot(plot_dates, df["close"], color="#0b5fff", linewidth=2, label="QQQ Price")
    axes[2].set_ylabel("Price ($)", fontsize=14, color="#0b5fff")

    ax_entropy = axes[2].twinx()
    ax_entropy.plot(
        plot_dates, df["entropy"], color="#34495e", linewidth=1.5, alpha=0.6, label="Info Entropy"
    )
    ax_entropy.fill_between(plot_dates, 0, df["entropy"], color="#34495e", alpha=0.1)
    ax_entropy.set_ylabel("Entropy", fontsize=14, color="#34495e")
    ax_entropy.set_ylim(0, 1.1)

    # Format dates
    axes[2].xaxis.set_major_locator(mdates.AutoDateLocator())
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    plt.savefig(output_path, bbox_inches="tight", dpi=120)
    plt.close()


def run_visualization_suite(audit_csv="artifacts/v12_audit/full_audit.csv"):
    if not os.path.exists(audit_csv):
        print(f"Error: {audit_csv} not found.")
        return

    df = pd.read_csv(audit_csv, parse_dates=["date"]).set_index("date")
    df = df.sort_index()

    os.makedirs("artifacts/diagnostics", exist_ok=True)

    # Full Panorama
    print("Generating Panorama...")
    plot_regime_diagnostic(
        df, "artifacts/diagnostics/expected_vs_posterior_panorama.png", " (Panorama)"
    )

    # Slices
    slices = {
        "2000_tech_bubble": ("2000-01-01", "2002-12-31"),
        "2008_gf_crisis": ("2007-06-01", "2009-12-31"),
        "2020_covid": ("2020-01-01", "2021-06-30"),
        "oos_recent": ("2022-01-01", "2026-12-31"),
    }

    for name, (start, end) in slices.items():
        sub_df = df.loc[start:end]
        if not sub_df.empty:
            print(f"Generating slice: {name}")
            plot_regime_diagnostic(
                sub_df,
                f"artifacts/diagnostics/slice_{name}.png",
                f" ({name.replace('_', ' ').title()})",
            )

    # Metrics
    metrics = calculate_metrics(df)
    import json

    with open("artifacts/diagnostics/ml_expert_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print("Metrics exported to artifacts/diagnostics/ml_expert_metrics.json")


if __name__ == "__main__":
    run_visualization_suite()
