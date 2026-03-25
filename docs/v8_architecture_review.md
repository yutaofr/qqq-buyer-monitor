# v8.0 Architecture Review: SRD vs ADD Alignment Report

## 1. Executive Summary
经评审，**v8.0 ADD (实现方案) 与 SRD (需求文档) 高度对齐**。ADD 准确捕捉了 SRD 中确立的“系统身份转变（推荐引擎非管理引擎）”、“Tier-0 线性决策链”以及“存量/增量解耦”的核心原则。

## 2. 核心特性对齐检查

| 特性分类 | SRD 需求要求 (SRD §6/7) | ADD 实现设计 (ADD Phase 1-7) | SDT 测试设计 (SDT §3/5) | 对齐状态 |
| :--- | :--- | :--- | :--- | :--- |
| **系统边界重塑** | 仅推荐目标 Beta，严禁金额计算。 | 删除 `build_execution_actions`。 | TC-EP-001 (接口删除), TC-EP-002 (无金额)。 | ✅ 完美对齐 |
| **Tier-0 硬约束** | `tier0_regime` 压制 Beta 天花板。 | `decide_risk_state` 接入拦截逻辑。 | TC-RC-001 (CRISIS), TC-RC-002 (RICH)。 | ✅ 完美对齐 |
| **Tier-0 软约束** | `RICH_TIGHTENING` 下降速，允许突破。 | 实现 `_TIER0_DEFAULT_CEILING` 等核心逻辑。 | TC-DC-003 (默认上限), TC-DC-004 (突破)。 | ✅ 完美对齐 |
| **决策链线性化** | 四级单向决策链。 | 模块改造顺序严格遵循线性 Pipeline。 | TC-INT-001/002 (端到端集成测试)。 | ✅ 完美对齐 |
| **存量/增量解耦** | 仅推荐目标 Beta，严禁金额计算。 | 移除 cash-precheck 依赖，逻辑纯净化。 | TC-INT-004 (属性独立性)。 | ✅ 完美对齐 |
| **v6 状态解耦** | 废弃 `AllocationState` 驱动的选择。 | `find_best_allocation_v8` 数学约束接口。 | TC-AS-004 (签名检查)。 | ✅ 完美对齐 |

## 3. 验收标准覆盖 (AC-13 to AC-19)

- **AC-13 (CRISIS -> EXIT):** ADD Phase 2.1 明确覆盖。
- **AC-14 (RICH_TIGHTENING -> 0.30):** ADD Phase 2.1 明确覆盖。
- **AC-15 (Soft Ceiling Override):** ADD Phase 3.2 明确覆盖（独立阈值 `0.70`）。
- **AC-16 (Decoupling):** [已移除] 存量/增量逻辑物理隔离。
- **AC-17 (No Amount Output):** ADD Phase 1 彻底删除旧接口。
- **AC-18 (Consistency):** ADD Phase 12 将其列为强约束。
- **AC-19 (Portfolio Beta):** ADD Phase 3.2 组合 Beta 计算公式正确。

## 4. 架构师观察与补充建议

1.  **输出段落演进**：初步设计文档 (`separation-design.md`) 曾建议“三段式输出”，SRD 最终定稿为“两段式（Risk+Beta / Deployment）”。ADD 遵循了 SRD 的最新定稿，这是合理的架构演进。
2.  **测试驱动能力**：SDT (`v8.0_linear_pipeline_sdt.md`) 针对 ADD 的每个 Phase 都设计了严密的单元测试和集成测试，特别是对 `RICH_TIGHTENING` 场景下的“软约束默认上限 (TC-DC-003)”与“突破行为 (TC-DC-004)”进行了精确定义，确保了设计意图的可测试性。
3.  **逻辑拦截点选择**：ADD 在 `Risk Controller` 内部最顶层进行 Tier-0 拦截，优于在外部注入，保障了“零偏见”的宏观压制。
4.  **下一步执行风险**：ADD 的 Phase 1 (删除旧代码) 是破坏性的。建议在开始 Step 1 之前，确保全量测试脚本已同步更新至引用 `BetaRecommendation`，否则会导致系统无法编译。

**结论：ADD 设计严谨，完全满足 SRD 指标要求。建议直接推进至开发。**
