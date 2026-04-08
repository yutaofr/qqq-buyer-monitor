import json
import os

import numpy as np
import pandas as pd


def calculate_ece(y_true, y_prob, n_bins=10):
    """Calculate Expected Calibration Error (ECE)."""
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    bin_lowers = bin_boundaries[:-1]
    bin_uppers = bin_boundaries[1:]

    ece = 0.0
    for bin_lower, bin_upper in zip(bin_lowers, bin_uppers, strict=True):
        # Find indices in current bin
        in_bin = (y_prob > bin_lower) & (y_prob <= bin_upper)
        prop_in_bin = np.mean(in_bin)

        if prop_in_bin > 0:
            accuracy_in_bin = np.mean(y_true[in_bin])
            avg_confidence_in_bin = np.mean(y_prob[in_bin])
            ece += prop_in_bin * np.abs(avg_confidence_in_bin - accuracy_in_bin)

    return ece

def audit_tau_dynamics(artifact_dir, name):
    full_path = os.path.join(artifact_dir, "full_audit.csv")
    if not os.path.exists(full_path):
        print(f"Skipping {name}: file not found at {full_path}")
        return None

    df = pd.read_csv(full_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    regimes = ['MID_CYCLE', 'LATE_CYCLE', 'BUST', 'RECOVERY']
    # 1. 1st Derivative (Velocity)
    for r in regimes:
        col = f'prob_{r}'
        df[f'{col}_v1'] = df[col].diff()
        # 2. 2nd Derivative (Acceleration)
        df[f'{col}_v2'] = df[f'{col}_v1'].diff()

    # Metrics
    metrics = {
        "name": name,
        "mean_absolute_v1": df[[f'prob_{r}_v1' for r in regimes]].abs().mean().mean(),
        "mean_absolute_v2": df[[f'prob_{r}_v2' for r in regimes]].abs().mean().mean(),
        "v1_volatility": df[[f'prob_{r}_v1' for r in regimes]].std().mean(),
        "ece_per_regime": {}
    }

    # Calibration Audit
    for r in regimes:
        y_true = (df['actual_regime'] == r).astype(int)
        y_prob = df[f'prob_{r}']
        metrics["ece_per_regime"][r] = calculate_ece(y_true, y_prob)

    metrics["mean_ece"] = np.mean(list(metrics["ece_per_regime"].values()))

    # Analyze Specific Cycles (e.g. 2020 Pivot)
    covid_pivot = df[(df['date'] >= '2020-02-15') & (df['date'] <= '2020-03-31')]
    if not covid_pivot.empty:
        metrics["covid_max_v1"] = covid_pivot[['prob_BUST_v1']].abs().max().values[0]
        metrics["covid_max_v2"] = covid_pivot[['prob_BUST_v2']].abs().max().values[0]

    return metrics

if __name__ == "__main__":
    configs = [
        ("artifacts/v12_audit_tau25", "Tau 2.5"),
        ("artifacts/v12_audit_tau50", "Tau 5.0"),
        ("artifacts/v12_audit_tau100", "Tau 10.0")
    ]

    results = []
    for path, name in configs:
        m = audit_tau_dynamics(path, name)
        if m:
            results.append(m)

    print(json.dumps(results, indent=2))

    # Save to artifact directory
    with open("artifacts/distribution_dynamics_summary.json", "w") as f:
        json.dump(results, f, indent=2)
