# PRD: True Kelly Criterion for Incremental Deployment Pacing
> Version: 1.0 | Status: APPROVED | Governed by: TRUE_KELLY_DEPLOYMENT_SRD.md

---

## 1. 产品背景与核心问题

### 1.1 现状痛点

现有 `ProbabilisticDeploymentPolicy._score_states()` 使用启发式评分函数（ad-hoc weighted summation），其本质是人工拼凑的线性组合，缺乏数学最优性保障：

- **无经济基础**：权重系数无法从现实世界中推导，只能凭感觉校准。
- **不可解释**：无法向用户说明"为什么当前选择 DEPLOY_FAST 而非 DEPLOY_BASE"。
- **无法参数化实验**：调参空间不透明，A/B 对比缺乏数学框架支撑。

### 1.2 产品目标

引入**数学最优的真凯利准则（True Kelly Criterion）**作为资金部署决策内核，实现：

1. **数学可证明的最优性**：Kelly Criterion 是对数财富期望最大化的解析解。
2. **可解释性**：每次决策附带 `kelly_fraction` 诊断字段，用户可直接查看计算依据。
3. **受控的实验框架**：通过 `kelly_scale` 与 `erp_weight` 两个维度的 6 变体矩阵，系统性评估保守度与价值倾斜的影响。
4. **零回归**：新策略以**平行模块**形式存在，绝不替换现有假凯利（用于 A/B 对比基准）。

---

## 2. 核心用例

### UC-01: Kelly 分数计算（核心数学引擎）

- **触发条件**：每个日历交易日，贝叶斯推理引擎输出后验概率向量后。
- **输入**：`posteriors: dict[str, float]`, `entropy: float`, `erp_percentile: float`, `kelly_scale`, `erp_weight`
- **处理**：执行广义多状态 Kelly 公式（SRD Section 2.2）
- **输出**：`kelly_fraction: float ∈ [-1.0, 1.0]`
- **约束**：纯函数，无副作用，无 I/O，无全局状态。

### UC-02: 连续 Kelly Fraction → 离散部署状态映射

- **输入**：`kelly_fraction: float`
- **映射规则**（物理规格，不可修改）：
  - `fraction ≤ 0.0` → `DEPLOY_PAUSE`
  - `0.0 < fraction ≤ 0.25` → `DEPLOY_SLOW`
  - `0.25 < fraction ≤ 0.6` → `DEPLOY_BASE`
  - `fraction > 0.6` → `DEPLOY_FAST`
- **输出**：`DeploymentState` 字面值

### UC-03: Kelly 部署策略决策（含惰性状态切换）

- **触发条件**：同 UC-01
- **接口要求**：与 `ProbabilisticDeploymentPolicy.decide()` 完全兼容（相同参数签名 + 相同返回 key 集合）
- **额外输出**：`kelly_fraction` 诊断字段
- **惰性切换**：复用 `_entropy_barrier()` 逻辑，防止高熵环境下的频繁状态跳变。

### UC-04: A/B 对比报告生成

- **触发条件**：研究员手动运行 `docker-compose run kelly-ab`
- **输入**：`artifacts/v12_audit/execution_trace.csv`（历史回溯数据）
- **处理**：对每行数据，计算 6 个 True Kelly 变体 + 1 个假凯利基准的部署决策
- **输出**：
  - `artifacts/kelly_ab/ab_summary.json`（机器可读）
  - `artifacts/kelly_ab/ab_report.md`（人类可读 Markdown 报告，含 regime 对齐率排名）

---

## 3. 非功能性需求

### 3.1 数值稳定性（强制）

| 约束 | 规格 |
|:---|:---|
| Sharpe 方差分母下界 | `max(variance, 1e-6)` |
| 熵输入 clip | `[0.0, 1.0]` |
| ERP 百分位 clip | `[0.0, 1.0]` |
| Kelly Fraction 输出 clip | `[-1.0, 1.0]` |
| `_entropy_barrier` 分母下界 | `max(1e-6, 1.0 - h)` |

### 3.2 接口兼容性（强制）

`KellyDeploymentPolicy.decide()` 的返回 dict 必须包含以下 11 个 key：

```
deployment_state, raw_state, deployment_multiplier,
readiness_score, value_score, action_required,
reason, scores, barrier, evidence, kelly_fraction
```

### 3.3 隔离性（强制）

- 新模块对现有代码库**零修改**（仅追加新文件 + docker-compose 末尾追加 service）
- 原有 `ProbabilisticDeploymentPolicy` 完整保留，不受任何影响

### 3.4 Regime Sharpe 标定值（默认值合同）

```python
DEFAULT_REGIME_SHARPES = {
    "MID_CYCLE":  1.0,
    "LATE_CYCLE": 0.2,
    "BUST":       -0.8,
    "RECOVERY":   1.2,
}
```

这些值来自 `regime_audit.json`，是**只读引用**。coding agent 严禁修改 `regime_audit.json`。

---

## 4. 禁止事项（产品红线）

| 禁止行为 | 原因 |
|:---|:---|
| 使用线性混合 `m * L + (1-m) * P` 替代除法 | 违反 Kelly 数学定义，且违反 GEMINI.md Bayesian Integrity Lock |
| 修改 `deployment_policy.py` | A/B 基准保护 |
| 修改 `conductor.py` | Scope 边界 |
| 修改任何现有测试 | 测试变绿不等于交付完成 |
| 修改 `regime_audit.json` | 数值源保护 |
| 修改 `deployment_multiplier_for_state()` | 共享函数，超出 Scope |

---

## 5. 成功标准

1. `docker-compose run test` → **0 failures, 0 errors**
2. 所有 TC-K01 ~ TC-K20 通过（数学正确性）
3. 所有 TC-P01 ~ TC-P07 通过（接口兼容性）
4. `test_deployment_policy.py` 原有测试无回归
5. `docker-compose run kelly-ab` 成功生成 `ab_summary.json` 与 `ab_report.md`

---

© 2026 QQQ Entropy AI Governance — True Kelly PRD v1.0
