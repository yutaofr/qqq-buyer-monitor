"""v11 Core: Feature Library Manager.
Maintains the 25-year historical dataset required for consistent EWMA ranking.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.engine.v11.core.adaptive_memory import ExogenousMemoryOperator


class FeatureLibraryManager:
    def __init__(self, storage_path: str = "data/v11_feature_library.csv", *, persist: bool = True):
        self.storage_path = Path(storage_path)
        self.persist = persist
        self.memory_engine = ExogenousMemoryOperator()
        self.df = self._load_library()

    def _load_library(self) -> pd.DataFrame:
        """
        加载特征库：优先从 Vercel Blob 同步最新数据，并与本地缓存合并。
        """
        local_df = pd.DataFrame()
        if self.storage_path.exists():
            local_df = pd.read_csv(self.storage_path)
            local_df["observation_date"] = pd.to_datetime(local_df["observation_date"])

        # Cloud Sync (Read-only pull from edge to ensure memory parity)
        import os
        import requests
        import io
        
        # We only attempt cloud pull in CI or if explicitly configured
        is_ci = os.environ.get("GITHUB_ACTIONS") == "true"
        blob_token = os.environ.get("VERCEL_BLOB_READ_WRITE_TOKEN")
        
        if is_ci and blob_token:
            try:
                # Use standard public URL for reading if possible, or authenticated API
                blob_url = "https://blob.vercel-storage.com/v11_feature_library.csv"
                headers = {"authorization": f"Bearer {blob_token}"}
                resp = requests.get(blob_url, headers=headers, timeout=10)
                
                if resp.status_code == 200:
                    cloud_df = pd.read_csv(io.BytesIO(resp.content))
                    cloud_df["observation_date"] = pd.to_datetime(cloud_df["observation_date"])
                    
                    # Merge and deduplicate
                    if local_df.empty:
                        local_df = cloud_df
                    else:
                        local_df = pd.concat([local_df, cloud_df]).drop_duplicates(subset=["observation_date"])
                    
                    print(f"DEBUG: V11 Feature Library synced from cloud (Total rows: {len(local_df)})")
            except Exception as e:
                # Silent fallback to local data to prevent pipeline halts
                print(f"WARNING: V11 Cloud Sync failed, falling back to local: {e}")

        if not local_df.empty:
            return local_df.sort_values("observation_date").reset_index(drop=True)
        return pd.DataFrame()

    def update_library(self, new_row: pd.Series):
        """追加 T+0 数据并持久化"""
        new_row_df = pd.DataFrame([new_row])
        new_row_df["observation_date"] = pd.to_datetime(new_row_df["observation_date"])
        self.df = pd.concat([self.df, new_row_df]).drop_duplicates(subset=["observation_date"])
        self.df = self.df.sort_values("observation_date").reset_index(drop=True)
        if self.persist:
            self.df.to_csv(self.storage_path, index=False)

    def get_standardized_features(self, lookback_window: int = 252*20) -> pd.DataFrame:
        """
        计算所有特征的自适应 EWMA 分位数排名。
        """
        if self.df.empty:
            return pd.DataFrame()

        df = self._prepare_feature_frame()

        # 计算外生半衰期
        lambdas = self.memory_engine.compute_adaptive_lambda(df["credit_spread_bps"])

        features = [
            "spread_stress",
            "liquidity_stress",
            "vix_stress",
            "drawdown_stress",
            "breadth_stress",
            "term_structure_stress",
            "erp_stress",
        ]
        standardized = pd.DataFrame(index=df.index)
        standardized["observation_date"] = df["observation_date"]

        for feat in features:
            if feat in df.columns:
                standardized[f"{feat}_pct"] = self.memory_engine.get_weighted_rank(
                    df[feat], lambdas, window=lookback_window
                )
                rolling_mean = standardized[f"{feat}_pct"].rolling(60, min_periods=10).mean()
                rolling_std = standardized[f"{feat}_pct"].rolling(60, min_periods=10).std().replace(0, pd.NA)
                standardized[f"{feat}_momentum"] = (
                    (standardized[f"{feat}_pct"] - rolling_mean) / rolling_std
                ).fillna(0.0)

        return standardized

    def _prepare_feature_frame(self) -> pd.DataFrame:
        df = self.df.copy().sort_values("observation_date").reset_index(drop=True)
        df["credit_spread_bps"] = pd.to_numeric(df.get("credit_spread_bps"), errors="coerce")
        df["spread_stress"] = df["credit_spread_bps"]

        liquidity = (
            df.get("liquidity_roc_pct_4w")
            if "liquidity_roc_pct_4w" in df.columns
            else df.get("liquidity_roc")
        )
        if liquidity is not None:
            liquidity = pd.to_numeric(liquidity, errors="coerce")
            df["liquidity_stress"] = (-liquidity).clip(lower=0.0)

        if "vix" in df.columns:
            df["vix_stress"] = pd.to_numeric(df["vix"], errors="coerce")

        if "drawdown_pct" in df.columns:
            drawdown = pd.to_numeric(df["drawdown_pct"], errors="coerce").fillna(0.0)
            df["drawdown_stress"] = drawdown.abs()

        if "breadth_proxy" in df.columns:
            breadth = pd.to_numeric(df["breadth_proxy"], errors="coerce")
            df["breadth_stress"] = (1.0 - breadth).clip(lower=0.0)

        if "vix" in df.columns and "vix3m" in df.columns:
            vix = pd.to_numeric(df["vix"], errors="coerce")
            vix3m = pd.to_numeric(df["vix3m"], errors="coerce").replace(0, pd.NA)
            df["term_structure_stress"] = (vix / vix3m).clip(lower=0.0)

        # New Features for Audit
        if "forward_pe" in df.columns and "real_yield_10y_pct" in df.columns:
            pe = pd.to_numeric(df["forward_pe"], errors="coerce")
            yield10y = pd.to_numeric(df["real_yield_10y_pct"], errors="coerce")
            erp = (100.0 / pe) - yield10y
            df["erp_stress"] = (-erp).fillna(0.0) # Lower ERP = Higher Stress

        if "funding_stress_flag" in df.columns:
            df["funding_stress"] = pd.to_numeric(df["funding_stress_flag"], errors="coerce").fillna(0.0)

        return df
