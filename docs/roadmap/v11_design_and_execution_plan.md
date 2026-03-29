# v11.0 Design and Execution Plan: Probabilistic & Permanent Dual-Track Architecture

## 1. 核心愿景 (Vision)
v11.0 "Entropy" 旨在构建一个基于统计严谨性的永久双轨决策引擎。核心目标是剔除一切前向泄漏（Forward-Looking Bias），通过**信号正交化**与**核密度估计 (KDE)**，建立真实的概率预测优势。

---

## 2. 贝叶斯推理与正交标定协议 (Bayesian Orthogonality)

### 2.1 信号解耦 (De-coupling Labels and Evidence)
为了避免循环定义，系统在标定（训练标签）与推理（观测证据）上使用互不重叠的信号组：
*   **标定信号 (Regime Labels)**: **仅限信贷/流动性维度**。
    *   `Spread_pct`, `Spread_Acceleration`, `Liquidity_ROC`.
*   **推理信号 (Likelihood Evidence)**: **仅限市场/价格维度**。
    *   `VIX_pct`, `Market_Breadth`, `Drawdown`, `Price_Momentum`.

### 2.2 标定优先级协议 (Labeling Priority Protocol)
为防止信号重叠导致样本污染，历史样本点按以下**严格顺序**进行唯一标定：
1.  **BUST**: `Spread_pct >= 0.90`. (优先级最高)
2.  **CAPITULATION**: `Spread_pct >= 0.80` 且 `Spread_Acceleration <= 0` 且 `Liquidity_ROC > 0`.
3.  **LATE_CYCLE**: `ERP_pct <= 0.15` 且 `Spread_pct > 0.65`.
4.  **RECOVERY**: `Spread_20d_delta < -30bps` 且 `Liquidity_ROC > 0`.
5.  **MID_CYCLE**: 上述条件均不满足时的默认状态。

### 2.3 似然函数计算 (Likelihood via Percentile-PCA & KDE)
*   **标准化**: 所有推理信号在进入 PCA 前必须进行 **20年滚动分位数标准化**（Rank-order Transformation），将数值缩放至 [0, 1]。
*   **降维**: 对标准化后的向量进行 PCA 降维，提取反映信号排名结构的主成分。
*   **估计**: 使用 KDE 构建 $P(Price\_Rank\_Structure | Credit\_Regime)$。

---

## 3. 永久双轨与总风险监控 (Dual-Track & Risk Aggregator)

### 3.1 决策隔离与桶 B 规模 (Isolation & Sizing)
*   **决策解耦**: 桶 A (Legacy) 与 桶 B (Active) 逻辑完全隔离。
*   **桶 B 规模公式**: 
    $$Size_B = New\_Cash \times P(CAPITULATION) \times Opportunity\_Score \times 0.5\_Kelly\_Cap$$
    *   该公式确保回测的风险调整后 Alpha 在实盘中具有严格的执行一致性。

### 3.2 组合风险汇总层 (Consolidated Risk Layer)
*   **监控指标**: `Combined_VaR(95%, 10-day)`.
*   **警报阈值**: 超过参考本金 15% 时触发预警。

---

## 4. POC 验证路径 (The POC Roadmap)

### 阶段 1：特征库构建与似然标定 (Feature & Likelihood)
*   **任务**: 按照 2.2 节优先级协议进行无污染标定。
*   **任务**: 执行分位数 PCA 与 KDE 分布建模。

### 阶段 2：Regime 感知型 Purged Walk-Forward 审计
*   **动态禁运 (Embargo Days)**: `BUST`: 60d | `LATE_CYCLE`: 45d | `CAPITULATION`: 30d | `RECOVERY`: 20d | `MID_CYCLE`: 10d.

### 阶段 3：风险调整增量 Alpha (Success Metrics)
*   基于 3.1 节规模公式，测量桶 B 相对 QQQ VWAP 的风险调整后溢价。

---

## 5. 验收标准 (Final Success Metrics)
1.  **分维度 Brier Score**: $P(BUST)$ 和 $P(CAPITULATION)$ 预测质量显著优于历史频率模型。
2.  **入场质量**: 桶 B 规模公式下的风险调整后 Alpha 显著为正。
3.  **贝叶斯正交性**: 标定与推理信号在代码实现层面物理隔离且逻辑正交。

---
*Architect Review Note: v11 architecture is now fully converged with explicit implementation constraints (Priority, Percentile-PCA, Sizing). Ready for POC Phase 1.*
