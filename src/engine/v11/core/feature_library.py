"""v11 Core: Feature Library Manager.
Maintains the 25-year historical dataset required for consistent EWMA ranking.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path
from src.engine.v11.core.adaptive_memory import ExogenousMemoryOperator

class FeatureLibraryManager:
    def __init__(self, storage_path: str = "data/v11_feature_library.csv"):
        self.storage_path = Path(storage_path)
        self.memory_engine = ExogenousMemoryOperator()
        self.df = self._load_library()

    def _load_library(self) -> pd.DataFrame:
        if self.storage_path.exists():
            df = pd.read_csv(self.storage_path)
            df["observation_date"] = pd.to_datetime(df["observation_date"])
            return df.sort_values("observation_date")
        return pd.DataFrame()

    def update_library(self, new_row: pd.Series):
        """追加 T+0 数据并持久化"""
        new_row_df = pd.DataFrame([new_row])
        new_row_df["observation_date"] = pd.to_datetime(new_row_df["observation_date"])
        self.df = pd.concat([self.df, new_row_df]).drop_duplicates(subset=["observation_date"])
        self.df = self.df.sort_values("observation_date")
        self.df.to_csv(self.storage_path, index=False)

    def get_standardized_features(self, lookback_window: int = 252*20) -> pd.DataFrame:
        """
        计算所有特征的自适应 EWMA 分位数排名。
        """
        # 计算外生半衰期
        lambdas = self.memory_engine.compute_adaptive_lambda(self.df["credit_spread_bps"])
        
        features = ["vix", "drawdown_pct", "breadth_proxy"]
        standardized = pd.DataFrame(index=self.df.index)
        standardized["observation_date"] = self.df["observation_date"]
        
        for feat in features:
            if feat in self.df.columns:
                # 使用 min_periods=1 确保即使只有一行也能返回排名
                standardized[f"{feat}_pct"] = self.memory_engine.get_weighted_rank(
                    self.df[feat], lambdas, window=lookback_window
                )
            
        return standardized
