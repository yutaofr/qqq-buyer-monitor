"""v11 Core: Bayesian Inference Engine.
The heart of the 'Entropy' architecture. 
Strictly NO hard-coded thresholds (e.g., 800bps). 
Uses continuous Sigmoid tension for prior shifting.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class BayesianInferenceEngine:
    """
    接收 PCA 降维后的战术证据与宏观基准，输出各 Regime 的后验概率。
    强制使用连续的 Sigmoid 函数处理先验漂移，绝无阶跃函数 (IF-ELSE)。
    """
    def __init__(self, 
                 kde_models: Dict[str, Any], 
                 base_priors: Dict[str, float],
                 sigmoid_alpha: float = 0.05, 
                 spread_baseline: float = 400.0):
        """
        Args:
            kde_models: 预训练的各 Regime 的 KDE 核密度估计器集合。
            base_priors: 历史基础先验概率（如 MID_CYCLE: 0.8, BUST: 0.1）。
            sigmoid_alpha: Sigmoid 曲线的陡峭度（张力系数）。
            spread_baseline: 正常信贷环境的基准中枢（非触发阈值，仅为中心点）。
        """
        self.kde_models = kde_models
        self.base_priors = base_priors
        self.alpha = sigmoid_alpha
        self.baseline = spread_baseline
        self.regimes = ["MID_CYCLE", "BUST", "CAPITULATION", "RECOVERY", "LATE_CYCLE"]
        
    def _compute_prior_shift(self, current_spread: float) -> float:
        """
        核心物理算子：使用 Sigmoid 函数将信贷绝对压力连续映射为先验漂移量。
        公式: Delta_Prior = max(0, 1 / (1 + exp(-alpha * (S - S_base))) - 0.5)
        这消灭了所有诸如 "if spread > 800" 的硬编码毒瘤。
        """
        # Sigmoid 映射到 (0, 1) 区间
        sigmoid_val = 1.0 / (1.0 + np.exp(-self.alpha * (current_spread - self.baseline)))
        # 我们只在信贷恶化时施加正向推力（即 sigmoid > 0.5 的右半边）
        shift = max(0.0, sigmoid_val - 0.5) 
        return shift

    def infer_posterior(self, pca_evidence: np.ndarray, current_spread: float) -> Dict[str, float]:
        """
        基于当前 PCA 坐标与绝对信贷压力，计算严格的贝叶斯后验概率。
        """
        posteriors = {}
        total_likelihood = 0.0
        
        # 1. 计算连续先验漂移 (The Continuous Tension)
        delta_prior = self._compute_prior_shift(current_spread)
        
        # 动态调整先验（从安全状态抽取概率补偿给极值状态）
        dynamic_priors = self.base_priors.copy()
        
        # 危机状态吸收漂移概率
        crisis_boost = delta_prior * 0.5
        dynamic_priors["BUST"] += crisis_boost
        dynamic_priors["CAPITULATION"] += crisis_boost
        
        # 平稳状态释放概率（保证和为 1）
        dynamic_priors["MID_CYCLE"] -= (crisis_boost * 2)
        dynamic_priors["MID_CYCLE"] = max(0.001, dynamic_priors["MID_CYCLE"]) # Laplacian floor
        
        # 重新归一化先验
        prior_sum = sum(dynamic_priors.values())
        dynamic_priors = {k: v / prior_sum for k, v in dynamic_priors.items()}

        # 2. 计算似然与后验
        for regime in self.regimes:
            if regime in self.kde_models:
                # KDE 返回对数似然，需转回正常概率密度
                log_lh = self.kde_models[regime].score_samples([pca_evidence])[0]
                likelihood = np.exp(log_lh)
            else:
                likelihood = 1e-9 # 惩罚无模型的极稀疏状态

            # P(Posterior) = Likelihood * Prior
            posterior = likelihood * dynamic_priors[regime]
            posteriors[regime] = posterior
            total_likelihood += posterior
            
        # 3. 后验归一化
        if total_likelihood > 0:
            for r in self.regimes:
                posteriors[r] /= total_likelihood
        else:
            # 极度黑天鹅（所有 KDE 都无法解释当前坐标），退守动态先验
            logger.warning("PCA coordinates strictly out-of-distribution. Reverting to dynamic priors.")
            posteriors = dynamic_priors.copy()
            
        return posteriors
