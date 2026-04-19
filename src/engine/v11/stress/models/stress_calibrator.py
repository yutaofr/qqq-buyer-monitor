from __future__ import annotations

import math
import warnings

import numpy as np

try:
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression
except Exception:  # pragma: no cover
    IsotonicRegression = None
    LogisticRegression = None


def _as_score_array(scores) -> np.ndarray:
    arr = np.asarray(scores, dtype=float).reshape(-1)
    arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(arr, 0.0, 1.0)


class StressCalibrator:
    """Configurable causal calibrator for raw stress scores."""

    def __init__(self, method: str = "platt"):
        self.method = str(method)
        self.model = None
        self.fit_metadata: dict[str, object] = {"fit_rows": 0, "method": self.method}

    def fit(self, scores, labels, sample_weight=None) -> StressCalibrator:
        x = _as_score_array(scores)
        y = np.asarray(labels, dtype=int).reshape(-1)
        if len(x) != len(y):
            raise ValueError("scores and labels must have the same length")
        if len(x) == 0:
            return self
        weights = None
        if sample_weight is not None:
            weights = np.asarray(sample_weight, dtype=float).reshape(-1)
            if len(weights) != len(x):
                raise ValueError("sample_weight must have the same length as scores")
            weights = np.nan_to_num(weights, nan=1.0, posinf=1.0, neginf=1.0)
            weights = np.clip(weights, 0.0, None)
        self.fit_metadata = {
            "fit_rows": int(len(x)),
            "method": self.method,
            "weighting": "sample_weight" if weights is not None else "uniform",
        }
        unique = set(int(v) for v in y)
        if len(unique) < 2:
            self.model = ("constant", float(next(iter(unique), 0)))
            return self
        if self.method in {"isotonic", "weighted_isotonic"} and IsotonicRegression is not None:
            self.model = IsotonicRegression(out_of_bounds="clip").fit(
                x,
                y,
                sample_weight=weights,
            )
        elif self.method == "identity":
            self.model = None
        elif LogisticRegression is not None:
            class_weight = "balanced" if self.method == "platt_balanced" else None
            lr = LogisticRegression(
                solver="lbfgs",
                random_state=17,
                max_iter=1000,
                class_weight=class_weight,
            )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                lr.fit(x.reshape(-1, 1), y, sample_weight=weights)
            self.model = lr
        else:
            self.model = ("empirical", float(y.mean()))
        return self

    def transform(self, scores) -> np.ndarray:
        x = _as_score_array(scores)
        if self.method == "identity" or self.model is None:
            return x
        if isinstance(self.model, tuple):
            kind, value = self.model
            if kind == "constant":
                return np.full_like(x, float(value), dtype=float)
            return np.clip(0.5 * x + 0.5 * float(value), 0.0, 1.0)
        if self.method in {"isotonic", "weighted_isotonic"}:
            return np.clip(np.asarray(self.model.predict(x), dtype=float), 0.0, 1.0)
        return np.clip(np.asarray(self.model.predict_proba(x.reshape(-1, 1))[:, 1], dtype=float), 0.0, 1.0)

    def transform_one(self, score: float) -> float:
        value = self.transform([score])[0]
        if not math.isfinite(float(value)):
            return 0.0
        return float(np.clip(value, 0.0, 1.0))
