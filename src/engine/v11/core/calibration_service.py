"""v11 Core: Calibration Service.
Handles PCA dimensionality reduction and KDE likelihood model training.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.neighbors import KernelDensity
from sklearn.model_selection import GridSearchCV

class CalibrationService:
    def __init__(self, n_components: int = 2):
        self.pca = PCA(n_components=n_components)
        self.kde_models = {}

    def calibrate(self, standardized_df: pd.DataFrame, labeled_df: pd.DataFrame):
        """
        根据标定标签训练 KDE 模型。
        """
        # 1. 对齐数据
        df = pd.merge(standardized_df, labeled_df[["observation_date", "regime"]], on="observation_date")
        feature_cols = [c for c in df.columns if c.endswith("_pct")]
        
        # 强制删除 NaN 样本，防止 PCA 崩溃
        df_clean = df.dropna(subset=feature_cols)
        if df_clean.empty:
            return
            
        X = df_clean[feature_cols].values
        
        # 2. PCA 降维
        X_pca = self.pca.fit_transform(X)
        
        # 3. 为每个 Regime 训练 KDE
        for r in df_clean["regime"].unique():
            r_data = X_pca[df_clean["regime"] == r]
            if len(r_data) < 10:
                continue
            
            kde = KernelDensity(bandwidth=0.1, kernel='gaussian')
            kde.fit(r_data)
            self.kde_models[r] = kde
            
    def get_inference_packet(self, latest_row_standardized: pd.Series) -> np.ndarray | None:
        """转换最新的 T+0 特征为 PCA 坐标"""
        feature_cols = [c for c in latest_row_standardized.index if c.endswith("_pct")]
        # 强制转换为 float 以支持 isnan 检查
        vals = latest_row_standardized[feature_cols].values.astype(float)
        if np.isnan(vals).any():
            return None
        return self.pca.transform(vals.reshape(1, -1))[0]
