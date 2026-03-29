# v11.0 Design and Execution Plan: Probabilistic & Permanent Dual-Track Architecture

## 1. 核心愿景 (Vision)
v11.0 代码代号 "Entropy"，旨在构建一个**永久双轨 (Permanent Dual-Track)** 的决策引擎。通过贝叶斯推理融合宏观先验与战术似然，并在物理层面彻底隔离存量风险与增量机会，实现极端环境下的理性决策。

---

## 2. 贝叶斯推理规范 (Bayesian Inference Specification)

### 2.1 决策公式
最终仓位决策基于各 Regime 的后验概率：
$$P(Regime_i | Tactical) = \frac{P(Tactical | Regime_i) \times P(Regime_macro_i)}{Z}$$

### 2.2 似然函数校准协议 (Likelihood Calibration Protocol)
*   **经验分布建模**: 拒绝参数化假设，采用 1995-2020 样本集的经验直方图。
*   **Regime 样本划分**: 基于 NBER 衰退标定（BUST）与 Forward Return 聚类标定（CAPITULATION, LATE_CYCLE 等）。
*   **似然得分提取**: 对于实时输入的战术信号向量（VIX, Breadth, DD），在对应 Regime 的历史分布中提取似然概率。
*   **避免过拟合**: 似然函数每 12 个月更新一次，且必须通过 Leave-one-out 交叉验证。

---

## 3. 永久双轨架构 (Permanent Dual-Track Architecture)

系统在逻辑与资金层面执行**物理隔离**，且**永久不合流**，以保持决策纯净度。

### 3.1 桶 A：存量维护轨道 (Legacy Bucket)
*   **资金来源**: 初始存量资金。
*   **核心逻辑**: 锚定 HWM (High Water Mark)。在宏观 $P(BUST)$ 上升时强制减仓。
*   **目标**: 长期资本保护，执行低频、高确定性的宏观调仓。

### 3.2 桶 B：增量部署轨道 (Active Bucket)
*   **资金来源**: **仅限外部新现金注入**。严禁桶 A 资金转入。
*   **核心逻辑**: T+0 盈亏比驱动。不受存量水位污染，专注于捕捉 `CAPITULATION` 与 `RECOVERY` 阶段的超额收益。
*   **目标**: 优化增量购买力，执行“猎杀式”入场。

### 3.3 零耦合原则 (Zero-Coupling)
*   桶 A 与 桶 B 的仓位决策逻辑完全解耦。
*   桶 B 决策引擎禁止读取桶 A 的持仓成本与盈亏状态。

---

## 4. 执行计划：POC 验证路径 (The POC Roadmap)

### 阶段 1：特征库构建与似然标定 (Feature Engineering & Likelihood)
*   构建 1995-2026 的“分位数特征库”。
*   建立各战术信号在五个 Regime 下的历史频率分布表。

### 阶段 2：模型原型与 Walk-Forward 审计
*   **审计协议**: 
    *   以 5 年为训练窗，滚动验证 1 年。
    *   **对照组**: v10 HSM 确定性模型。
    *   **实验组**: v11 Probabilistic Bayesian 模型。
*   **压力测试**: 特别审计 2000 (Dot-com), 2008 (Lehman), 2020 (Covid), 2025 (Tariff Shock) 四个关键窗口。

### 阶段 3：质量指标验证 (Quality Metrics)
*   **入场质量 (Bottom Proximity)**: 测量桶 B 在 `CAPITULATION` 触发后的入场点相对于真实底部的距离（时间与空间维度）。

---

## 5. 验收标准 (Revised Metrics)
1.  **入场精度**: 桶 B 在重大回撤（>20%）中的入场点处于底部 15% 价格区间的概率 > 70%。
2.  **预测增益**: 贝叶斯模型的 Brier Score 显著优于 Climatological Baseline（历史基础概率模型）。
3.  **架构纯净度**: 桶 A/B 代码物理隔离，无任何共用的状态读取接口。
4.  **纪律性**: 桶 B 资金流向存量账户的“会计合流”仅作为结果展示，不参与逻辑运算。

---
*Architect Review Note: v11 moves away from complexity. The strength lies in the permanent separation of fear (Bucket A) and opportunity (Bucket B).*
