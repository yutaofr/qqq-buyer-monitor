"""v11 Core: Calibration Service.
Handles PCA dimensionality reduction and KDE likelihood model training.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.neighbors import KernelDensity
from sklearn.preprocessing import StandardScaler


class CalibrationService:
    def __init__(self, n_components: int = 2):
        self.pca = PCA(n_components=n_components)
        self.scaler = StandardScaler()
        self.kde_models = {}
        self.feature_cols: list[str] = []
        self.is_fitted = False

    def calibrate(
        self,
        standardized_df: pd.DataFrame,
        labeled_df: pd.DataFrame,
        feature_cols: list[str] | None = None,
    ):
        """
        根据标定标签训练 KDE 模型。
        """
        if "regime" not in labeled_df.columns:
            self.is_fitted = False
            return

        if feature_cols is None:
            # Include both Level (_pct) and Momentum (_momentum)
            # This follows Howard Marks' advice: "Not just level, but direction/derivative"
            feature_cols = sorted(
                c for c in standardized_df.columns if c.endswith("_pct") or c.endswith("_momentum")
            )

        self.feature_cols = feature_cols

        # 1. 对齐数据
        df = pd.merge(
            standardized_df, labeled_df[["observation_date", "regime"]], on="observation_date"
        )

        # 强制删除 NaN 样本，防止 PCA 崩溃
        df_clean = df.dropna(subset=feature_cols)
        if (
            df_clean.empty
            or len(feature_cols) < self.pca.n_components
            or len(df_clean) < self.pca.n_components
        ):
            self.is_fitted = False
            return

        X = np.nan_to_num(
            df_clean[feature_cols].values.astype(float), nan=0.0, posinf=1.0, neginf=0.0
        )
        X = np.clip(X, 0.0, 1.0)

        # 2. PCA 降维
        X_scaled = self.scaler.fit_transform(X)
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            X_pca = self.pca.fit_transform(X_scaled)

        # 3. 为每个 Regime 训练 KDE
        self.kde_models = {}
        for r in df_clean["regime"].unique():
            r_data = X_pca[df_clean["regime"] == r]
            if len(r_data) < 10:
                continue

            kde = KernelDensity(bandwidth=0.1, kernel="gaussian")
            kde.fit(r_data)
            self.kde_models[r] = kde
        self.is_fitted = bool(self.kde_models)

    def get_inference_packet(self, latest_row_standardized: pd.Series) -> np.ndarray | None:
        """转换最新的 T+0 特征为 PCA 坐标"""
        if not self.is_fitted or not self.feature_cols:
            return None
        feature_cols = self.feature_cols
        # 强制转换为 float 以支持 isnan 检查
        vals = latest_row_standardized[feature_cols].values.astype(float)
        if np.isnan(vals).any():
            return None
        vals = np.clip(vals.reshape(1, -1), 0.0, 1.0)
        scaled = self.scaler.transform(vals)
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            return self.pca.transform(scaled)[0]
