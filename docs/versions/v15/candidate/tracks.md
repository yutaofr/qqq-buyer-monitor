# tracks.md — True Kelly Criterion 实施节点
> 全局实施计划 | 架构: architecture.md | SRD: TRUE_KELLY_DEPLOYMENT_SRD.md

每个节点必须满足：**原子性**（单一职责）、**互不依赖**（可并行或严格串行）。

---

## 节点依赖图

```
T-01 (阅读 SRD 与代码审计)
  └─> T-02 (test_kelly_criterion.py)
        └─> T-03 (kelly_criterion.py)
              └─> T-04 (pytest TC-K* GREEN 验收)
                    └─> T-05 (test_kelly_deployment_policy.py)
                          └─> T-06 (kelly_deployment_policy.py)
                                └─> T-07 (pytest TC-P* GREEN 验收)
                                      └─> T-08 (全量回归验收)
                                            └─> T-09 (kelly_ab_comparison.py)
                                                  └─> T-10 (docker-compose 追加)
                                                        └─> T-11 (AC-5 最终验收)
```

---

## 节点详情

### T-01 — 环境与代码审计
- **状态**: `[DONE]`
- **锁定文件**: (只读) `deployment_policy.py`, `src/models/deployment.py`, `regime_audit.json`
- **依赖前置**: 无
- **产出**: 确认以下文件存在且结构正确：
  - `src/engine/v11/signal/deployment_policy.py` ✅ 存在（`_entropy_barrier` 公式已确认）
  - `src/models/deployment.py` ✅ 存在（`deployment_multiplier_for_state()` 接口已确认）
  - `tests/unit/engine/v11/` ✅ 目录存在
  - `docker-compose.yml` ✅ 存在，末尾为 `ortho-audit` service

---

### T-02 — 创建 `test_kelly_criterion.py`（TDD 先写测试）
- **状态**: `[DONE]`
- **锁定文件**: `tests/unit/engine/v11/test_kelly_criterion.py` [NEW]
- **依赖前置**: T-01
- **验收条件**:
  - 文件存在，包含 TC-K01 ~ TC-K20 共 20 个测试函数（含参数化）
  - `docker-compose run test -k test_kelly_criterion` → **全部 FAIL**（预期红色，因为 `kelly_criterion.py` 尚不存在）
- **严禁**:
  - 提前实现任何 `kelly_criterion.py` 函数体
  - 修改任何现有测试文件

---

### T-03 — 实现 `kelly_criterion.py`
- **状态**: `[DONE]`
- **锁定文件**: `src/engine/v11/core/kelly_criterion.py` [NEW]
- **依赖前置**: T-02
- **实现要点**:
  1. `compute_regime_expected_sharpe`: `Σ P(i) * Sharpe_i`，跳过未知 regime，空输入返回 0.0
  2. `compute_regime_sharpe_variance`: `Σ P(i) * (Sharpe_i - E)²`，最低返回 1e-6
  3. `compute_kelly_fraction`:
     - entropy, erp_percentile clip 到 [0.0, 1.0]
     - `value_tilt = 1.0 + (erp_percentile - 0.5) * erp_weight`
     - `variance = compute_regime_sharpe_variance(...) + entropy²`
     - `raw_kelly = (edge * value_tilt) / max(variance, 1e-6)`
     - 最终 `clip(raw_kelly * kelly_scale, -1.0, 1.0)`
  4. `kelly_fraction_to_deployment_state`: 严格按 SRD Section 2.4 阈值实现，边界值：
     - `fraction <= 0.0` → `"DEPLOY_PAUSE"`（包含等于）
     - `fraction <= 0.25` → `"DEPLOY_SLOW"`（包含等于）
     - `fraction <= 0.6` → `"DEPLOY_BASE"`（包含等于）
     - `fraction > 0.6` → `"DEPLOY_FAST"`
  5. `kelly_fraction_to_deployment_multiplier`: 内部组合调用，不重复实现映射逻辑
- **禁止**: 使用线性混合；引入任何 I/O 或状态
- **验收条件**: 无（等待 T-04）

---

### T-04 — pytest TC-K* GREEN 验收
- **状态**: `[DONE]`
- **锁定文件**: (只读)
- **依赖前置**: T-02, T-03
- **命令**:
  ```bash
  docker run --rm -v $(pwd):/app -w /app qqq-monitor:py313 \
    pytest tests/unit/engine/v11/test_kelly_criterion.py -v --tb=short
  ```
- **验收条件**: TC-K01 ~ TC-K20 全部 PASS，0 failures, 0 errors, 0 skipped

---

### T-05 — 创建 `test_kelly_deployment_policy.py`（TDD 先写测试）
- **状态**: `[DONE]`
- **锁定文件**: `tests/unit/engine/v11/test_kelly_deployment_policy.py` [NEW]
- **依赖前置**: T-04
- **验收条件**:
  - 文件存在，包含 TC-P01 ~ TC-P07 共 7 个测试函数
  - `docker-compose run test -k test_kelly_deployment_policy` → **全部 FAIL**（预期红色）
- **严禁**: 提前实现 `kelly_deployment_policy.py`

---

### T-06 — 实现 `kelly_deployment_policy.py`
- **状态**: `[DONE]`
- **锁定文件**: `src/engine/v11/signal/kelly_deployment_policy.py` [NEW]
- **依赖前置**: T-05
- **实现要点**:
  1. `__init__`: 接收 `initial_state, evidence, kelly_scale, erp_weight, regime_sharpes`，默认值见 architecture.md
  2. `decide()` 参数签名必须与 `ProbabilisticDeploymentPolicy.decide()` 完全一致（含 `mid_delta=0.0` 兼容参数）
  3. `decide()` 内部流程:
     - `erp_percentile = value_score` (接口兼容映射)
     - 调用 `compute_kelly_fraction(...)` 获得 `kelly_fraction`
     - `raw_state = kelly_fraction_to_deployment_state(kelly_fraction)`
     - 惰性切换逻辑（见 architecture.md Section 3.2）
     - 构造并返回 11 key 结果 dict
  4. `_entropy_barrier`: 完全复用 `ProbabilisticDeploymentPolicy._entropy_barrier` 公式，不引用原类
  5. `scores` 字段值为 `{"kelly_fraction": kelly_fraction}`
  6. `deployment_multiplier` 必须通过 `deployment_multiplier_for_state(self.current_state)` 获得（不得硬编码）
- **禁止**: 修改 `deployment_policy.py`；引入 conductor 依赖

---

### T-07 — pytest TC-P* GREEN 验收
- **状态**: `[DONE]`
- **锁定文件**: (只读)
- **依赖前置**: T-05, T-06
- **命令**:
  ```bash
  docker run --rm -v $(pwd):/app -w /app qqq-monitor:py313 \
    pytest tests/unit/engine/v11/test_kelly_deployment_policy.py -v --tb=short
  ```
- **验收条件**: TC-P01 ~ TC-P07 全部 PASS，0 failures, 0 errors

---

### T-08 — 全量回归验收（Regression Guard）
- **状态**: `[DONE]`
- **锁定文件**: (只读)
- **依赖前置**: T-07
- **命令**:
  ```bash
  docker-compose run test
  ```
- **验收条件**:
  - `tests/unit/engine/v11/test_deployment_policy.py` 原有测试仍然全部 PASS
  - 全量 0 failures, 0 errors
- **Note**: 这是 AC-1 + AC-4 的联合验收点。**此步骤通过前，不允许继续。**

---

### T-09 — 实现 `kelly_ab_comparison.py`
- **状态**: `[TODO]`
- **锁定文件**: `scripts/kelly_ab_comparison.py` [NEW]
- **依赖前置**: T-08
- **实现要点**:
  1. `_load_trace()`: 加载 CSV，验证必需列存在，`erp_percentile` 缺失时默认填 0.5
  2. `_compute_all_variant_decisions()`: 对每行迭代 6 个 VARIANTS，调用 `compute_kelly_fraction()` + `kelly_fraction_to_deployment_state()`，生成 `{id}_fraction`, `{id}_state` 列
  3. `_compute_metrics()`: 计算 state_distribution, switch_rate, regime_alignment, fraction_stats（含 pseudo-kelly 基准列）
  4. `_render_markdown_report()`: 生成对比表格 + 推荐方案（regime_alignment 综合得分最高者）
  5. `main()`: argparse 入口，输出到 `output_dir`
- **验收条件**: 无（等待 T-11）

---

### T-10 — `docker-compose.yml` 追加 `kelly-ab` service
- **状态**: `[TODO]`
- **锁定文件**: `docker-compose.yml` [APPEND ONLY]
- **依赖前置**: T-09
- **操作**: 仅在文件末尾追加以下内容，不修改任何现有 service：
  ```yaml
    kelly-ab:
      image: qqq-monitor:py313
      build: .
      volumes:
        - .:/app
        - ./data:/app/data
        - ./artifacts:/app/artifacts
        - .env:/app/.env
      env_file:
        - .env
      command: >
        python scripts/kelly_ab_comparison.py
        --trace-path artifacts/v12_audit/execution_trace.csv
        --regime-audit src/engine/v11/resources/regime_audit.json
        --output-dir artifacts/kelly_ab
  ```
- **验收条件**: 无（等待 T-11）

---

### T-11 — AC-5 最终验收（A/B 脚本运行）
- **状态**: `[TODO]`
- **锁定文件**: (只读)
- **依赖前置**: T-10
- **命令**:
  ```bash
  docker-compose run kelly-ab
  ```
- **验收条件**:
  - 无 Python 异常，退出码 0
  - `artifacts/kelly_ab/ab_summary.json` 存在且合法 JSON
  - `artifacts/kelly_ab/ab_report.md` 存在且非空

---

### T-12 — Git 审计与 PR 准备
- **状态**: `[TODO]`
- **锁定文件**: (只读)
- **依赖前置**: T-11
- **命令**:
  ```bash
  git status
  git diff --stat HEAD
  ```
- **验收条件**:
  - Staged 区域为空（所有变更均已 add + commit，或按 PR 流程处理）
  - 仅以下新文件存在于变更列表：
    - `src/engine/v11/core/kelly_criterion.py`
    - `src/engine/v11/signal/kelly_deployment_policy.py`
    - `tests/unit/engine/v11/test_kelly_criterion.py`
    - `tests/unit/engine/v11/test_kelly_deployment_policy.py`
    - `scripts/kelly_ab_comparison.py`
    - `docker-compose.yml`（仅末尾追加）
  - 零个现有文件被修改（strictly no regressions in tracked files）

---

## 快速状态总览

| ID | 节点 | 状态 | 产出文件 |
|:---|:---|:---:|:---|
| T-01 | 环境审计 | `[DONE]` | — |
| T-02 | test_kelly_criterion.py | `[DONE]` | `tests/unit/engine/v11/test_kelly_criterion.py` |
| T-03 | kelly_criterion.py | `[DONE]` | `src/engine/v11/core/kelly_criterion.py` |
| T-04 | TC-K* GREEN 验收 | `[DONE]` | — |
| T-05 | test_kelly_deployment_policy.py | `[DONE]` | `tests/unit/engine/v11/test_kelly_deployment_policy.py` |
| T-06 | kelly_deployment_policy.py | `[DONE]` | `src/engine/v11/signal/kelly_deployment_policy.py` |
| T-07 | TC-P* GREEN 验收 | `[DONE]` | — |
| T-08 | 全量回归验收 | `[DONE]` | — |
| T-09 | kelly_ab_comparison.py | `[TODO]` | `scripts/kelly_ab_comparison.py` |
| T-10 | docker-compose 追加 | `[TODO]` | `docker-compose.yml` (+追加) |
| T-11 | AC-5 最终验收 | `[TODO]` | `artifacts/kelly_ab/` |
| T-12 | Git 审计与 PR 准备 | `[TODO]` | — |

---

© 2026 QQQ Entropy AI Governance — True Kelly Tracks v1.0
