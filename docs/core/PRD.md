# PRD: QQQ Bayesian Orthogonal Allocation Engine (v13.7-ULTIMA)

> **Status**: Production Baseline (Sealed)
> **Version**: v13.7-ULTIMA
> **Date**: 2026-04-03

## 1. 产品定义

`qqq-monitor` 已进化为基于**实体增强型贝叶斯推断**的资产配置决策中枢。它通过对 8 年以上（2018-2026）宏观 DNA 的深度预热（Deep Hydration），利用 12 因子正交矩阵量化市场重力与流动性，自动生成 `目标 Beta` 建议。

核心原则：
- **物理传导优先**：因子权重由霍华德·马克斯周期论驱动，而非统计最优化。
- **历史自洽性**：通过 2000+ 样本的回演确保先验知识的稳健性。
- **生存红线高于一切**：业务底线（0.5 Beta Floor）具有最高执行优先级。
- **全息透明度**：所有决策环节（包括物理底线拦截、先验锚定点）必须全量透传至用户。

## 2. 核心目标 (v13.7 演进)

| 编号 | 目标 | v13.7 实现路径 |
| :--- | :--- | :--- |
| **G1** | **消除实体盲视** | 注入 PMI 动量与劳动力市场松弛度，捕捉宏观重力。 |
| **G2** | **根治冷启动混沌** | 实施 2018 深度注水协议，消除新实例启动时的高熵死锁。 |
| **G3** | **建立理性防御** | 引入二阶非线性熵值惩罚 ($\exp(-0.6 \cdot H^2)$)，防止自杀式减仓。 |
| **G4** | **实现认知自愈** | 引入 ULTIMA 熔断机制，在持续认知冲突下自动回归信贷基本盘。 |

## 3. 正交因子矩阵 (12 因子 · 三层体系)

### Layer 1: 金融生命线 (Financial Core) — 2.5x 权重
- **Credit Spread**: 金融系统的“痛感神经”。
- **ERP (TTM-based)**: 极致估值作为风险放大器。

### Layer 2: 定价引力 (Valuation Gravity) — 2.0x 权重
- **Real Yield**: 真实融资成本的结构趋势。
- **Net Liquidity**: 货币供应总量。

### Layer 3: 实体与动能 (Real Economy & Momentum) — 1.5x 权重
- **PMI Momentum**: 制造业扩张速度的边际衰减（EWMA 平滑）。
- **Labor Slack**: 劳动力市场从极热转向松动的拐点（EWMA 平滑）。
- **Treasury Vol (MOVE)**: 系统性压力哨兵。
- **Price Momentum (Orthogonal)**: 排除信用风险后的价格动能。

---

## 4. 防御与安全规格 (The Safety Shield)

### 4.1 业务红线 (User Redline)
- **Beta Floor**: 最终推荐 Beta 严禁低于 0.5。系统必须确保在极端噪音下仍持有基本的多头参与度。

### 4.2 级联熔断 (Cascading Breaker)
- **High Entropy Streak**: 记录持续高熵天数。
- **ULTIMA Cut**: 持续 > 21 天则强制切除非核心因子感官，直至认知冲突解除。

---

## 5. 输出面规格 (The Interface)

### 核心输出 (The Signal)
- **`stable_regime`**: 经过状态锚定同步后的当前市场制度。
- **`target_beta`**: 受 0.5 底线保护的最终执行目标。
- **`is_floor_active`**: 显式标记当前是否处于物理保护状态。
- **`hydration_anchor`**: 展示系统先验数据的起始锚点（2018-01-01）。

---
© 2026 QQQ Entropy 决策系统开发组.
