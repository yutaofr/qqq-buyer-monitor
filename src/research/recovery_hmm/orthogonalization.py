"""Rolling PCA orthogonalization for the recovery HMM research track."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.decomposition import PCA


@dataclass(frozen=True)
class RollingPcaResult:
    transformed: pd.DataFrame
    component_count: int
    explained_variance_ratio_sum: float


@dataclass(frozen=True)
class FittedPcaProjection:
    means: pd.Series
    stds: pd.Series
    components: list[str]
    pca: PCA
    explained_variance_ratio_sum: float

    def transform(self, feature_frame: pd.DataFrame) -> pd.DataFrame:
        numeric = feature_frame.loc[:, self.means.index].apply(pd.to_numeric, errors="coerce").dropna()
        standardized = (numeric - self.means) / self.stds
        transformed = self.pca.transform(standardized)[:, : len(self.components)]
        return pd.DataFrame(transformed, index=standardized.index, columns=self.components)


def fit_transform_rolling_pca(
    feature_frame: pd.DataFrame,
    *,
    window: int = 504,
    variance_threshold: float = 0.85,
) -> RollingPcaResult:
    if len(feature_frame) < window:
        raise ValueError("Feature frame is shorter than the requested PCA window.")

    latest_window = feature_frame.iloc[-window:].apply(pd.to_numeric, errors="coerce").dropna()
    means = latest_window.mean()
    stds = latest_window.std().replace(0.0, 1.0).fillna(1.0)
    standardized_window = (latest_window - means) / stds

    pca = PCA()
    pca.fit(standardized_window)
    cumulative = pd.Series(pca.explained_variance_ratio_).cumsum()
    component_count = int((cumulative < variance_threshold).sum() + 1)
    explained_variance_ratio_sum = float(cumulative.iloc[component_count - 1])

    full_frame = feature_frame.iloc[window - 1 :].apply(pd.to_numeric, errors="coerce").dropna()
    standardized_full = (full_frame - means) / stds
    transformed = pca.transform(standardized_full)[:, :component_count]
    transformed_frame = pd.DataFrame(
        transformed,
        index=standardized_full.index,
        columns=[f"PC{i}" for i in range(1, component_count + 1)],
    )
    return RollingPcaResult(
        transformed=transformed_frame,
        component_count=component_count,
        explained_variance_ratio_sum=explained_variance_ratio_sum,
    )


def fit_pca_projection(
    feature_frame: pd.DataFrame,
    *,
    variance_threshold: float = 0.85,
) -> FittedPcaProjection:
    numeric = feature_frame.apply(pd.to_numeric, errors="coerce").dropna()
    means = numeric.mean()
    stds = numeric.std().replace(0.0, 1.0).fillna(1.0)
    standardized = (numeric - means) / stds

    pca = PCA()
    pca.fit(standardized)
    cumulative = pd.Series(pca.explained_variance_ratio_).cumsum()
    component_count = int((cumulative < variance_threshold).sum() + 1)
    components = [f"PC{i}" for i in range(1, component_count + 1)]
    return FittedPcaProjection(
        means=means,
        stds=stds,
        components=components,
        pca=pca,
        explained_variance_ratio_sum=float(cumulative.iloc[component_count - 1]),
    )
