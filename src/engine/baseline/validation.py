import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import roc_auc_score

from src.engine.baseline.engine import predict_baseline_crisis_prob, train_baseline_model


def generate_baseline_target(
    price_series: pd.Series, vix_series: pd.Series, horizon: int = 20
) -> pd.Series:
    """
    SRD: Target Y=1 if SP500 MDD > 8% or VIX > 30 in next 20 days.
    """
    # Calculate rolling MDD for next 'horizon' periods
    # This is a bit complex: for each t, look at t+1 to t+horizon
    n = len(price_series)
    y = pd.Series(0, index=price_series.index)

    for i in range(n - horizon):
        window = price_series.iloc[i + 1 : i + 1 + horizon]
        vix_window = vix_series.iloc[i + 1 : i + 1 + horizon]

        # Max drawdown in window: (P_start - P_min) / P_start
        p_start = price_series.iloc[i]
        p_min = window.min()
        mdd = (p_start - p_min) / p_start

        if mdd > 0.08 or vix_window.max() > 30:
            y.iloc[i] = 1

    # Last 'horizon' points are undefined/NaN as we can't look forward
    y.iloc[-horizon:] = np.nan
    return y.dropna()


def run_ac2_label_permutation_test(X: pd.DataFrame, y: pd.Series):
    """
    AC-2: Shuffle Y and check if AUC converges to 0.45 ~ 0.55.
    """
    y_shuffled = y.sample(frac=1.0, random_state=None).values
    model = train_baseline_model(X, pd.Series(y_shuffled, index=X.index))
    probs = predict_baseline_crisis_prob(model, X)
    auc = roc_auc_score(y_shuffled, probs)
    return auc


def plot_ac3_reliability_diagram(y_true, y_prob, n_bins=5, save_path=None):
    """
    AC-3: Calibration Curve (Reliability Diagram).
    """
    prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=n_bins)

    plt.figure(figsize=(8, 6))
    plt.plot(prob_pred, prob_true, marker="o", linewidth=1, label="V_Baseline")
    plt.plot([0, 1], [0, 1], linestyle="--", label="Perfectly calibrated")
    plt.xlabel("Predicted Probability")
    plt.ylabel("Actual Frequency (Y=1)")
    plt.title("AC-3: Reliability Diagram (Calibration)")
    plt.legend()
    plt.grid(True)

    if save_path:
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()

    return prob_true, prob_pred
