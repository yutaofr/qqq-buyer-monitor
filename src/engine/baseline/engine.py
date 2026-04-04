import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegressionCV
from sklearn.model_selection import TimeSeriesSplit


def calculate_composites(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate the 3 structural composites for V_Baseline."""
    if df.empty:
        raise ValueError("Empty DataFrame provided.")

    # We need: IPMAN, growth_margin (Growth); M2REAL, T10Y2Y (Liquidity); BAMLH0A0HYM2, VIXCLS (Stress)
    # Replaced StandardScaler with Point-in-Time Rolling Z-Score
    mean_roll = df.rolling(750, min_periods=100).mean()
    std_roll = df.rolling(750, min_periods=100).std()
    z_scores = (df - mean_roll) / std_roll

    composites = pd.DataFrame(index=df.index)

    # 2.1 Growth Composite (Arithmetic Mean)
    # 2.2 Liquidity Composite (Arithmetic Mean)
    # 2.3 Stress Composite (Max Retention - CRITICAL)

    # Growth: ISM/PMI proxy (IPMAN) + Corporate Margin (growth_margin)
    growth_cols = ["IPMAN", "growth_margin"]
    if all(c in z_scores.columns for c in growth_cols):
        composites["growth_composite"] = z_scores[growth_cols].mean(axis=1)

    # Liquidity: Real M2 (M2REAL) + Yield Curve (T10Y2Y)
    liq_cols = ["M2REAL", "T10Y2Y"]
    if all(c in z_scores.columns for c in liq_cols):
        composites["liquidity_composite"] = z_scores[liq_cols].mean(axis=1)

    # Stress: Credit Spread (BAMLH0A0HYM2) + VIX (VIXCLS)
    stress_cols = ["BAMLH0A0HYM2", "VIXCLS"]
    if all(c in z_scores.columns for c in stress_cols):
        # Stress uses Extreme Retention (Max)
        composites["stress_composite"] = z_scores[stress_cols].max(axis=1)

    return composites.dropna()


def train_baseline_model(X: pd.DataFrame, y: pd.Series):
    """
    Train Ridge Logistic Regression with Cross-Validation for C coefficient.
    X: [C_growth, C_liquidity, C_stress]
    y: Target Crisis Binary (Y=1 if MDD > 8% or VIX > 30 in T+1 to T+20)
    """
    # Ridge Logistic = L2 Penalty.
    # LogisticRegressionCV by default does L2 if penalty='l2'
    # Smaller Cs means stronger regularization.
    tscv = TimeSeriesSplit(n_splits=5, gap=20)
    model = LogisticRegressionCV(
        Cs=np.logspace(-4, 0, 10),
        cv=tscv,
        penalty="l2",
        scoring="neg_brier_score",  # Fixed metric name
        random_state=42,
    )
    model.fit(X, y)
    return model


def predict_baseline_crisis_prob(model, X: pd.DataFrame) -> pd.Series:
    """Output P(Crisis|X)."""
    # model.predict_proba returns [P(0), P(1)]
    return pd.Series(model.predict_proba(X)[:, 1], index=X.index)
