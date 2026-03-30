"""v11 Conductor: The Dictatorial Exoskeleton Orchestrator.
Coordinates data scrubbing, cognitive inference, and hysteresis mapping.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from datetime import date

from src.engine.v11.signal.data_degradation_pipeline import DataDegradationPipeline, SignalDegradationOverrider
from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine
from src.engine.v11.core.kill_switch import DynamicZScoreKillSwitch
from src.engine.v11.signal.hysteresis_exposure_mapper import HysteresisExposureMapper
from src.engine.v11.core.feature_library import FeatureLibraryManager
from src.engine.v11.core.calibration_service import CalibrationService

class V11Conductor:
    def __init__(self):
        self.pipeline = DataDegradationPipeline()
        self.overrider = SignalDegradationOverrider()
        self.kill_switch = DynamicZScoreKillSwitch()
        self.mapper = HysteresisExposureMapper()
        self.library = FeatureLibraryManager()
        self.calibrator = CalibrationService()
        
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
        latest_raw = clean_df.iloc[-1]
        
        # 2. 更新特征库
        self.library.update_library(latest_raw)
        
        # 3. 计算标准化分位数
        standardized_df = self.library.get_standardized_features()
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
                current_spread=latest_raw["credit_spread_bps"]
            )
        else:
            # 数据缺失，回退到先验
            posteriors = self.base_priors.copy()
        
        # 6. 右侧解冻判定
        # 需要 VIX3M 序列计算 Z-Score
        ts_series = self.library.df["vix3m"] - self.library.df["vix"]
        vix_series = self.library.df["vix"]
        is_resurrected = self.kill_switch.evaluate_resurrection(
            is_blackout=(vix_series.iloc[-1] > 60),
            ts_series=ts_series,
            vix_1m=vix_series,
            current_idx=len(vix_series) - 1
        )
        
        # 7. 独裁信号映射
        raw_signal = self.mapper.get_signal(posteriors["BUST"], is_resurrected)
        self.mapper.tick_cooldown() # 更新结算锁
        
        # 8. 优雅降级覆写
        final_signal = self.overrider.enforce_degradation(raw_signal, quality_score)
        
        return {
            "date": latest_raw["observation_date"],
            "signal": final_signal,
            "probabilities": posteriors,
            "data_quality": quality_score,
            "resurrection_active": is_resurrected
        }
