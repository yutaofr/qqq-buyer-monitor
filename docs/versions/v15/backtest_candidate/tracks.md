# tracks.md — True Kelly PnL Backtest 实施节点
> 全局实施计划 | 架构: architecture.md | SRD: TRUE_KELLY_BACKTEST_SRD.md

每个节点必须满足：**原子性**（单一职责）、**互不依赖**（可并行或严格串行）。

---

## 节点依赖图

```
B-01 (创建 TDD 测试 test_kelly_pnl.py)
  └─> B-02 (实现 kelly_pnl_backtest.py 核心账纲)
        └─> B-03 (pytest 验收 AC-8 GREEN)
              └─> B-04 (修复 kelly_ab_comparison.py 的 ERP Bug)
                    └─> B-05 (实现 kelly_pnl_backtest 主执行入口与报告生成)
                          └─> B-06 (docker-compose 追加服务)
                                └─> B-07 (集成运行: kelly-ab 验收 AC-6)
                                      └─> B-08 (集成运行: kelly-pnl 验收 AC-7)
                                            └─> B-09 (最后防线: 全量回归验收 AC-9)
                                                  └─> B-10 (Git 审计与主分支放行)
```

---

## 节点详情

### B-01 — 创建 `test_kelly_pnl.py`（TDD 先决条件）
- **状态**: `[DONE]`
- **锁定文件**: `tests/unit/engine/v11/test_kelly_pnl.py` [NEW]
- **依赖前置**: 无
- **验收条件**:
  - 文件存在，根据 SRD 5. 节包含 5 个财务运算测试（含边角情况测试）。
  - 执行测试：`docker-compose run test -k test_kelly_pnl` 必须完全为红色 FAIL。

---

### B-02 — 实现 `kelly_pnl_backtest.py` 核心回测逻辑
- **状态**: `[DONE]`
- **锁定文件**: `scripts/kelly_pnl_backtest.py` [NEW]
- **依赖前置**: B-01
- **实现要点**:
  - 实现 `_compute_pnl_curve`: 对 DataFrame 执行 iter 或矢量化，基于 `close` 计算 `daily_return`。
  - 处理交易摩擦 `transaction_cost`，若当天的 `multiplier` 和前一天不同，则在当日净值扣抵。
  - 实现 `_compute_performance_metrics`: 标准化算子 CAGR, MDD, 年化 Sharpe 等，确保安全除数。
- **验收条件**: 逻辑实现暂不执行主程序（保护单体）。

---

### B-03 — 财务量化单元测试 GREEN 验收 (AC-8)
- **状态**: `[DONE]`
- **依赖前置**: B-02
- **命令**: 
  ```bash
  docker-compose run test -k test_kelly_pnl
  ```
- **验收条件**: 5 个 PnL 数学公式测试无报错全过（GREEN）。

---

### B-04 — 修复 `_load_trace` 中的 ERP 数据空洞
- **状态**: `[DONE]`
- **锁定文件**: `scripts/kelly_ab_comparison.py`
- **依赖前置**: 无（可与 B-01 并行）
- **操作**:
  - 如果 `erp_percentile` 在 csv 中缺失，检查提取 `target_beta` 进行转换推算。
  - 应用公式 `(1.0 - beta_norm).clip(0.0, 1.0)` 将 `beta` 映射为逆向的百分位。
- **验收条件**: 无可见输出，由后续集成节点连带测试。

---

### B-05 — 完善 `kelly_pnl_backtest.py` 报告主程序
- **状态**: `[DONE]`
- **锁定文件**: `scripts/kelly_pnl_backtest.py`
- **依赖前置**: B-03, B-04
- **实现要点**:
  - 导入并复用 `kelly_ab_comparison._load_trace` (已获得修复) 及 `_compute_all_variant_decisions`。
  - 执行 `pseudo_kelly` 与其他真凯利变体的横向净值模拟对比。
  - 生成表格化的 Markdown 报告及 JSON 指标存储。

---

### B-06 — 配置 Docker 服务入口
- **状态**: `[DONE]`
- **锁定文件**: `docker-compose.yml`
- **依赖前置**: B-05
- **操作**: 文件最后追加 `kelly-pnl` 容器服务信息。

---

### B-07 — 执行 A/B 实验修正确认 (AC-6)
- **状态**: `[TODO]`
- **命令**: 
  ```bash
  docker-compose run kelly-ab
  ```
- **验收条件**: 成功运行，检查新生成的 `artifacts/kelly_ab/ab_summary.json`。观察不同 `erp` 系列的统计分布是否开始分化。

---

### B-08 — 生成最终 PNL 指标报告 (AC-7)
- **状态**: `[TODO]`
- **命令**: 
  ```bash
  docker-compose run kelly-pnl
  ```
- **验收条件**: `artifacts/kelly_ab/pnl_summary.json` 和 `pnl_report.md` 生成，且内部包含 CAGR 和 MDD。

---

### B-09 — 全量回路安全阻断器 (AC-9)
- **状态**: `[TODO]`
- **命令**: 
  ```bash
  docker-compose run test
  ```
- **验收条件**: 历史存留包含 `test_kelly_criterion`, `test_kelly_deployment_policy` 以及其它数百个测试，0 FAILURES。

---

### B-10 — Code 冻结与 PR 批准合并
- **状态**: `[TODO]`
- **命令**: `git diff`, `git status`
- **操作**: 将修复后的 AB 测试与新的回测工具 Push 到 `feature/true-kelly-deployment`，通知架构层执行主干融合。

---

© 2026 QQQ Entropy AI Governance — True Kelly Backtest Tracks v1.0
