"""v11 Conductor: The Dictatorial Exoskeleton Orchestrator.
Coordinates data scrubbing, cognitive inference, and hysteresis mapping.
"""
from __future__ import annotations

import pandas as pd

from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine
from src.engine.v11.core.calibration_service import CalibrationService
from src.engine.v11.core.feature_library import FeatureLibraryManager
from src.engine.v11.core.kill_switch import DynamicZScoreKillSwitch
from src.engine.v11.core.position_sizer import ProbabilisticPositionSizer
from src.engine.v11.signal.behavioral_guard import BehavioralGuard
from src.engine.v11.signal.data_degradation_pipeline import (
    DataDegradationPipeline,
    SignalDegradationOverrider,
)


class V11Conductor:
    def __init__(self, *, storage_path: str = "data/v11_feature_library.csv", persist_library: bool = True):
        self.pipeline = DataDegradationPipeline()
        self.overrider = SignalDegradationOverrider()
        self.kill_switch = DynamicZScoreKillSwitch()
        self.execution_guard = BehavioralGuard()
        self.library = FeatureLibraryManager(storage_path=storage_path, persist=persist_library)
        self.calibrator = CalibrationService()
        self.position_sizer = ProbabilisticPositionSizer()

        # 初始先验
        self.base_priors = {
            "MID_CYCLE": 0.85,
            "BUST": 0.05,
            "CAPITULATION": 0.02,
            "RECOVERY": 0.05,
            "LATE_CYCLE": 0.03
        }

    def daily_run(self, raw_t0_data: pd.DataFrame) -> dict:
        """
        每日执行流水线 (SOP 落地)。
        """
        # 1. 数据防毒面具
        clean_df, quality_score = self.pipeline.scrub_and_score(raw_t0_data)
        latest_row = clean_df.iloc[-1]

        # 2. 更新特征库
        self.library.update_library(latest_row)

        # 3. 计算标准化分位数
        standardized_df = self.library.get_standardized_features()
        if standardized_df.empty:
            standardized_df = pd.DataFrame([{"observation_date": latest_row["observation_date"]}])
        latest_std = standardized_df.iloc[-1]

        # 4. 校准与推断
        self.calibrator.calibrate(standardized_df, self.library.df)
        pca_coords = self.calibrator.get_inference_packet(latest_std)

        # 5. 贝叶斯核心推断
        inference_engine = BayesianInferenceEngine(
            kde_models=self.calibrator.kde_models,
            base_priors=self.base_priors
        )

        if pca_coords is not None:
            posteriors = inference_engine.infer_posterior(
                pca_coords,
                current_spread=float(latest_row.get("credit_spread_bps", 400.0))
            )
        else:
            # 数据缺失，回退到先验
            posteriors = self.base_priors.copy()

        # 6. 右侧解冻判定
        # 需要 VIX3M 序列计算 Z-Score
        if {"vix3m", "vix"}.issubset(self.library.df.columns):
            ts_series = self.library.df["vix3m"] - self.library.df["vix"]
            vix_series = self.library.df["vix"]
            is_resurrected = self.kill_switch.evaluate_resurrection(
                is_blackout=(vix_series.iloc[-1] > 60),
                ts_series=ts_series,
                vix_1m=vix_series,
                current_idx=len(vix_series) - 1
            )
        else:
            is_resurrected = False

        # 7. 概率输出 -> 行为约束
        sizing = self.position_sizer.size_positions(
            posteriors=posteriors,
            reference_capital=max(1.0, float(latest_row.get("reference_capital", 100_000.0))),
            current_nav=max(1.0, float(latest_row.get("current_nav", 100_000.0))),
            previous_target_beta=self.execution_guard.last_target_beta,
        )
        execution_signal = self.execution_guard.apply(
            sizing,
            kill_switch_active=is_resurrected,
        ).to_dict()
        final_signal = self.overrider.enforce_degradation(execution_signal, quality_score)
        if final_signal.get("target_bucket") and final_signal["target_bucket"] != execution_signal["target_bucket"]:
            self.execution_guard.sync_to_bucket(final_signal["target_bucket"])

        # 8. 采集展示特征 (UI mapping)
        feature_values = {
            "credit_spread": float(latest_row.get("credit_spread_bps", 0.0)),
            "erp": float(latest_row.get("erp", 0.0)) if latest_row.get("erp") is not None else None,
            "net_liquidity": float(latest_row.get("net_liquidity", 0.0)) if latest_row.get("net_liquidity") is not None else None,
            "liquidity_roc": float(latest_row.get("liquidity_roc_pct_4w", 0.0)),
            "vix": float(latest_row.get("vix", 0.0)),
            "fear_greed": int(latest_row.get("fear_greed", 50)),
        }
        
        # 计算战术压力得分 (基于标准化动量的绝对值总和作为 UI 代理)
        momentum_cols = [c for k, c in latest_std.items() if "momentum" in str(k)]
        if momentum_cols:
            feature_values["tactical_stress_score"] = int(sum(abs(v) for v in momentum_cols) * 10)
        else:
            feature_values["tactical_stress_score"] = 0

        return {
            "date": latest_row["observation_date"],
            "signal": final_signal,
            "probabilities": posteriors,
            "entropy": sizing.entropy,
            "target_beta": sizing.target_beta,
            "raw_target_beta": sizing.raw_target_beta,
            "target_allocation": {
                "qqq_dollars": sizing.qqq_dollars,
                "qld_notional_dollars": sizing.qld_notional_dollars,
                "cash_dollars": sizing.cash_dollars,
            },
            "data_quality": quality_score,
            "quality_audit": self.pipeline.last_audit,
            "resurrection_active": is_resurrected,
            "feature_values": feature_values,
        }
