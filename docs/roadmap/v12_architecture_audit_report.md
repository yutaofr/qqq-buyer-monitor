# v12.0 贝叶斯正交因子架构审计报告 (Locked)

> **审计状态**: COMPLETED (Architecture Sealed)
> **审计日期**: 2026-04-01
> **架构师**: Gemini-CLI-Architect
> **目标**: 构建优雅、正交且具备生产韧性的资产配置引擎。

---

## 1. 核心审计结论：语义污染与外壳滞后

当前项目正处于从 v11.5 到 v12.0 的物理重构中点。虽然**算法规格 (Specs)** 已在 `docs/core/` 中对齐，但**工程实现 (Implementation)** 层面存在明显的“语义滞后”。

### 1.1 语义污染 (Semantic Pollution)
- **引擎命名冲突**：`src/engine/v11/` 仍然承载着 v12.0 的 10 因子正交推断逻辑。这导致了开发者认知上的混乱，增加了维护成本。
- **SSoT 路径错位**：关键审计资源 `regime_audit.json` 仍位于 `v11` 路径下，导致 v12.0 的“唯一事实来源”在物理存储上依赖于旧版本目录。

### 1.2 品牌与外壳滞后 (Branding & Shell Lag)
- **前端硬编码**：`src/web/public/index.html` 与 `status.json` 仍标记为 `v11.5 Probabilistic`。
- **输出层错配**：`src/output/discord_notifier.py` 和 `web_exporter.py` 的元数据与话术仍未对齐 v12.0 的“正交因子”与“信息诚实性”话术。

### 1.3 采集器碎片化 (Collector Fragmentation)
- **职责重叠**：`src/collector/` 下同时存在 `macro.py`, `macro_v3.py`, `global_macro.py`。
- **V12 专用采集器已就绪**：`global_macro.py` 已经具备了采集 10 因子（含 Shiller EPS）的能力，但旧采集器未被物理删除，存在被误调用的风险。

---

## 2. 优雅架构重构提议 (v12.0 Elegant Refactor)

为实现架构的“优雅”与“物理对齐”，建议执行以下重构动作：

### A. 引擎语义升级 (Semantic Upgrade)
- **动作**：将 `src/engine/v11/` 重命名为 **`src/engine/v12/`**。
- **意义**：使代码结构与 `docs/V12_ORTHOGONAL_FACTOR_SPEC.md` 实现 1:1 的物理映射。

### B. 采集器归一化 (Collector Consolidation)
- **动作**：移除 `src/collector/macro.py` 和 `macro_v3.py`，将所有 10 因子采集逻辑收拢至 `global_macro.py`。
- **意义**：消除数据采集阶段的“未来函数”泄漏隐患，确保 PIT 合规性。

### C. 输出元数据全量同步 (Branding Synchronization)
- **动作**：全量替换 `src/output/` 和 `src/web/` 中的 `v11.5` 字样为 `v12.0`。
- **意义**：向用户准确传递“正交推断”与“信息熵 Haircut”的决策逻辑。

### D. 研究与生产边界清晰化 (Separation of Concerns)
- **动作**：明确 `src/research/` 仅负责离线数据探索，`src/backtest.py` 负责核心算法的 PIT 因果回归。
- **意义**：防止研究代码侵入生产推断链路。

---

## 3. 重构路线图 (The Road to v12.0 Elegance)

| 阶段 | 任务 | 验收标准 |
| :--- | :--- | :--- |
| **Phase 1** | **物理路径对齐** | `src/engine/v12/` 已创建，Import 路径全量更新。 |
| **Phase 2** | **SSoT 资源迁移** | `regime_audit.json` 移至 v12 资源库。 |
| **Phase 3** | **前端/输出品牌更新** | Discord 消息与 Web UI 显示 `v12.0 Orthogonal-Core`。 |
| **Phase 4** | **采集器清理** | `src/collector/` 下仅保留 v12 必需的传感器代码。 |

---
© 2026 QQQ Entropy 架构审计组.
