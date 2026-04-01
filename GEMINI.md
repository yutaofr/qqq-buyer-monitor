# GEMINI.md - QQQ Bayesian Orthogonal Factor Monitor (v12.0)

> **The Design Spec & Philosophy**
> 本文档定义了项目的架构核心与设计哲学。开发与操作指南请参见 **[AGENTS.md](./AGENTS.md)**。

---

## 1. 架构核心 (v12.0 Orthogonal-Core)
`qqq-monitor` 在 v12.0 中全面进化为“贝叶斯正交因子引擎”。系统通过三层 10 因子的正交矩阵，利用信息熵控制与 Gram-Schmidt 正交化算法实现全天候宏观风险定价。

### 核心组件职责
- **Orthogonal Matrix (v12):** 三层因子架构（贴现层、实体层、情绪层），彻底消除信息近亲繁殖。
- **Gram-Schmidt Engine:** 在线正交化。通过 Expanding Window 残差提取，确保 MOVE 与利差等因子的条件独立。
- **PIT Integrity Layer:** 点时合规层。严格对齐金融 (T+1)、实体 (Release+30d) 与盈利 (MonthEnd+30d) 的物理发布滞后。
- **Shannon Entropy Controller:** 风险调节层。基于后验分布熵值对敞口执行惩罚 (Haircut)，实现信息诚实性。
- **Inertial Beta Mapper:** 决策平滑层。在确保敞口符合贝叶斯期望的前提下，通过惯性机制减少换手。

## 2. 设计哲学 (Inviolable Principles)
- **正交推断优先**: 决策必须基于相互独立的宏观物理维度。
- **信息诚实性**: 承认高维空间的稀疏性，利用 Shannon 熵量化模型“怀疑度”。
- **PIT 绝对合规**: 回测与生产必须严格对齐数据发布滞后，严禁未来函数。
- **意志与行动分离**: 信号接口必须同时包含 `raw_target_beta` (原始推断) 与 `target_beta` (执行目标)。

## 3. SSoT 索引 (Single Source of Truth)
- **架构规格书**: `docs/versions/v12/V12_ORTHOGONAL_FACTOR_SPEC.md`
- **产品需求 (PRD)**: `docs/core/PRD.md`
- **核心哲学**: `docs/core/V12_USER_PHILOSOPHY.md`
- **宏观 DNA 库**: `data/macro_historical_dump.csv`
- **审计配置文件**: `src/engine/v12/resources/regime_audit.json`

---
👉 **开发、编码规范与操作命令请移步至: [AGENTS.md](./AGENTS.md)**

---
© 2026 QQQ Entropy 架构设计组.
