# v11.0 Design and Execution Plan: Probabilistic & Permanent Dual-Track Architecture

## 1. 核心愿景 (Vision)
v11.0 "Entropy" 旨在构建一个基于统计严谨性的永久双轨决策引擎。核心目标是剔除前向泄漏，通过**正交信号组**与**规则+似然混合模型**，实现对极端回撤的理性猎杀。

---

## 2. 贝叶斯推理与标定协议 (Bayesian Orthogonality)

### 2.1 信号正交化 (De-coupling Labels and Evidence)
*   **标定信号 (Regime Labels)**: **仅限信贷/流动性维度**。
    *   `Spread_pct`, `Spread_Acceleration`, `Liquidity_ROC`.
*   **推理信号 (Likelihood Evidence)**: **仅限市场/价格维度**。
    *   `VIX_pct`, `Market_Breadth`, `Drawdown`, `Price_Momentum`.
*   **输入规范**: 推理信号在进入 PCA 前必须经过 20 年滚动分位数标准化。

### 2.2 Regime 标定优先级与方法论 (Revised)
1.  **BUST (KDE)**: `Spread_pct >= 0.90`. (优先级 1)
2.  **CAPITULATION (Rule-based)**: `Spread_pct >= 0.80` 且 `Spread_Acceleration <= 0` 且 `Liquidity_ROC > 0`.
    *   *注: 鉴于样本稀疏 (N=20)，此状态由规则强制触发，KDE 仅做微调。*
3.  **RECOVERY (KDE)**: `Spread_20d_delta < -30bps` 且 `Liquidity_ROC > 0`.
4.  **MID_CYCLE (KDE)**: 默认状态。
5.  **LATE_CYCLE (Constraint Overlay)**: `ERP_pct <= 0.15`.
    *   *决策: 不作为独立分类器，作为全局敞口上限 (0.8x) 的硬拦截器。*

---

## 3. 永久双轨与 Blood-Chip 通道 (Dual-Track & Blood-Chip)

### 3.1 桶 B 规模公式 (The Multiplicative Law)
$$Size_B = New\_Cash \times [P(CAPITULATION) + P(RECOVERY)] \times Opportunity\_Score \times 0.5\_Kelly\_Cap$$
*   **严禁使用加法拼接仓位。**
*   **Opportunity_Score**: 基于 VIX 峰值与 Drawdown 深度，作为入场激进度的乘数。

### 3.2 Blood-Chip (DEPLOY_FAST) 逻辑
当 `Regime == BUST` 但 `Spread_Acceleration <= 0` 且 `Liquidity_ROC > +0.5%` 时，`RiskController` 开启 `DEPLOY_FAST` 通道：
*   允许新现金以 100% 权重直接购买 QQQ 现货。
*   无视 BUST 状态下的常规 0.5x 敞口限制。

---

## 4. POC 阶段 3R (Revised Alpha Audit)

在进入正式实现前，必须执行 **3R 轮模拟**，验证修复后的架构性能：
*   **目标**: 使用上述**乘法公式**与 **DEPLOY_FAST 通道**，重新审计 2020 年和 2022 年场景。
*   **验收**: 2020 年的入场成本必须显著优于 (或至少对齐) VWAP，证明 Blood-Chip 逻辑的有效性。

---

## 5. 验收标准 (Final Metrics)
1.  **Alpha 质量**: 桶 B 在 3R 模拟中必须展现出正向的风险调整后增益。
2.  **Brier 分解**: $P(BUST)$ 的 Brier Score 必须显著优于历史频率模型。
3.  **架构纯净度**: 标定与推理信号物理隔离，LATE_CYCLE 硬拦截器逻辑独立。

---
*Architect Review Note: v11 architecture is now logically closed with the inclusion of Blood-Chip logic and Multiplicative Sizing. POC Phase 3R is mandatory before any production code is written.*
