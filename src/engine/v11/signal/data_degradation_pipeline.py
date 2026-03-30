"""v11 Signal: Data Degradation & Robustness Pipeline.
Defends the dictatorial state machine against NaN, outliers, and API ghost prints.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class DataDegradationPipeline:
    """
    v11 数据防毒面具。执行“优雅降级”。
    """
    def __init__(self, max_forward_fill: int = 1):
        self.max_fill = max_forward_fill
        self.last_audit: dict[str, object] = {
            "anomalies": [],
            "proxy_fields": [],
            "critical_cols": [],
        }

    def scrub_and_score(self, raw_df: pd.DataFrame) -> tuple[pd.DataFrame, float]:
        """
        清洗原始数据并返回当日的质量分 [0.0 - 1.0]。
        """
        df = raw_df.copy()
        anomalies: set[str] = set()
        proxy_fields: set[str] = set()

        # 1. 物理常识校验 (Sanity Checks)
        if 'vix' in df.columns:
            # 斩杀幽灵报价
            mask = (df['vix'] < 9.0) | (df['vix'] > 150.0)
            if bool(mask.iloc[-1]):
                anomalies.add("vix")
            df.loc[mask, 'vix'] = np.nan

        if 'vix3m' in df.columns and 'vix' in df.columns:
            # 斩杀荒谬的期限结构错乱
            spread = df['vix3m'] - df['vix']
            mask = (spread > 50.0) | (spread < -80.0)
            if bool(mask.iloc[-1]):
                anomalies.update({"vix", "vix3m"})
            df.loc[mask, ['vix', 'vix3m']] = np.nan

        # 2. 尖刺清洗 (Spike Removal: 偏离 5 日中位数 30%)
        # For POC/simplicity, apply to VIX.
        if 'vix' in df.columns:
            rolling_median = df['vix'].rolling(window=5, min_periods=1).median()
            deviation = np.abs(df['vix'] - rolling_median) / rolling_median
            mask = deviation > 0.30
            if bool(mask.iloc[-1]):
                anomalies.add("vix")
            df.loc[mask, 'vix'] = np.nan

        # 3. 影子代理 (Shadow Proxy)
        # VIX3M 缺失 -> VIX * 0.9 (保守的 Backwardation 假设)
        if 'vix3m' in df.columns and 'vix' in df.columns:
            missing_vix3m = df['vix3m'].isna() & df['vix'].notna()
            if bool(missing_vix3m.iloc[-1]):
                proxy_fields.add("vix3m")
            df.loc[missing_vix3m, 'vix3m'] = df.loc[missing_vix3m, 'vix'] * 0.9

        # VIX 缺失 -> QQQ 20d Realized Volatility
        if 'vix' in df.columns and 'qqq_close' in df.columns:
            missing_vix = df['vix'].isna()
            rv_proxy = df['qqq_close'].pct_change().rolling(20).std() * np.sqrt(252) * 100
            if bool(missing_vix.iloc[-1]):
                proxy_fields.add("vix")
            df.loc[missing_vix, 'vix'] = rv_proxy.loc[missing_vix]

        # 4. 计算当前质量分 (必须使用原始的缺失情况)
        latest_row = raw_df.iloc[-1]
        critical_cols = [c for c in ['vix', 'vix3m', 'qqq_close', 'credit_spread_bps'] if c in raw_df.columns]

        if not critical_cols:
             return df, 0.0

        missing_count = latest_row[critical_cols].isna().sum()
        quality_score = 1.0 - (missing_count / len(critical_cols))
        quality_score -= len([c for c in anomalies if c in critical_cols]) / len(critical_cols)
        quality_score -= 0.5 * len([c for c in proxy_fields if c in critical_cols]) / len(critical_cols)

        # 5. 有限插值
        df_cleaned = df.ffill(limit=self.max_fill)

        # 彻底断绝校验
        if df_cleaned.iloc[-1][critical_cols].isna().any():
            quality_score = 0.0

        quality_score = max(0.0, min(1.0, float(quality_score)))
        self.last_audit = {
            "anomalies": sorted(anomalies),
            "proxy_fields": sorted(proxy_fields),
            "critical_cols": critical_cols,
            "quality_score": quality_score,
            "field_status": {
                field: {
                    "usable": field not in anomalies,
                    "anomaly_detected": field in anomalies,
                    "proxy_used": field in proxy_fields,
                }
                for field in critical_cols
            },
        }

        return df_cleaned, quality_score

class SignalDegradationOverrider:
    """
    根据数据质量强制阉割前端状态机的信号。
    """
    def __init__(self, leverage_ban_threshold: float = 0.8, blackout_threshold: float = 0.5):
        self.leverage_ban_threshold = leverage_ban_threshold
        self.blackout_threshold = blackout_threshold

    def enforce_degradation(self, original_signal: dict, quality_score: float) -> dict:
        degraded = original_signal.copy()
        current_exp = original_signal.get("target_exposure", original_signal.get("target_bucket", "CASH"))

        # Level 1: 物理断网
        if quality_score < self.blackout_threshold:
            if current_exp in ["QLD", "QQQ"]:
                degraded["target_exposure"] = "CASH"
                degraded["target_bucket"] = "CASH"
                degraded["action_required"] = True
                degraded["reason"] = "CRITICAL: DATA CORRUPTION. FORCED CASH."
            return degraded

        # Level 2: 剥夺杠杆权
        if quality_score < self.leverage_ban_threshold:
            if current_exp == "QLD":
                degraded["target_exposure"] = "QQQ"
                degraded["target_bucket"] = "QQQ"
                degraded["action_required"] = True
                degraded["reason"] = "WARNING: SENSOR DEGRADATION. LEVERAGE DISABLED."

        return degraded
