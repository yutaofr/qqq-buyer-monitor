# v12.0 项目组织与工程效能审计报告 (Locked)

> **审计状态**: COMPLETED (Operational Governance Sealed)
> **审计日期**: 2026-04-01
> **架构师**: Gemini-CLI-Architect
> **目标**: 清理工程债务，建立数据与脚本的严格分层。

---

## 1. 核心审计结论：碎片化与语义偏移

项目目前在组织架构层面表现出明显的**多版本混居 (Multi-version Co-habitation)** 现象，物理文件夹的职责边界正在模糊。

### 1.1 脚本目录的“冷战遗存” (The Script Jungle)
- **碎片化严重**: `scripts/` 下混杂了大量的 v11 实验脚本（`v11_poc_phase1.py`, `v11_historical_analyzer.py`）。这些脚本在 v12 架构下已失去生产价值，但仍占据顶层目录空间。
- **职责重叠与语义歧义**: 存在多个功能相近的宏观构建脚本（`build_historical_macro_dataset.py` vs `v12_historical_data_builder.py`）。
- **缺乏归档分流**: 所有的单次运行脚本（One-off scripts）与生产级辅助脚本处于同一目录级别。

### 1.2 数据层的“物理熵增” (Data Layer Entropy)
- **生产 DNA 与研究产物混放**: `data/` 根目录下混杂着生产数据 (`macro_historical_dump.csv`)、旧版 POC 结果 (`v11_poc_phase1_results.csv`) 以及临时备份文件 (`.bak`, `.tmp4.csv`)。
- **缓存策略不透明**: `qqq_history_cache.csv` 与 `signals.db` 直接暴露在 `data/` 下，未建立明确的 `dna/` (生产数据)、`cache/` (运行时缓存) 和 `audit/` (审计结果) 分层。

### 1.3 CI/CD 工作流的语义脱节 (Workflow Semantic Drift)
- **环境隔离风险**: 工作流（如 `runtime.yml`）中的环境变量命名与 v12 架构的 10 因子要求尚未完成强制审计。
- **Docker 强制性缺失**: 虽然 `GEMINI.md` 强制要求 Docker，但在 CI/CD 层面的自动化测试（`ci.yml`）若直接在 Runner 上运行 `pytest`，将破坏“环境 bit-identical 对齐”的原则。

---

## 2. 组织重构建议 (Organizational Governance)

为实现工程效能的“优雅归位”，建议执行以下重构动作：

### A. 脚本分流计划 (Script Stratification)
- **动作**: 创建 `scripts/archive/` (历史遗留) 和 `scripts/utils/` (生产辅助)。
- **操作**: 仅保留 `v12_historical_data_builder.py` 等核心构建器于顶层。

### B. 数据三层建模 (Data Stratification)
- **动作**: 建立物理隔离层。
    - `data/dna/`: 存放 10 因子 PIT 历史数据。
    - `data/cache/`: 存放运行时缓存与临时数据库。
    - `data/audit/`: 存放回测报告与 POC 指标。
- **意义**: 物理层面的 SSoT 隔离。

### C. 环境变量标准化 (Env-SSoT)
- **动作**: 在根目录锁定 `.env.example`，明确 v12.0 所需的所有 API (FRED, yf, Shiller) 权限。
- **操作**: 工作流文件必须通过 `docker compose -f docker-compose.yml run` 进行容器化测试。

---

## 3. 组织演进路线图 (The Road to Operational Excellence)

| 阶段 | 任务 | 验收标准 |
| :--- | :--- | :--- |
| **Phase 1** | **物理归档 (The Big Sweep)** | `scripts/` 顶层仅保留 v12 核心，旧版脚本全量入库。 |
| **Phase 2** | **数据层物理重构** | `data/` 下不再有杂散的 `.bak` 和旧版本 POC 结果。 |
| **Phase 3** | **CI/CD 语义对齐** | 工作流全量迁移至容器化测试路径。 |
| **Phase 4** | **环境隔离验证** | 通过 `.env.example` 完成全量环境变量审计。 |

---
© 2026 QQQ Entropy 组织架构组.
