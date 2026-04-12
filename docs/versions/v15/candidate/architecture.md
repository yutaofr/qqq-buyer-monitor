# Architecture: True Kelly Criterion Module (v1.0)
> 支撑文档: `TRUE_KELLY_DEPLOYMENT_SRD.md` | 关联 PRD: `PRD.md`

---

## 1. 模块划分

```
src/
└── engine/
    └── v11/
        ├── core/
        │   ├── [EXISTING] bayesian_inference.py     # 🔒 禁区：不得修改
        │   ├── [EXISTING] prior_knowledge.py        # 🔒 禁区：不得修改
        │   └── [NEW] kelly_criterion.py             # ✅ 纯数学模块
        └── signal/
            ├── [EXISTING] deployment_policy.py      # 🔒 禁区：A/B 基准保留
            └── [NEW] kelly_deployment_policy.py     # ✅ True Kelly 策略
src/
└── models/
    └── [EXISTING] deployment.py                     # 🔒 禁区：不得修改

tests/
└── unit/
    └── engine/
        └── v11/
            ├── [EXISTING] test_deployment_policy.py # 🔒 禁区：不得修改
            ├── [NEW] test_kelly_criterion.py        # ✅ 数学单元测试
            └── [NEW] test_kelly_deployment_policy.py# ✅ 策略单元测试

scripts/
└── [NEW] kelly_ab_comparison.py                     # ✅ A/B 对比脚本

docker-compose.yml
└── [APPEND] kelly-ab service                        # ✅ 末尾追加，不改现有
```

---

## 2. 数据流向

```
[贝叶斯引擎] --posteriors--> [KellyDeploymentPolicy.decide()]
                                     │
                    ┌────────────────┼─────────────────────┐
                    ▼                ▼                      ▼
          compute_regime_      compute_regime_         entropy (input)
          expected_sharpe()    sharpe_variance()       erp_percentile (input)
                    │                │
                    └───────┬────────┘
                            ▼
                  compute_kelly_fraction()
                            │
                    kelly_fraction: float ∈[-1,1]
                            │
              ┌─────────────┼──────────────────┐
              ▼             ▼                  ▼
  kelly_fraction_to_   惰性切换逻辑      _entropy_barrier()
  deployment_state()   (evidence积累)
              │
              ▼
  deployment_multiplier_for_state()  [src/models/deployment.py ← 只读引用]
              │
              ▼
         decide() 返回 dict（11 keys）
```

### 数据流约束

- `kelly_criterion.py` → `deployment_policy.py`：**禁止依赖**（单向隔离）
- `kelly_deployment_policy.py` → `kelly_criterion.py`：允许（单向依赖）
- `kelly_deployment_policy.py` → `src/models/deployment.py`：只读引用，允许
- `kelly_ab_comparison.py` → `kelly_criterion.py`：允许（脚本层入口）
- 任何新模块 → `conductor.py`：**绝对禁止**

---

## 3. 接口契约（API Contracts）

### 3.1 `kelly_criterion.py` — 函数契约

#### `compute_regime_expected_sharpe`

```python
def compute_regime_expected_sharpe(
    posteriors: dict[str, float],   # {regime: probability}, 值域 [0,1]，无需和为1（自动加权）
    regime_sharpes: dict[str, float],  # {regime: sharpe_ratio}
) -> float:
    # E[Sharpe] = Σ P(regime_i) × Sharpe_i
    # 健壮性: 未知 regime 静默跳过; 空输入返回 0.0
    # 返回范围: 理论上 [-inf, +inf]，实际约 [-0.8, 1.2]
```

#### `compute_regime_sharpe_variance`

```python
def compute_regime_sharpe_variance(
    posteriors: dict[str, float],
    regime_sharpes: dict[str, float],
    expected_sharpe: float,
) -> float:
    # Var[Sharpe] = Σ P(regime_i) × (Sharpe_i - E[Sharpe])²
    # 约束: 返回值 >= 1e-6（防除零）
```

#### `compute_kelly_fraction`

```python
def compute_kelly_fraction(
    *,                               # 强制关键字参数
    posteriors: dict[str, float],
    regime_sharpes: dict[str, float],
    entropy: float,                  # clip 到 [0.0, 1.0]
    erp_percentile: float,           # clip 到 [0.0, 1.0]，0.5=中位数
    kelly_scale: float = 0.5,        # 0.5=half-Kelly; 0.25=quarter-Kelly
    erp_weight: float = 0.4,         # ERP 对 value_tilt 的影响权重
) -> float:
    # 公式:
    #   edge     = E[Sharpe]
    #   variance = Var[Sharpe] + entropy²
    #   tilt     = 1.0 + (erp_percentile - 0.5) × erp_weight
    #   raw_kelly = (edge × tilt) / max(variance, 1e-6)
    #   return clip(raw_kelly × kelly_scale, -1.0, 1.0)
```

#### `kelly_fraction_to_deployment_state`

```python
def kelly_fraction_to_deployment_state(kelly_fraction: float) -> str:
    # 物理映射（不可修改阈值）:
    # fraction <= 0.0           → "DEPLOY_PAUSE"
    # 0.0 < fraction <= 0.25   → "DEPLOY_SLOW"
    # 0.25 < fraction <= 0.6   → "DEPLOY_BASE"
    # fraction > 0.6           → "DEPLOY_FAST"
```

#### `kelly_fraction_to_deployment_multiplier`

```python
def kelly_fraction_to_deployment_multiplier(kelly_fraction: float) -> float:
    # 内部调用 kelly_fraction_to_deployment_state()
    # 再调用 deployment_multiplier_for_state()（src/models/deployment.py）
    # 映射: PAUSE→0.0, SLOW→0.5, BASE→1.0, FAST→2.0
```

---

### 3.2 `kelly_deployment_policy.py` — 类契约

#### 构造器

```python
class KellyDeploymentPolicy:
    def __init__(
        self,
        *,
        initial_state: str = "DEPLOY_BASE",
        evidence: float = 0.0,
        kelly_scale: float = 0.5,
        erp_weight: float = 0.4,
        regime_sharpes: dict[str, float] | None = None,
    ): ...
    # regime_sharpes 默认值: {"MID_CYCLE": 1.0, "LATE_CYCLE": 0.2, "BUST": -0.8, "RECOVERY": 1.2}
```

#### `decide()` 返回契约

```
Key                  Type     描述
─────────────────────────────────────────────────────────────────
deployment_state     str      当前部署状态（含惰性过滤）
raw_state            str      本次计算的目标状态（未过滤）
deployment_multiplier float   0.0 / 0.5 / 1.0 / 2.0
readiness_score      float    透传输入
value_score          float    透传输入（即 erp_percentile）
action_required      bool     是否发生状态切换
reason               str      "PACE_SWITCH" 或 "PACE_HOLD"
scores               dict     {"kelly_fraction": f}
barrier              float    当前惰性屏障值
evidence             float    当前累计证据
kelly_fraction       float    原始凯利分数（诊断专用）
─────────────────────────────────────────────────────────────────
```

**关键合同保证**：`deployment_multiplier` 必须等于 `deployment_multiplier_for_state(deployment_state)`，两者不得自相矛盾。

#### 惰性切换状态机

```
状态: current_state, evidence

每次调用 decide():
  1. 计算 kelly_fraction
  2. raw_state = kelly_fraction_to_deployment_state(kelly_fraction)
  3. barrier = _entropy_barrier(entropy, n_states=4)
  4. if raw_state != current_state:
       evidence += abs(kelly_fraction - prev_fraction_or_0)
       if evidence >= barrier:
         current_state = raw_state
         evidence = 0.0
         switched = True
     else:
       evidence = 0.0
       switched = False
  5. 返回结果 dict
```

---

### 3.3 `kelly_ab_comparison.py` — CLI 契约

```
输入:
  --trace-path     str  execution_trace.csv 路径（必须存在以下列）
                        actual_regime, entropy,
                        prob_MID_CYCLE, prob_LATE_CYCLE,
                        prob_BUST, prob_RECOVERY
                        可选: deployment_state, erp_percentile
  --regime-audit   str  regime_audit.json 路径（默认: src/engine/v11/resources/regime_audit.json）
  --output-dir     str  输出目录（默认: artifacts/kelly_ab）

输出（文件契约）:
  {output_dir}/ab_summary.json   结构见下方
  {output_dir}/ab_report.md      Markdown 报告

ab_summary.json schema:
{
  "{variant_id}": {
    "state_distribution": {"DEPLOY_FAST": 0.xx, ...},
    "switch_rate": 0.xx,
    "regime_alignment": {
      "recovery_fast_rate": 0.xx,
      "bust_pause_rate": 0.xx,
      "mid_base_rate": 0.xx
    },
    "fraction_stats": {
      "mean": 0.xx, "std": 0.xx,
      "min": 0.xx,  "max": 0.xx,
      "p25": 0.xx,  "p75": 0.xx
    }
  }
}
```

---

## 4. 依赖图谱

```
kelly_criterion.py
  └─ numpy (外部)
  └─ [无内部依赖] ← 纯函数层，最底层

kelly_deployment_policy.py
  └─ kelly_criterion.py
  └─ src.models.deployment (只读引用)

kelly_ab_comparison.py
  └─ kelly_criterion.py
  └─ src.models.deployment (只读引用)
  └─ pandas, argparse, json, pathlib (标准/外部)

test_kelly_criterion.py
  └─ kelly_criterion.py
  └─ src.models.deployment (TC-K20)
  └─ pytest

test_kelly_deployment_policy.py
  └─ kelly_deployment_policy.py
  └─ src.models.deployment
  └─ pytest
```

---

## 5. 绝对禁区

| 禁区 | 级别 | 原因 |
|:---|:---|:---|
| `src/engine/v11/signal/deployment_policy.py` | 🔴 绝对禁止修改 | A/B 基准保护 |
| `src/engine/v11/conductor.py` | 🔴 绝对禁止修改 | Scope 边界 |
| `src/engine/v11/resources/regime_audit.json` | 🔴 绝对禁止修改 | 数值源保护 |
| `src/models/deployment.py` | 🔴 绝对禁止修改 | 共享函数契约 |
| 任何现有测试文件 | 🔴 绝对禁止修改 | 测试绿化合规 |
| 使用线性混合代替除法 | 🔴 违反 GEMINI.md Bayesian Integrity Lock | Kelly 数学定义 |

---

## 6. 数值稳定性协议

| 变量 | 处理方式 | 代码位置 |
|:---|:---|:---|
| `entropy` 输入 | `clip(entropy, 0.0, 1.0)` | `compute_kelly_fraction` |
| `erp_percentile` 输入 | `clip(erp_percentile, 0.0, 1.0)` | `compute_kelly_fraction` |
| `variance` 分母 | `max(variance, 1e-6)` | `compute_kelly_fraction` |
| Sharpe 方差返回 | `max(result, 1e-6)` | `compute_regime_sharpe_variance` |
| Kelly Fraction 输出 | `clip(result, -1.0, 1.0)` | `compute_kelly_fraction` |
| `_entropy_barrier` 分母 | `max(1e-6, 1.0 - h)` | `KellyDeploymentPolicy._entropy_barrier` |

---

© 2026 QQQ Entropy AI Governance — True Kelly Architecture v1.0
