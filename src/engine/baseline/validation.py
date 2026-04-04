import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import roc_auc_score

from src.engine.baseline.engine import predict_baseline_crisis_prob, train_baseline_model
from src.engine.baseline.targets import align_target_inputs

logger = logging.getLogger(__name__)


def generate_baseline_target(
    price_series: pd.Series, vix_series: pd.Series, horizon: int = 20
) -> pd.Series:
    aligned = align_target_inputs(price_series, vix_series)
    price_series = aligned["price"]
    vix_series = aligned["stress"]
    n = len(price_series)
    y = pd.Series(0.0, index=price_series.index)
    for i in range(n - horizon):
        window = price_series.iloc[i + 1 : i + 1 + horizon]
        vix_window = vix_series.iloc[i + 1 : i + 1 + horizon]
        if window.isna().any() or vix_window.isna().any() or pd.isna(price_series.iloc[i]):
            y.iloc[i] = np.nan
            continue
        if ((price_series.iloc[i] - window.min()) / price_series.iloc[i] > 0.08) or vix_window.max() > 30:
            y.iloc[i] = 1
    y.iloc[-horizon:] = np.nan
    return y.dropna()


def run_ac2_label_permutation_test(X: pd.DataFrame, y: pd.Series, n_shuffles: int = 20):
    from src.engine.baseline.engine import (
        predict_baseline_crisis_prob,
        train_baseline_model,
    )

    rng = np.random.default_rng(42)
    aucs = []
    n = len(X)
    cadence = 21
    start_idx = int(n * 0.5)
    for _ in range(n_shuffles):
        y_shuffled = rng.permutation(y.values)
        y_shuffled_ser = pd.Series(y_shuffled, index=y.index)
        all_oos_probs = []
        all_oos_targets = []
        model = None
        for i in range(start_idx, n):
            if (i - start_idx) % cadence == 0:
                y_train = y_shuffled_ser.iloc[:i]
                if len(np.unique(y_train)) > 1:
                    model = train_baseline_model(X.iloc[:i], y_train)
            if model is not None:
                all_oos_probs.append(float(predict_baseline_crisis_prob(model, X.iloc[[i]]).iloc[0]))
                all_oos_targets.append(y_shuffled_ser.iloc[i])
        if all_oos_probs and len(np.unique(all_oos_targets)) > 1:
            aucs.append(roc_auc_score(all_oos_targets, all_oos_probs))
    return float(np.mean(aucs)) if aucs else 0.5


def run_ac2_leakage_detection():
    from src.engine.baseline.engine import predict_baseline_crisis_prob, train_baseline_model

    rng = np.random.default_rng(42)
    n = 1000
    dates = pd.date_range("2010-01-01", periods=n, freq="B")
    latent = np.zeros(n)
    for i in range(1, n):
        latent[i] = 0.95 * latent[i - 1] + rng.standard_normal()
    y = pd.Series((latent > 0).astype(int), index=dates)
    X_safe = pd.DataFrame(rng.standard_normal((n, 3)), index=dates, columns=["feat_0", "feat_1", "feat_2"])
    X_leaky = X_safe.copy()
    X_leaky["future_label"] = pd.Series(y.values, index=dates).shift(-1).fillna(0).astype(float)

    def _walk_forward_auc(features: pd.DataFrame) -> float:
        probs = []
        targets = []
        start_idx = 500
        model = None
        for i in range(start_idx, n):
            if (i - start_idx) % 100 == 0:
                model = train_baseline_model(features.iloc[:i], y.iloc[:i])
            if model is not None:
                probs.append(float(predict_baseline_crisis_prob(model, features.iloc[[i]]).iloc[0]))
                targets.append(int(y.iloc[i]))
        return roc_auc_score(targets, probs) if len(np.unique(targets)) > 1 else 0.5

    pit_safe_probs = []
    targets = []
    start_idx = 500
    model = None
    for i in range(start_idx, n):
        if (i - start_idx) % 100 == 0:
            model = train_baseline_model(X_safe.iloc[:i], y.iloc[:i])
        if model is not None:
            pit_safe_probs.append(float(predict_baseline_crisis_prob(model, X_safe.iloc[[i]]).iloc[0]))
            targets.append(int(y.iloc[i]))

    auc_pit = roc_auc_score(targets, pit_safe_probs) if len(np.unique(targets)) > 1 else 0.5
    auc_leaky = _walk_forward_auc(X_leaky)

    return {
        "pit_safe_auc": float(auc_pit),
        "leaky_auc": float(auc_leaky),
        "leakage_detected": bool(auc_leaky > auc_pit + 0.1)
    }


def plot_ac3_reliability_diagram(y_true, y_prob, n_bins=5, save_path=None):
    if len(np.unique(y_prob)) < 2:
        logger.warning("AC-3: Probability collapse detected (all values same). Calibration invalid.")
        return None, None

    prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=n_bins)

    plt.figure(figsize=(8, 6))
    plt.plot(prob_pred, prob_true, marker="o", linewidth=1, label="V_Baseline")
    plt.plot([0, 1], [0, 1], linestyle="--", label="Perfectly calibrated")
    plt.xlabel("Predicted Probability")
    plt.ylabel("Actual Frequency (Y=1)")
    plt.title("AC-3: Reliability Diagram (OOS Calibration)")
    plt.legend()
    plt.grid(True)

    if save_path:
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()

    return prob_true, prob_pred
