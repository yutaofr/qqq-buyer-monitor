# PRD: QQQ Bayesian Orthogonal Allocation Engine (v12.0)

> **Status**: Production Baseline (Locked)
> **Version**: v12.0-ORTHOGONAL-CORE
> **Date**: 2026-04-01

## 1. 产品定义

`qqq-monitor` 已进化为基于**贝叶斯全概率推断**的资产配置决策中枢。它不再依赖人工定义的硬阈值（Hard Thresholds），而是通过对 25 年以上宏观 DNA 的实时学习，利用信息论模型量化市场不确定性，自动生成 `目标 Beta` 建议。

核心原则：
- **正交推断优先**：决策必须基于相互独立的宏观物理维度（贴现、实体、情绪）。
- **信息诚实性**：系统必须诚实地通过 Shannon 熵反映模型不确定性，在高不确定性下自动执行敞口惩罚（Haircut）。
- **PIT (Point-in-Time) 绝对合规**：回测与生产必须严格对齐数据发布滞后，严禁使用任何形式的“未来函数”或事后修正数据。
- **意志与行动分离**：系统必须同时输出 `raw_target_beta` (原始推断) 与 `target_beta` (经过惯性平滑与熵惩罚后的执行目标)。

## 2. 核心目标

| 编号 | 目标 | v12.0 实现路径 |
| :--- | :--- | :--- |
| **G1** | **消除信息近亲繁殖** | 引入 10 因子三层正交体系，替换 v11.5 的共线性因子。 |
| **G2** | **量化模型怀疑度** | 利用 Shannon 熵计算后验分布的混沌度，自动执行 Beta Haircut。 |
| **G3** | **确保回测零水分** | 建立 PIT 合规协议，强制模拟月频实体数据（Capex/EPS）的物理发布滞后。 |
| **G4** | **实现协方差自发现** | 弃用人工权重，由 GaussianNB 根据历史 DNA 的协方差矩阵自动发现因子解释力。 |

## 3. 正交因子矩阵 (10 因子 · 三层体系)

### Layer 1: 贴现层 (Discount) — 货币与通胀周期
- **Real Yield**: 真实融资成本的结构趋势。
- **Treasury Realized Vol (MOVE Proxy)**: 贴现率假设的恐慌度（先行哨兵）。
- **Breakeven Accel**: 通胀预期的变化速度（Fed Put 失效探测）。

### Layer 2: 实体层 (Real Economy) — 资本开支与跨境融资
- **Core Capex Momentum**: 实体经济动能（资本支出幅度）。
- **Copper/Gold ROC**: 全球制造业需求 vs 恐慌。
- **USD/JPY (Carry Trade)**: 全球融资压力与去杠杆信号。

### Layer 3: 情绪层 (Sentiment) — 信用与流动性
- **Credit Spread (Level & Pulse)**: 金融系统的“痛感神经”。
- **Net Liquidity**: 美联储资产负债表的现金流。
- **ERP (TTM-based)**: 基于已实现盈利（Shiller EPS）的股权风险溢价。

---

## 4. 决策流水线 (The Bayesian Loop)

1.  **Ingestion & PIT Alignment**: 采集多源数据，执行物理发布滞后对齐（Tier 1-4）。
2.  **Orthogonalization Engine**: 对 `move_21d` 等共线性因子执行 **Gram-Schmidt 正交化**。
3.  **JIT GaussianNB Training**: 基于 16 年+ PIT 历史 DNA 实时训练模型。
4.  **Posterior Inference**: 计算当前观测值的后验概率分布（Regime Posterior）。
5.  **Entropy Controller**: 计算 Shannon 熵，根据模型不确定性执行 **Beta Haircut**。
6.  **Inertial Beta Mapper**: 在物理可行性约束下，通过惯性机制平滑执行目标。

## 5. 输出面规格 (The Interface)

### 核心输出 (The Signal)
- **`stable_regime`**: 经过惯性平滑后的当前市场制度（BOOM, MID, LATE, BUST）。
- **`target_beta`**: 最终执行目标（已包含熵惩罚与惯性平滑）。
- **`raw_target_beta`**: 原始贝叶斯期望值（用于透明度审计）。
- **`entropy`**: 当前模型的不确定性量化值。

### 质量审计 (Data Quality)
- **`quality_score`**: 基于数据来源（Canonical vs Proxy）的调和平均分。
- **`is_pit_compliant`**: 显式标记当前运行是否符合 PIT 滞后契约。

## 6. 验收标准 (Gate 3)

1.  **极端 Regime 召回率 >= 90%**：确保 2020 COVID 与 2022 通胀紧缩被准确捕捉。
2.  **2018 Q4 无 BUST 误报**：验证实体层正交性对纯情绪波动的免疫力。
3.  **Brier Score <= 0.15**：确保后验概率分布具备极高的预测校准度。
4.  **PIT 测试全绿**：通过自动化测试验证历史数据构建器无“未来函数”泄漏。

---
© 2026 QQQ Entropy 决策系统开发组.
