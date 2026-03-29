# v11.0 Design and Execution Plan: Probabilistic & Dual-Bucket Architecture

## 1. 核心愿景 (Vision)
v11.0 代码代号 "Entropy"，旨在从 v10.0 的“确定性逻辑”进化为“概率化决策系统”。它承认认知的局限性，通过统计学意义上的概率分布与物理隔离的资金管理，构建一个更具反脆弱性的决策引擎。

---

## 2. 深度架构：贝叶斯融合 (Bayesian Fusion of Tier-0 & Tactical)

### 2.1 非二元关系 (Non-Binary Interaction)
在 v10 中，Tier-0 是下游的“硬开关”。在 v11 中，二者互为影响因子：
*   **Tier-0 (先验 Prior)**: 基于信用利差、Net Liquidity、ERP 分位数的长期宏观背景。它决定了当前战场的“基本重力”。
*   **v10 Tactical (证据 Likelihood)**: 基于价格行为、波动率结构、市场宽度的中短期信号。
*   **动态权重合成**: 
    $$P(Action) = \frac{P(Tactical | Regime_{macro}) \times P(Regime_{macro})}{Z}$$
    *   当宏观处于 `BUST` 极端（高分位数）时，宏观因子的权重自动“吸走”所有决策熵，强制执行防御。
    *   当宏观处于 `NEUTRAL` 时，战术信号拥有更高的敏感度。

### 2.2 统计支撑与信号纠偏
*   引入**信号置信度 (Confidence Score)**：若宏观与战术信号背离，系统不会简单报错，而是输出“高熵/不确定”状态，自动通过 Kelly 公式缩减仓位。

---

## 3. 双筒架构 (Dual-Bucket System Design)

为了消除“路径依赖”与“认知污染”，系统逻辑在架构层面进行物理隔离：

### 3.1 桶 A：存量维护系统 (Legacy/Core Bucket)
*   **定位**: 保护已实现利润，管理长期风险。
*   **锚定物**: 历史净值峰值 (HWM)。
*   **逻辑**: 执行“阶梯式止盈”与“底仓防御”。在 `LATE_CYCLE` 中，它优先缩减 QLD 暴露。
*   **心理约束**: 它的决策受已发生回撤的影响，目标是最小化最大回撤 (MDD)。

### 3.2 桶 B：增量部署系统 (Incremental/Active Bucket)
*   **定位**: 优化新资金的入场效能，利用市场恐慌。
*   **锚定物**: 现金注入点 (T+0 Cost Basis)。
*   **逻辑**: **纯净决策**。它不关心存量账户亏损了多少，只关心当前的“盈亏比”。
*   **核心特性**: 在 `CAPITULATION` 阶段，即使存量桶在执行防御，增量桶也可以开启 `DEPLOY_FAST` 通道，以 QQQ 现货或小比例 QLD 进行抢筹。
*   **合流机制**: 增量资金在入场 N 天（或盈利覆盖波动）后，平滑并入存量桶，接受长期风险控制。

---

## 4. 执行计划：POC 验证路径 (The POC Roadmap)

### 阶段 1：特征库构建 (Feature Engineering)
*   构建 1995-2026 的“分位数特征库”。
*   计算 ERP、Spread、Liquidity 的 20 年滚动分布函数。

### 阶段 2：模型原型与 Walk-Forward 审计
*   **审计协议**: 
    *   以 5 年为训练窗，滚动验证 1 年。
    *   **对照组**: v10 HSM 确定性模型。
    *   **实验组**: v11 Probabilistic Bayesian 模型。
*   **压力测试**: 特别审计 2000 (Dot-com), 2008 (Lehman), 2020 (Covid), 2025 (Tariff Shock) 四个关键窗口。

### 阶段 3：双筒逻辑模拟
*   模拟在 2022 年大回撤期间，若有增量资金注入，v11 的“双筒”逻辑与 v10 的“合流”逻辑在最终收益率与回撤表现上的差异。

---

## 5. 验收标准 (Success Metrics)
1.  **决策平滑度**: 信号跳变（Whipsaw）次数较 v10 降低 >30%。
2.  **底部灵敏度**: 在 `CAPITULATION` 触发后 5 个交易日内，增量桶的入场响应率 >90%。
3.  **统计显著性**: 概率分布的 Brier Score 优于随机分类器 2x 以上。
4.  **架构纯净度**: 存量与增量桶的决策代码实现 0 耦合。

---
*Architect Review Note: This document serves as the SSoT for v11 development. Implementers must adhere to the physical separation of buckets defined in Section 3.*
