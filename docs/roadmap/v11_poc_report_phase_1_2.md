# Archived Research Note

> 归档状态: Historical research only
> 说明: 该阶段性 POC 报告保留用于追溯，不代表当前生产结论。

# v11 POC Phase 1 & 2: Findings and Observations Report

## 1. 阶段 1：特征库构建与正交标定 (Findings)

### 1.1 数据分布与稀疏性
*   **样本总量**: 1995 - 2026 (7362 原始行，6465 有效行)。
*   **Regime 频率分布**:
    *   `MID_CYCLE`: 5350 (82.7%) — 系统的基准背景。
    *   `BUST`: 766 (11.8%) — 样本量充足，模型表现稳定。
    *   `RECOVERY`: 318 (4.9%) — 具有明显的滞后特征。
    *   `CAPITULATION`: 20 (0.3%) — **极度稀疏**，主要集中在 2000, 2008, 2020。
    *   `LATE_CYCLE`: 11 (0.17%) — 样本量不足以支持独立的 KDE 建模，建议并入广义风险区。

### 1.2 PCA-KDE 表现
*   **方差解释率**: 前两个主成分 (PCA1, PCA2) 解释了约 93.6% 的价格信号变异。
*   **似然分离度**: `BUST` 和 `MID_CYCLE` 在 PCA 空间中展现出明显的拓扑分离，证明价格行为（VIX/DD/Momentum）在不同信贷环境下具有显著差异。

---

## 2. 阶段 2：Purged Walk-Forward 审计 (Findings)

### 2.1 预测增益 (Brier Score Gain)
审计区间：2017-06-05 至 2026-03-27 (2187 样本)。

| Regime | v11 Brier | Baseline | **Gain (%)** | 结论 |
| :--- | :--- | :--- | :--- | :--- |
| **BUST** | 0.00818 | 0.00942 | **+13.15%** | **显著成功**：模型能有效识别信贷危机。 |
| **MID_CYCLE** | 0.09860 | 0.09489 | -3.91% | 平稳期存在过度拟合噪音。 |
| **RECOVERY** | 0.09005 | 0.08521 | -5.68% | 状态切换点存在识别滞后。 |
| **CAPITULATION** | 0.00516 | 0.00500 | -3.04% | 样本过少，预测优势尚未体现。 |

### 2.2 架构师观察 (Architectural Observations)
1.  **正交性验证**: 标定信号（信贷）与推理信号（价格）的背离在 2022 年表现尤为明显。信贷利差在 2022 年初已进入 `BUST` 概率区，但价格信号直到 2022 年中才确认恐慌，这证明了 **贝叶斯先验** 在预警中的核心价值。
2.  **禁运期效应**: Regime 感知型 Embargo 成功切断了 `BUST` 期间的长程自相关，审计结果具备高度的实战参考价值。
3.  **数值警告**: 在 PCA 计算中观察到由于极端分位数导致的数值不稳定，生产级实现需引入微小扰动（Jitter）或 Robust Scaling。

---
*Status: Phase 1 & 2 Approved. Moving to Phase 3: Incremental Alpha Simulation.*
