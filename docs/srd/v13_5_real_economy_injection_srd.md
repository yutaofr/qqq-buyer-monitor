# SRD-v13.5: QQQ Bayesian Orthogonal Factor Monitor - Real-Economy Signal Injection

**Version**: 13.5  
**Status**: Engineering Draft  
**Architect**: Gemini CLI / Senior Systems Architect  
**Reviewers**: Senior Data Scientist  
**Date**: 2026-04-03

---

## 1. 架构目标 (Objective)
通过注入实体经济领先指标（PMI 动量与就业市场松弛度）及重平衡估值权重，消除模型在周期后期的“金融盲视”，解决 v13.4 架构中 0.73 熵值的决策摇摆。

---

## 2. 核心变更 (Core Changes)

### 2.1 特征工程扩展 (Feature Engineering - FR-7)
在 `ProbabilitySeeder` 中追加以下 2 个维度：
1.  **PMI_Acceleration (PMI_Accel)**: 
    *   源数据: `ISM_PMI_Index` (或代理变量)。
    *   算法: 3个月移动窗口的一阶导数。
    *   逻辑: 捕捉制造业扩张速度的衰减，而非绝对水平。
2.  **Beveridge_Curve_Slack (Labor_Slack)**:
    *   源数据: `UNRATE` (失业率) 与 `JTSJOL` (职位空缺)。
    *   算法: `(Job_Openings / Unemployed_Persons)` 的 Z-Score。
    *   逻辑: 捕捉劳动力市场从极度供不应求转向松动的拐点。

### 2.2 传导路径权重调整 (Weights Registry - FR-8)
更新 `src/engine/v11/resources/v13_4_weights_registry.json` 为 v13.5 格式：

| 特征根 (Root) | 权重 (Weight) | 变更理由 |
| :--- | :--- | :--- |
| `credit_spread_bps` | 2.5x | 保持 (Level 1) |
| `erp_ttm_pct` | 2.5x | **提升** (Level 1): 极端估值是周期终结的放大器。 |
| `macro_growth_pivot` | 2.0x | **新增** (Level 2): 实体经济重力。 |
| `net_liquidity_usd_bn`| 2.0x | 保持 (Level 2) |

---

## 3. 技术规范 (Technical Specifications)

### 3.1 重新注水协议 (Mandatory Re-Hydration)
由于特征空间从 10 维扩展至 12 维，系统必须执行以下步骤：
1.  **废弃** 旧的 `data/v13_hydrated_prior.json`。
2.  **强制执行** `scripts/v13_sequential_replay.py`，回放 2018-2026 数据。
3.  **校验**: 在回放结束后，`LATE_CYCLE` 的边缘概率在当前市场环境下预期应由 26% 提升至 40% 以上。

---

## 4. 交付约束 (Constraints)
*   **KISS**: 新增特征必须使用现有的 `_compute_z` 逻辑。
*   **PIT**: 严禁在 PMI 注入中使用修正后的数据。

---
**核准**: Gemini CLI (Architect)
