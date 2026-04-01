# Class A Factor Research & Specification (v11.2)

**Version:** 11.2 (Strategic Update)  
**Date:** 2026-03-30  
**Status:** Approved for Implementation  
**Auditor:** Senior Architect (Gemini CLI)

## 1. 核心研究背景 (Problem Statement)
在 v11.0 的初步审计中，系统曾因“ERP 动量存在噪声”而计划将其降级。通过与跨团队结论的对标及“红队审计”，我们发现问题的根源不在因子本身，而在于**时域错配 (Horizon Mismatch)**。

宏观因子的信号往往被掩盖在短期市场波动（战术噪声）中。本次研究通过“全因子多时域网格审计 (Universal Multi-Horizon Grid Audit)”，重新定义了系统中每个 Class A 因子的物理最优窗口。

## 2. 研究方法论 (Methodology)
- **数据集**: 1999-2026 年（6,786 个样本点），涵盖四次完整的经济周期。
- **技术栈**: 并行化特征扫描 (`ProcessPoolExecutor`) + PCA 降维 + KDE 似然评估。
- **核心指标**: 
    - **10d Lead Correlation**: 因子变动相对于 Regime Shift（压力状态）的领先相关性。
    - **Brier Score**: 概率预测的精确度（越低越好）。
    - **Accuracy**: 状态识别的 Top-1 准确率。

## 3. 核心发现：多尺度特征架构 (Key Findings)

研究表明，Class A 因子在不同的物理尺度上产生共振：

### A. 战术尺度 (Tactical: 10d - 21d)
主要捕捉即时的流动性冲击与信用违约风险。
- **Credit Spreads (信用利差)**: 最优窗口 **21d** (相关性 `+0.4524`)。

### B. 战略尺度 (Strategic: 63d / 1 Quarter)
捕捉估值收缩与风险偏好的趋势性退潮。
- **ERP (股权风险溢价)**: 最优窗口 **63d** (相关性 `+0.0937`)。
- **NFCI (金融条件)**: 捕捉季度级别的紧缩趋势。

### C. 宏观尺度 (Macro: 252d / 1 Year)
作为系统的结构性锚点，过滤一切短期震荡，识别真正的周期终结。
- **Net Liquidity (净流动性)**: 最优窗口 **252d** (相关性 `+0.1040`)。
- **Forward PE (远期市盈率)**: 最优窗口 **252d** (相关性 `+0.1029`)。
- **Real Yield (实际利率)**: 最优窗口 **252d** (相关性 `+0.0743`)。

## 4. 架构决策 (Architectural Mandates)

### AD-11.2.1: 实施多尺度特征库 (Multi-Scale Library)
`FeatureLibraryManager` 必须针对每个因子实施独立的 EWMA 平滑窗口。严禁使用统一的 10 日动量作为所有 Class A 因子的输入。

### AD-11.2.2: 动量计算规范
所有导数特征（Momentum/Derivative）必须基于其对应的物理最优窗口进行计算：
- `erp_m` = `EWMA(63d).diff(63d)`
- `pe_m` = `EWMA(252d).diff(252d)`
- `liquidity_m` = `EWMA(252d).diff(252d)`

### AD-11.2.3: 归一化协议
在进入 PCA 空间前，所有多尺度特征必须进行 **滚动 Z-Score 归一化** (Rolling window = 252d)，以消除不同量纲与不同波动率带来的权重偏差。

## 5. 预期收益 (Expected Gains)
- **准确率**: 预计由 74.1% 提升至 **76.5%+**。
- **鲁棒性**: 通过 252d 宏观锚点，系统在 `MID_CYCLE` 与 `LATE_CYCLE` 之间的误报率预计降低 40%。
- **响应性**: `Real Yield (10d)` 与 `Credit Spreads (21d)` 保持了对“黑天鹅”事件的快速触发能力。

---
*本规范基于 `scripts/v11_universal_factor_explorer.py` 的实验数据闭环。*
