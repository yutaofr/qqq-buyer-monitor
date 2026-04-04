import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import TimeSeriesSplit


def rolling_zscore(
    values: pd.DataFrame | pd.Series, window: int = 750, min_periods: int = 100, clip: float = 8.0
) -> pd.DataFrame | pd.Series:
    rolling = values.rolling(window, min_periods=min_periods)
    z = (values - rolling.mean()) / rolling.std().replace(0.0, np.nan)
    return z.replace([np.inf, -np.inf], np.nan).clip(lower=-clip, upper=clip)


def _sanitize_feature_frame(X: pd.DataFrame, clip: float = 8.0) -> pd.DataFrame:
    return (
        X.apply(pd.to_numeric, errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .clip(lower=-clip, upper=clip)
    )


def _standardize(X: pd.DataFrame, mean: pd.Series, scale: pd.Series) -> pd.DataFrame:
    aligned = _sanitize_feature_frame(X).reindex(columns=mean.index)
    filled = aligned.fillna(mean)
    return (filled - mean) / scale


def _valid_time_splits(y: pd.Series, n_splits: int = 5, gap: int = 20) -> list[tuple[np.ndarray, np.ndarray]]:
    splits: list[tuple[np.ndarray, np.ndarray]] = []
    for train_idx, test_idx in TimeSeriesSplit(n_splits=n_splits, gap=gap).split(y):
        y_train = y.iloc[train_idx]
        y_test = y.iloc[test_idx]
        if y_train.nunique() > 1 and y_test.nunique() > 1:
            splits.append((train_idx, test_idx))
    return splits


def _predict_scores(model, X: pd.DataFrame) -> np.ndarray:
    return np.einsum("ij,j->i", X.to_numpy(dtype=float), model.coef_[0]) + float(model.intercept_[0])


def _predict_probs(model, X: pd.DataFrame) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(_predict_scores(model, X), -30.0, 30.0)))


def _select_regularization_c(
    X: pd.DataFrame, y: pd.Series, splits: list[tuple[np.ndarray, np.ndarray]]
) -> float:
    candidate_cs = np.array([1e-4, 1e-3, 1e-2, 1e-1], dtype=float)
    if len(splits) < 2:
        return 1e-2

    best_c = 1e-2
    best_loss = float("inf")
    for c in candidate_cs:
        losses: list[float] = []
        for train_idx, test_idx in splits:
            model = LogisticRegression(C=float(c), solver="liblinear", max_iter=2000)
            model.fit(X.iloc[train_idx], y.iloc[train_idx])
            probs = _predict_probs(model, X.iloc[test_idx])
            losses.append(float(brier_score_loss(y.iloc[test_idx], probs)))
        mean_loss = float(np.mean(losses))
        if mean_loss < best_loss:
            best_loss = mean_loss
            best_c = float(c)
    return best_c


def calculate_composites(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError("Empty DataFrame provided.")
    z = rolling_zscore(df)
    out = pd.DataFrame(index=df.index)
    if {"IPMAN", "growth_margin"}.issubset(z.columns):
        out["growth_composite"] = z[["IPMAN", "growth_margin"]].mean(axis=1)
    if {"M2REAL", "T10Y2Y"}.issubset(z.columns):
        out["liquidity_composite"] = z[["M2REAL", "T10Y2Y"]].mean(axis=1)
    if {"BAMLH0A0HYM2", "VIXCLS"}.issubset(z.columns):
        out["stress_composite"] = z[["BAMLH0A0HYM2", "VIXCLS"]].max(axis=1)
    return out.dropna()


def train_baseline_model(X: pd.DataFrame, y: pd.Series):
    X_clean = _sanitize_feature_frame(X).dropna()
    train_idx = X_clean.index.intersection(y.dropna().index)
    X_clean = X_clean.loc[train_idx]
    y_clean = y.loc[train_idx].astype(int)
    mean = X_clean.mean()
    scale = X_clean.std(ddof=0).replace(0.0, 1.0).fillna(1.0)
    X_scaled = _standardize(X_clean, mean, scale)
    splits = _valid_time_splits(y_clean)
    best_c = _select_regularization_c(X_scaled, y_clean, splits)
    model = LogisticRegression(C=best_c, solver="liblinear", max_iter=2000)
    model.fit(X_scaled, y_clean)
    model.C_ = np.atleast_1d(best_c)
    model._feature_mean = mean
    model._feature_scale = scale
    return model


def predict_baseline_crisis_prob(model, X: pd.DataFrame) -> pd.Series:
    mean = getattr(model, "_feature_mean", None)
    scale = getattr(model, "_feature_scale", None)
    X_eval = _standardize(X, mean, scale) if mean is not None and scale is not None else X
    probs = _predict_probs(model, X_eval)
    return pd.Series(probs, index=X_eval.index)
