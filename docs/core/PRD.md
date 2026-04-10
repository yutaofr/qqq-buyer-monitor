# PRD: QQQ Bayesian Orthogonal Allocation Engine (v13.8-ULTIMA)

> **Status**: v13.8 Industrial Acceptance State (Sealed)
> **Disclaimer**: Real-money deployment is strictly contingent on the empirical verification results in `calibration_report.json`.
> **Version**: v13.8-ULTIMA
> **Date**: 2026-04-04

## 1. 产品定义

`qqq-monitor` 已进化为基于**实体增强型贝叶斯推断**的资产配置决策模型。它通过对 8 年以上（2018-2026）宏观 DNA 的深度预热（Deep Hydration），利用 12 因子正交矩阵量化市场重力与流动性，自动生成 `目标 Beta` 建议。其有效性仅限于 `calibration_report.json` 所校验的特定正交空间。

核心原则：
- **物理传导优先**：因子权重由霍华德·马克斯周期论驱动，而非统计最优化。
- **历史自洽性**：通过 2000+ 样本的回演确保先验知识的稳健性。
- **生存红线高于一切**：业务底线（0.5 Beta Floor）具有最高执行优先级。
- **全息透明度**：所有决策环节（包括物理底线拦截、先验锚定点）必须全量透传至用户。

## 2. 核心目标 (v12.1-FIXED 演进)

| 编号 | 目标 | v12.1-FIXED 实现路径 |
| :--- | :--- | :--- |
| **G1** | **消除实体盲视** | 注入 PMI 动量与劳动力市场松弛度，捕捉宏观重力。 |
| **G2** | **回归正统贝叶斯** | 废除错误的线性混合更新，实施 $Posterior \propto Prior \times Likelihood$ 乘积更新，允许置信度有效累积。 |
| **G3** | **似然度平滑** | 实施 Tau=3.0 的温度平滑（Temperature Scaling），消除 Naive Bayes 的过度自信与单极化分布。 |
| **G4** | **根治高熵死锁** | 移除高达 40% 的静态历史先验重力，将历史权重降至 5%，优先考虑“昨日记忆”与“转移矩阵预测”。 |
| **G5** | **建立理性防御** | 引入二阶非线性熵值惩罚 ($\exp(-0.6 \cdot (H_{norm} \cdot \ln(S))^2)$)，在不确定性增加时保护本金。 |

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
- **`posterior_regime`**: 当日后验最高概率的市场制度，对 UI/审计层可见。
- **`execution_regime`**: 稳定器输出的执行层制度，用于节奏与风控，不冒充 UI 真相。
- **`stable_regime`**: 向后兼容的后验制度别名，当前与 `posterior_regime` 保持一致。
- **`target_beta`**: 受 0.5 底线保护的最终执行目标。
- **`is_floor_active`**: 显式标记当前是否处于物理保护状态。
- **`hydration_anchor`**: 展示系统先验数据的起始锚点（2018-01-01）。

---
© 2026 QQQ Entropy 决策系统开发组.
