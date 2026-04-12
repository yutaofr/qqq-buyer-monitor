# SRD: True Kelly Criterion for Incremental Deployment Pacing
# (面向初级 AI Coding Agent 的 TDD 实施规格书)

> **版本**: v1.0
> **状态**: APPROVED FOR IMPLEMENTATION
> **作者**: Systems Architect
> **目标 Branch**: `feature/true-kelly-deployment`
> **验收模式**: TDD-First — 必须先通过 `pytest` 全量回归再声明完成

---

## 0. 你是谁 / 你的边界

你是一个 **辅助开发代理 (Engineering Proxy)**。你的职责边界：

- ✅ 创建 `src/engine/v11/core/kelly_criterion.py`（新文件）
- ✅ 创建 `src/engine/v11/signal/kelly_deployment_policy.py`（新文件）
- ✅ 创建 `tests/unit/engine/v11/test_kelly_criterion.py`（新文件）
- ✅ 创建 `tests/unit/engine/v11/test_kelly_deployment_policy.py`（新文件）
- ✅ 在 `docker-compose.yml` 添加 `kelly-ab` service（追加，不修改现有 service）
- ✅ 创建 `scripts/kelly_ab_comparison.py`（新文件）

**永远禁止**：
- ❌ 修改 `src/engine/v11/signal/deployment_policy.py`（原有假凯利保持不变用于 A/B 对比）
- ❌ 修改 `src/engine/v11/conductor.py`（接口独立，不接入 conductor）
- ❌ 修改任何已有测试文件
- ❌ 修改 `regime_audit.json`


---

## 1. 背景：为什么现有实现是"假凯利"

现有 `ProbabilisticDeploymentPolicy._score_states()` 方法使用的是启发式评分函数：

```python
# 这不是凯利准则，这是人工拼凑的分数
raw_scores = {
    "DEPLOY_PAUSE": bust * (1.0 - readiness + h) + late * h,
    "DEPLOY_SLOW": late * (1.0 + h) + bust * (1.0 - readiness),
    "DEPLOY_BASE": mid * (1.0 + value) + conviction * max(0.0, 1.0 - bust - late),
    "DEPLOY_FAST": (recovery + max(0.0, mid_delta) * 1.5) * (readiness + value + conviction + 0.5),
}
```

**问题**: 这些权重是凭感觉设定的，没有数学原理支撑。

---

## 2. 真凯利准则的数学定义

### 2.1 单轮博弈凯利公式

$$f^* = \frac{p \cdot b - (1-p)}{b}$$

其中 $p$ 是获胜概率，$b$ 是赢时赔率。

### 2.2 多状态 Regime 广义凯利

在四 Regime 贝叶斯系统中，每个 Regime 有自己的 Sharpe Ratio（期望收益/风险），凯利分数定义为：

$$f^* = \frac{E[Sharpe] \cdot \text{value\_tilt}}{Var[Sharpe] + H^2}$$

展开各项：

$$E[Sharpe] = \sum_{i \in Regimes} P(i) \cdot Sharpe_i$$

$$Var[Sharpe] = \sum_{i \in Regimes} P(i) \cdot (Sharpe_i - E[Sharpe])^2$$

$$H = \text{normalized\_entropy} \in [0, 1]$$

$$\text{value\_tilt} = 1.0 + (erp\_percentile - 0.5) \cdot w_{erp}$$

- $w_{erp}$ 是 ERP 权重参数（实验参数，见 Section 3.3）
- Value tilt 让高 ERP 百分位（廉价市场）的期望更大，低 ERP（昂贵市场）的期望更小

### 2.3 半凯利 & 四分之一凯利

实际下注比例需要缩放：

$$f_{half} = f^* \times 0.5$$

$$f_{quarter} = f^* \times 0.25$$

### 2.4 连续 Kelly Fraction → 离散部署状态映射

| Kelly Fraction 范围 | 部署状态 | 含义 |
|:---|:---|:---|
| `fraction ≤ 0.0` | `DEPLOY_PAUSE` | 负期望，停止部署新资金 |
| `0.0 < fraction ≤ 0.25` | `DEPLOY_SLOW` | 正期望但低信心，每月定投 |
| `0.25 < fraction ≤ 0.6` | `DEPLOY_BASE` | 正常基准配速 |
| `fraction > 0.6` | `DEPLOY_FAST` | 高信心低熵，加速部署 |

> **注意**: 这些阈值是物理规格，不得随意修改。

---

## 3. 实验参数矩阵

本 SRD 要求实现以下实验变体。变体通过函数参数控制，不是不同类。

### 3.1 Kelly Scale 变体（必须都实现）

| 变体名 | kelly_scale 参数 | 说明 |
|:---|:---|:---|
| `half_kelly` | `0.5` | SRD 标准方案 |
| `quarter_kelly` | `0.25` | 更保守方案 |

### 3.2 ERP Weight 变体（必须都实现）

| 变体名 | erp_weight 参数 | value_tilt 最大幅度 |
|:---|:---|:---|
| `erp_low` | `0.2` | ±0.1 |
| `erp_mid` | `0.4` | ±0.2（基准） |
| `erp_high` | `0.8` | ±0.4 |

### 3.3 全矩阵组合（共 6 个变体）

A/B 对比脚本需要运行以下组合：

| 变体 ID | kelly_scale | erp_weight |
|:---|:---|:---|
| `half_erp_low` | 0.5 | 0.2 |
| `half_erp_mid` | 0.5 | 0.4 |
| `half_erp_high` | 0.5 | 0.8 |
| `quarter_erp_low` | 0.25 | 0.2 |
| `quarter_erp_mid` | 0.25 | 0.4 |
| `quarter_erp_high` | 0.25 | 0.8 |

---

## 4. 文件规格

### 4.1 `src/engine/v11/core/kelly_criterion.py`（新文件）

**功能**: 纯数学计算模块。无副作用，无状态，无 I/O。

**函数规格**:

```python
"""True Kelly Criterion core mathematics for regime-aware deployment sizing."""

from __future__ import annotations

import numpy as np


def compute_regime_expected_sharpe(
    posteriors: dict[str, float],
    regime_sharpes: dict[str, float],
) -> float:
    """
    计算 regime-weighted 期望 Sharpe Ratio。

    E[Sharpe] = Σ P(regime_i) × Sharpe_i

    参数:
        posteriors: 贝叶斯后验概率分布，如 {"MID_CYCLE": 0.6, "BUST": 0.1, ...}
        regime_sharpes: 每个 Regime 的历史 Sharpe 标定值，如 {"MID_CYCLE": 1.0, "BUST": -0.8, ...}

    返回:
        float，范围约 [-0.8, 1.2]（由 regime_sharpes 范围决定）

    健壮性要求:
        - posteriors 中的 regime 如果不在 regime_sharpes 中，跳过（不报错）
        - 空输入返回 0.0
    """
    ...


def compute_regime_sharpe_variance(
    posteriors: dict[str, float],
    regime_sharpes: dict[str, float],
    expected_sharpe: float,
) -> float:
    """
    计算 regime-weighted Sharpe 方差。

    Var[Sharpe] = Σ P(regime_i) × (Sharpe_i - E[Sharpe])²

    参数:
        posteriors: 贝叶斯后验概率分布
        regime_sharpes: 每个 Regime 的 Sharpe 标定值
        expected_sharpe: compute_regime_expected_sharpe 的返回值

    返回:
        float, >= 0.0

    健壮性要求:
        - 最低返回 1e-6，防止除零
    """
    ...


def compute_kelly_fraction(
    *,
    posteriors: dict[str, float],
    regime_sharpes: dict[str, float],
    entropy: float,
    erp_percentile: float,
    kelly_scale: float = 0.5,
    erp_weight: float = 0.4,
) -> float:
    """
    计算最终 Kelly Fraction（已缩放）。

    公式:
        edge = E[Sharpe]
        variance = Var[Sharpe] + entropy²
        value_tilt = 1.0 + (erp_percentile - 0.5) × erp_weight
        raw_kelly = (edge × value_tilt) / max(variance, 1e-6)
        kelly_fraction = clip(raw_kelly × kelly_scale, -1.0, 1.0)

    参数:
        posteriors: 贝叶斯后验概率分布
        regime_sharpes: Regime Sharpe 标定值（来自 regime_audit.json）
        entropy: 归一化 Shannon 熵 [0.0, 1.0]
        erp_percentile: ERP 历史百分位 [0.0, 1.0]，0.5 = 中位数，0.8 = 历史低 ERP（昂贵市场）
        kelly_scale: 缩放因子，0.5=半凯利，0.25=四分之一凯利
        erp_weight: ERP 对 value_tilt 的影响权重

    返回:
        float，范围 [-1.0, 1.0]

    数值稳定性要求:
        - entropy 必须 clip 到 [0.0, 1.0]
        - erp_percentile 必须 clip 到 [0.0, 1.0]
        - 分母必须 max(variance, 1e-6)
        - 最终结果 clip 到 [-1.0, 1.0]
    """
    ...


def kelly_fraction_to_deployment_state(kelly_fraction: float) -> str:
    """
    将连续 Kelly Fraction 映射到离散部署状态。

    映射规则（见 SRD Section 2.4）:
        fraction <= 0.0           → "DEPLOY_PAUSE"
        0.0 < fraction <= 0.25   → "DEPLOY_SLOW"
        0.25 < fraction <= 0.6   → "DEPLOY_BASE"
        fraction > 0.6           → "DEPLOY_FAST"

    返回:
        str，DeploymentState 枚举的字面值之一
    """
    ...


def kelly_fraction_to_deployment_multiplier(kelly_fraction: float) -> float:
    """
    将 Kelly Fraction 映射到 deployment_multiplier（对齐 deployment_multiplier_for_state()）。

    映射规则:
        "DEPLOY_PAUSE" → 0.0
        "DEPLOY_SLOW"  → 0.5
        "DEPLOY_BASE"  → 1.0
        "DEPLOY_FAST"  → 2.0

    实现方式:
        内部调用 kelly_fraction_to_deployment_state() + deployment_multiplier_for_state()
    """
    ...
```

### 4.2 `src/engine/v11/signal/kelly_deployment_policy.py`（新文件）

**功能**: True Kelly 部署决策策略，接口与 `ProbabilisticDeploymentPolicy` 完全兼容。

```python
"""True Kelly Criterion deployment policy for incremental cash pacing."""

from __future__ import annotations

from src.engine.v11.core.kelly_criterion import (
    compute_kelly_fraction,
    kelly_fraction_to_deployment_multiplier,
    kelly_fraction_to_deployment_state,
)
from src.models.deployment import deployment_multiplier_for_state


class KellyDeploymentPolicy:
    """
    基于真实凯利准则的增量资金部署决策策略。

    接口与 ProbabilisticDeploymentPolicy 完全兼容。
    使用数学最优 Kelly Fraction 代替启发式评分。

    关键区别:
        - 假凯利: ad-hoc 评分函数选最高分
        - 真凯利: f* = edge / variance，直接计算最优下注比例

    额外必需参数（decide() 必须接收）:
        regime_sharpes: dict[str, float]  -- 来自 regime_audit.json
        kelly_scale: float                -- 0.5=半凯利, 0.25=四分之一凯利
        erp_weight: float                 -- ERP 对 value_tilt 的权重
    """

    def __init__(
        self,
        *,
        initial_state: str = "DEPLOY_BASE",
        evidence: float = 0.0,
        kelly_scale: float = 0.5,
        erp_weight: float = 0.4,
        regime_sharpes: dict[str, float] | None = None,
    ):
        self.current_state = initial_state
        self.evidence = float(evidence)
        self.kelly_scale = float(kelly_scale)
        self.erp_weight = float(erp_weight)
        # 默认 Sharpe 标定值（与 regime_audit.json 对齐）
        self.regime_sharpes = regime_sharpes or {
            "MID_CYCLE": 1.0,
            "LATE_CYCLE": 0.2,
            "BUST": -0.8,
            "RECOVERY": 1.2,
        }

    def decide(
        self,
        *,
        posteriors: dict[str, float],
        entropy: float,
        readiness_score: float,
        value_score: float,  # 兼容接口，此处即 erp_percentile
        mid_delta: float = 0.0,  # 兼容接口，不使用（凯利公式已内化此信号）
    ) -> dict[str, object]:
        """
        计算 True Kelly 部署决策。

        返回 dict 结构与 ProbabilisticDeploymentPolicy.decide() 完全兼容，
        并添加 kelly_fraction 字段用于诊断和 A/B 对比。

        必须返回以下字段（不得缺失）:
            deployment_state: str        - 当前部署状态
            raw_state: str               - 本次计算的目标状态（未经惰性过滤）
            deployment_multiplier: float - 0.0/0.5/1.0/2.0
            readiness_score: float       - 透传输入（用于 UI 显示）
            value_score: float           - 透传输入（即 erp_percentile）
            action_required: bool
            reason: str                  - "PACE_SWITCH" 或 "PACE_HOLD"
            scores: dict                 - 保留字段，此处存储 {"kelly_fraction": f}
            barrier: float               - 状态切换的惯性屏障（同原 policy）
            evidence: float              - 累计证据
            kelly_fraction: float        - 真凯利分数（诊断专用，新增字段）

        惰性状态切换规则（与原 policy 保持一致）:
            - 计算 kelly_fraction → 确定 raw_state
            - 如果 raw_state != current_state:
                - evidence += abs(kelly_fraction - prev_fraction)   # 积累证据
                - 如果 evidence >= barrier:  切换，重置 evidence=0
            - 否则: evidence = 0
            - barrier = _entropy_barrier(entropy, n_states=4)       # 复用相同公式
        """
        ...

    @staticmethod
    def _entropy_barrier(entropy: float, n_states: int = 4) -> float:
        """
        复用 ProbabilisticDeploymentPolicy._entropy_barrier() 的完全相同逻辑。

        公式: (h / (1 - h)) / n_states
        其中 h = clip(entropy, 0, 0.999)
        """
        h = min(0.999, max(0.0, float(entropy)))
        states = max(1, int(n_states))
        return (h / max(1e-6, 1.0 - h)) / states
```

### 4.3 `tests/unit/engine/v11/test_kelly_criterion.py`（新文件）

**功能**: 数学正确性单元测试。**必须先写测试，后写实现（TDD）。**

以下测试用例是规格，所有测试名称和断言必须完全实现：

```python
"""TDD tests for True Kelly Criterion core mathematics."""

import pytest
from src.engine.v11.core.kelly_criterion import (
    compute_regime_expected_sharpe,
    compute_regime_sharpe_variance,
    compute_kelly_fraction,
    kelly_fraction_to_deployment_state,
    kelly_fraction_to_deployment_multiplier,
)

REGIME_SHARPES = {"MID_CYCLE": 1.0, "LATE_CYCLE": 0.2, "BUST": -0.8, "RECOVERY": 1.2}


# ===========================================================================
# TC-K01 ~ TC-K05: compute_regime_expected_sharpe
# ===========================================================================

def test_k01_pure_mid_cycle_expected_sharpe_equals_mid_sharpe():
    """纯 MID_CYCLE 后验 → 期望 Sharpe = 1.0"""
    posteriors = {"MID_CYCLE": 1.0, "BUST": 0.0, "LATE_CYCLE": 0.0, "RECOVERY": 0.0}
    result = compute_regime_expected_sharpe(posteriors, REGIME_SHARPES)
    assert abs(result - 1.0) < 1e-9


def test_k02_pure_bust_expected_sharpe_equals_bust_sharpe():
    """纯 BUST 后验 → 期望 Sharpe = -0.8"""
    posteriors = {"MID_CYCLE": 0.0, "BUST": 1.0, "LATE_CYCLE": 0.0, "RECOVERY": 0.0}
    result = compute_regime_expected_sharpe(posteriors, REGIME_SHARPES)
    assert abs(result - (-0.8)) < 1e-9


def test_k03_uniform_posteriors_produce_weighted_average_sharpe():
    """均匀后验 → 期望 Sharpe = 均值"""
    posteriors = {"MID_CYCLE": 0.25, "BUST": 0.25, "LATE_CYCLE": 0.25, "RECOVERY": 0.25}
    expected = (1.0 + (-0.8) + 0.2 + 1.2) / 4  # = 0.4
    result = compute_regime_expected_sharpe(posteriors, REGIME_SHARPES)
    assert abs(result - expected) < 1e-9


def test_k04_unknown_regime_in_posteriors_is_silently_ignored():
    """posteriors 中含未标定 Regime → 忽略，不报错"""
    posteriors = {"MID_CYCLE": 0.8, "UNKNOWN_REGIME": 0.2}
    result = compute_regime_expected_sharpe(posteriors, REGIME_SHARPES)
    # 只有 MID_CYCLE=0.8 被计算: 0.8 * 1.0 = 0.8
    assert abs(result - 0.8) < 1e-9


def test_k05_empty_posteriors_return_zero():
    """空后验 → 返回 0.0"""
    result = compute_regime_expected_sharpe({}, REGIME_SHARPES)
    assert result == 0.0


# ===========================================================================
# TC-K06 ~ TC-K08: compute_regime_sharpe_variance
# ===========================================================================

def test_k06_pure_mid_cycle_has_zero_variance():
    """纯 MID_CYCLE 后验 → Sharpe 方差为 0（已知状态没有不确定性）"""
    posteriors = {"MID_CYCLE": 1.0, "BUST": 0.0, "LATE_CYCLE": 0.0, "RECOVERY": 0.0}
    expected_sharpe = compute_regime_expected_sharpe(posteriors, REGIME_SHARPES)
    result = compute_regime_sharpe_variance(posteriors, REGIME_SHARPES, expected_sharpe)
    # 纯确定性分布方差为 0，但函数有 1e-6 保底
    assert result >= 1e-6


def test_k07_uniform_posteriors_produce_positive_variance():
    """均匀后验 → Sharpe 方差 > 0（不同 Sharpe 之间存在分散）"""
    posteriors = {"MID_CYCLE": 0.25, "BUST": 0.25, "LATE_CYCLE": 0.25, "RECOVERY": 0.25}
    expected_sharpe = compute_regime_expected_sharpe(posteriors, REGIME_SHARPES)
    result = compute_regime_sharpe_variance(posteriors, REGIME_SHARPES, expected_sharpe)
    assert result > 0.01  # 不同 Sharpe 之间方差应显著


def test_k08_variance_is_always_non_negative():
    """方差恒 >= 1e-6（数值稳定性保障）"""
    import random
    random.seed(42)
    for _ in range(20):
        probs = [random.random() for _ in range(4)]
        total = sum(probs)
        posteriors = {r: p / total for r, p in zip(REGIME_SHARPES.keys(), probs)}
        expected_sharpe = compute_regime_expected_sharpe(posteriors, REGIME_SHARPES)
        result = compute_regime_sharpe_variance(posteriors, REGIME_SHARPES, expected_sharpe)
        assert result >= 1e-6


# ===========================================================================
# TC-K09 ~ TC-K15: compute_kelly_fraction
# ===========================================================================

def test_k09_pure_recovery_low_entropy_high_erp_produces_fast_deploy_fraction():
    """RECOVERY + 低熵 + 高 ERP → kelly_fraction > 0.6 → DEPLOY_FAST"""
    posteriors = {"RECOVERY": 1.0, "MID_CYCLE": 0.0, "BUST": 0.0, "LATE_CYCLE": 0.0}
    fraction = compute_kelly_fraction(
        posteriors=posteriors,
        regime_sharpes=REGIME_SHARPES,
        entropy=0.05,
        erp_percentile=0.85,
        kelly_scale=0.5,
        erp_weight=0.4,
    )
    # RECOVERY Sharpe=1.2, 低方差, 低熵 → fraction 应 > 0.6
    assert fraction > 0.6, f"Expected fraction > 0.6, got {fraction}"


def test_k10_pure_bust_low_entropy_produces_negative_fraction():
    """BUST + 低熵 → kelly_fraction ≤ 0 → DEPLOY_PAUSE"""
    posteriors = {"BUST": 1.0, "MID_CYCLE": 0.0, "LATE_CYCLE": 0.0, "RECOVERY": 0.0}
    fraction = compute_kelly_fraction(
        posteriors=posteriors,
        regime_sharpes=REGIME_SHARPES,
        entropy=0.1,
        erp_percentile=0.5,
        kelly_scale=0.5,
        erp_weight=0.4,
    )
    # BUST Sharpe=-0.8 → edge 为负 → fraction 为负
    assert fraction <= 0.0, f"Expected fraction <= 0, got {fraction}"


def test_k11_high_entropy_reduces_kelly_fraction():
    """高熵 → 分母增大 → kelly_fraction 更小"""
    posteriors = {"MID_CYCLE": 0.5, "RECOVERY": 0.5}
    low_entropy_fraction = compute_kelly_fraction(
        posteriors=posteriors,
        regime_sharpes=REGIME_SHARPES,
        entropy=0.1,
        erp_percentile=0.5,
        kelly_scale=0.5,
        erp_weight=0.4,
    )
    high_entropy_fraction = compute_kelly_fraction(
        posteriors=posteriors,
        regime_sharpes=REGIME_SHARPES,
        entropy=0.9,
        erp_percentile=0.5,
        kelly_scale=0.5,
        erp_weight=0.4,
    )
    assert high_entropy_fraction < low_entropy_fraction


def test_k12_quarter_kelly_produces_half_of_half_kelly():
    """quarter_kelly = 0.25x 版本的结果应约等于 half_kelly 的一半"""
    posteriors = {"MID_CYCLE": 0.7, "RECOVERY": 0.3}
    half = compute_kelly_fraction(
        posteriors=posteriors,
        regime_sharpes=REGIME_SHARPES,
        entropy=0.3,
        erp_percentile=0.6,
        kelly_scale=0.5,
        erp_weight=0.4,
    )
    quarter = compute_kelly_fraction(
        posteriors=posteriors,
        regime_sharpes=REGIME_SHARPES,
        entropy=0.3,
        erp_percentile=0.6,
        kelly_scale=0.25,
        erp_weight=0.4,
    )
    assert abs(quarter - half / 2.0) < 1e-9, f"Expected quarter={half/2}, got {quarter}"


def test_k13_high_erp_weight_amplifies_value_tilt():
    """erp_weight=0.8 vs 0.2 → 高 ERP 市场中, 高权重产生更高的 kelly_fraction"""
    posteriors = {"MID_CYCLE": 0.8, "RECOVERY": 0.2}
    low_weight = compute_kelly_fraction(
        posteriors=posteriors,
        regime_sharpes=REGIME_SHARPES,
        entropy=0.3,
        erp_percentile=0.8,  # 高 ERP 百分位 = 廉价市场
        kelly_scale=0.5,
        erp_weight=0.2,
    )
    high_weight = compute_kelly_fraction(
        posteriors=posteriors,
        regime_sharpes=REGIME_SHARPES,
        entropy=0.3,
        erp_percentile=0.8,
        kelly_scale=0.5,
        erp_weight=0.8,
    )
    assert high_weight > low_weight


def test_k14_result_is_always_clipped_to_minus1_plus1():
    """返回值恒在 [-1.0, 1.0] 之间"""
    import random
    random.seed(99)
    for _ in range(50):
        probs = [random.random() for _ in range(4)]
        total = sum(probs)
        posteriors = {r: p / total for r, p in zip(REGIME_SHARPES.keys(), probs)}
        fraction = compute_kelly_fraction(
            posteriors=posteriors,
            regime_sharpes=REGIME_SHARPES,
            entropy=random.random(),
            erp_percentile=random.random(),
            kelly_scale=random.choice([0.25, 0.5]),
            erp_weight=random.choice([0.2, 0.4, 0.8]),
        )
        assert -1.0 <= fraction <= 1.0, f"Out of bounds: {fraction}"


def test_k15_erp_at_midpoint_has_neutral_tilt():
    """erp_percentile=0.5 → value_tilt=1.0 → 不放大也不缩小边际效应"""
    posteriors = {"MID_CYCLE": 1.0}
    # 直接计算 edge = 1.0, variance ≈ 1e-6, entropy=0 → variance = 0+0 = 1e-6
    # kelly = (1.0 * 1.0) / 1e-6 * 0.5 → capped at 1.0
    # 我们只验证 erp=0.5 时 value_tilt 不改变符号
    f_at_mid = compute_kelly_fraction(
        posteriors=posteriors,
        regime_sharpes=REGIME_SHARPES,
        entropy=0.0,
        erp_percentile=0.5,
        kelly_scale=0.5,
        erp_weight=0.4,
    )
    assert f_at_mid > 0.0  # 正期望 MID_CYCLE 保持正向


# ===========================================================================
# TC-K16 ~ TC-K19: kelly_fraction_to_deployment_state
# ===========================================================================

@pytest.mark.parametrize("fraction,expected_state", [
    (-0.5, "DEPLOY_PAUSE"),
    (0.0,  "DEPLOY_PAUSE"),
    (0.01, "DEPLOY_SLOW"),
    (0.25, "DEPLOY_SLOW"),
    (0.26, "DEPLOY_BASE"),
    (0.6,  "DEPLOY_BASE"),
    (0.61, "DEPLOY_FAST"),
    (1.0,  "DEPLOY_FAST"),
])
def test_k16_state_mapping_boundary_conditions(fraction, expected_state):
    """边界条件：确保阈值 0.0, 0.25, 0.6 的映射完全正确"""
    assert kelly_fraction_to_deployment_state(fraction) == expected_state


# ===========================================================================
# TC-K20: kelly_fraction_to_deployment_multiplier
# ===========================================================================

def test_k20_multiplier_aligns_with_deployment_multiplier_for_state():
    """multiplier 函数的返回值必须与 deployment_multiplier_for_state() 完全一致"""
    from src.models.deployment import deployment_multiplier_for_state
    for fraction, expected_state in [
        (-1.0, "DEPLOY_PAUSE"),
        (0.1,  "DEPLOY_SLOW"),
        (0.4,  "DEPLOY_BASE"),
        (0.9,  "DEPLOY_FAST"),
    ]:
        expected_mult = deployment_multiplier_for_state(expected_state)
        actual_mult = kelly_fraction_to_deployment_multiplier(fraction)
        assert actual_mult == expected_mult, f"fraction={fraction}: expected {expected_mult}, got {actual_mult}"
```

### 4.4 `tests/unit/engine/v11/test_kelly_deployment_policy.py`（新文件）

```python
"""TDD tests for KellyDeploymentPolicy interface compliance and behavior."""

import pytest
from src.engine.v11.signal.kelly_deployment_policy import KellyDeploymentPolicy

REGIME_SHARPES = {"MID_CYCLE": 1.0, "LATE_CYCLE": 0.2, "BUST": -0.8, "RECOVERY": 1.2}


# ===========================================================================
# TC-P01: 接口兼容性验证 (Interface Compliance)
# ===========================================================================

def test_p01_decide_returns_all_required_keys():
    """decide() 必须返回与 ProbabilisticDeploymentPolicy 兼容的所有 key"""
    policy = KellyDeploymentPolicy(regime_sharpes=REGIME_SHARPES)
    result = policy.decide(
        posteriors={"MID_CYCLE": 0.6, "BUST": 0.1, "LATE_CYCLE": 0.1, "RECOVERY": 0.2},
        entropy=0.4,
        readiness_score=0.7,
        value_score=0.6,
    )
    required_keys = {
        "deployment_state", "raw_state", "deployment_multiplier",
        "readiness_score", "value_score", "action_required",
        "reason", "scores", "barrier", "evidence", "kelly_fraction",
    }
    missing = required_keys - set(result.keys())
    assert not missing, f"Missing required keys: {missing}"


def test_p02_deployment_multiplier_is_consistent_with_deployment_state():
    """deployment_multiplier 必须与 deployment_state 对应（不能自相矛盾）"""
    from src.models.deployment import deployment_multiplier_for_state
    policy = KellyDeploymentPolicy(regime_sharpes=REGIME_SHARPES)
    result = policy.decide(
        posteriors={"MID_CYCLE": 0.7, "RECOVERY": 0.3},
        entropy=0.2,
        readiness_score=0.8,
        value_score=0.7,
    )
    expected_mult = deployment_multiplier_for_state(result["deployment_state"])
    assert result["deployment_multiplier"] == expected_mult


# ===========================================================================
# TC-P03: 行为合规性验证 (Behavioral Compliance)
# ===========================================================================

def test_p03_pure_bust_low_entropy_leads_to_pause():
    """BUST 主导 + 低熵 → DEPLOY_PAUSE（负期望强信号）"""
    policy = KellyDeploymentPolicy(
        regime_sharpes=REGIME_SHARPES,
        kelly_scale=0.5,
        erp_weight=0.4,
    )
    # 首次调用 initial_state=DEPLOY_BASE → 如果 PAUSE 信号足够强，应切换
    # 为了确保切换发生，直接设 initial 为 DEPLOY_PAUSE
    policy.current_state = "DEPLOY_PAUSE"
    result = policy.decide(
        posteriors={"BUST": 0.95, "MID_CYCLE": 0.05, "LATE_CYCLE": 0.0, "RECOVERY": 0.0},
        entropy=0.05,
        readiness_score=0.1,
        value_score=0.2,
    )
    assert result["deployment_state"] == "DEPLOY_PAUSE"
    assert result["kelly_fraction"] <= 0.0


def test_p04_pure_recovery_low_entropy_leads_to_fast():
    """RECOVERY 主导 + 低熵 + 高 ERP → DEPLOY_FAST（强正期望信号）"""
    policy = KellyDeploymentPolicy(
        initial_state="DEPLOY_FAST",
        regime_sharpes=REGIME_SHARPES,
        kelly_scale=0.5,
        erp_weight=0.4,
    )
    result = policy.decide(
        posteriors={"RECOVERY": 0.95, "MID_CYCLE": 0.05, "BUST": 0.0, "LATE_CYCLE": 0.0},
        entropy=0.05,
        readiness_score=0.9,
        value_score=0.85,
    )
    assert result["deployment_state"] == "DEPLOY_FAST"
    assert result["kelly_fraction"] > 0.6


def test_p05_high_entropy_prevents_fast_deploy():
    """高熵（0.95）下，即使 RECOVERY 主导，方差膨胀也会压缩 kelly_fraction"""
    policy = KellyDeploymentPolicy(
        initial_state="DEPLOY_FAST",
        regime_sharpes=REGIME_SHARPES,
        kelly_scale=0.5,
        erp_weight=0.4,
    )
    result_low_entropy = policy.decide(
        posteriors={"RECOVERY": 0.9, "MID_CYCLE": 0.1},
        entropy=0.05,
        readiness_score=0.8,
        value_score=0.7,
    )
    result_high_entropy = policy.decide(
        posteriors={"RECOVERY": 0.9, "MID_CYCLE": 0.1},
        entropy=0.95,
        readiness_score=0.8,
        value_score=0.7,
    )
    # 高熵下 kelly_fraction 应更小
    assert result_high_entropy["kelly_fraction"] < result_low_entropy["kelly_fraction"]


def test_p06_quarter_kelly_produces_smaller_fraction_than_half_kelly():
    """quarter_kelly 实例的 kelly_fraction 应约为 half_kelly 的一半"""
    posteriors = {"MID_CYCLE": 0.6, "RECOVERY": 0.4}
    half = KellyDeploymentPolicy(
        initial_state="DEPLOY_BASE", regime_sharpes=REGIME_SHARPES, kelly_scale=0.5
    )
    quarter = KellyDeploymentPolicy(
        initial_state="DEPLOY_BASE", regime_sharpes=REGIME_SHARPES, kelly_scale=0.25
    )
    r_half = half.decide(posteriors=posteriors, entropy=0.3, readiness_score=0.7, value_score=0.6)
    r_quarter = quarter.decide(posteriors=posteriors, entropy=0.3, readiness_score=0.7, value_score=0.6)

    assert abs(r_quarter["kelly_fraction"] - r_half["kelly_fraction"] / 2.0) < 1e-9


def test_p07_action_required_and_reason_are_consistent():
    """action_required=True 时 reason 必须是 'PACE_SWITCH'"""
    policy = KellyDeploymentPolicy(
        initial_state="DEPLOY_PAUSE",  # 从 PAUSE 开始，给 FAST 信号
        regime_sharpes=REGIME_SHARPES,
        kelly_scale=0.5,
    )
    # 直接注入足够证据让 evidence >= barrier
    policy.evidence = 999.0
    result = policy.decide(
        posteriors={"RECOVERY": 1.0},
        entropy=0.01,
        readiness_score=1.0,
        value_score=1.0,
    )
    if result["action_required"]:
        assert result["reason"] == "PACE_SWITCH"
    else:
        assert result["reason"] == "PACE_HOLD"
```

### 4.5 `scripts/kelly_ab_comparison.py`（新文件）

**功能**: 在历史数据上对比所有 6 个实验变体 + 1 个假凯利基准。

```python
"""
A/B Comparison: True Kelly (6 variants) vs Pseudo Kelly Baseline.

Usage (in container):
    python scripts/kelly_ab_comparison.py \
        --trace-path artifacts/v12_audit/execution_trace.csv \
        --regime-audit src/engine/v11/resources/regime_audit.json \
        --output-dir artifacts/kelly_ab

Output:
    artifacts/kelly_ab/ab_summary.json   -- 机器可读 JSON
    artifacts/kelly_ab/ab_report.md      -- 人类可读 Markdown 对比报告
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from src.engine.v11.core.kelly_criterion import (
    compute_kelly_fraction,
    kelly_fraction_to_deployment_state,
)
from src.models.deployment import deployment_multiplier_for_state

# 实验矩阵
VARIANTS = [
    {"id": "half_erp_low",     "kelly_scale": 0.5,  "erp_weight": 0.2},
    {"id": "half_erp_mid",     "kelly_scale": 0.5,  "erp_weight": 0.4},
    {"id": "half_erp_high",    "kelly_scale": 0.5,  "erp_weight": 0.8},
    {"id": "quarter_erp_low",  "kelly_scale": 0.25, "erp_weight": 0.2},
    {"id": "quarter_erp_mid",  "kelly_scale": 0.25, "erp_weight": 0.4},
    {"id": "quarter_erp_high", "kelly_scale": 0.25, "erp_weight": 0.8},
]

REGIME_ORDER = ["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"]


def _load_trace(trace_path: str) -> pd.DataFrame:
    """
    加载 execution_trace.csv，提取每行的 posterior 概率、entropy、erp 和 actual_regime。

    必须包含以下列（如果不存在则报错）:
        - actual_regime
        - entropy
        - prob_MID_CYCLE, prob_LATE_CYCLE, prob_BUST, prob_RECOVERY
    可选列:
        - deployment_state (假凯利基准)
        - erp_percentile (如果没有则默认 0.5)
    """
    ...


def _compute_all_variant_decisions(
    trace: pd.DataFrame,
    regime_sharpes: dict[str, float],
) -> pd.DataFrame:
    """
    对 trace 的每一行，计算所有 6 个 True Kelly 变体的 kelly_fraction 和 deployment_state。

    返回 DataFrame，列名格式: f"{variant_id}_fraction", f"{variant_id}_state"
    """
    ...


def _compute_metrics(
    trace: pd.DataFrame,
    pseudo_kelly_col: str = "deployment_state",
) -> dict:
    """
    计算每个变体的对比指标:

    1. 部署状态分布 (state_distribution):
       每个状态出现的百分比

    2. 状态切换频率 (switch_rate):
       相邻天之间状态发生变化的比例

    3. Regime-conditioned 部署对齐率 (regime_alignment):
       - RECOVERY 期间 DEPLOY_FAST 比率
       - BUST 期间 DEPLOY_PAUSE 比率
       - MID_CYCLE 期间 DEPLOY_BASE 比率

    4. Kelly Fraction 统计描述 (fraction_stats):
       mean, std, min, max, p25, p75

    返回 dict，key 为 variant_id，value 为指标 dict
    """
    ...


def _render_markdown_report(metrics: dict, output_path: Path) -> None:
    """
    生成 Markdown 对比报告，包含:
    - 对比表格（所有变体 × 所有指标）
    - 推荐方案（基于 Regime 对齐率最高）
    """
    ...


def main(argv=None):
    parser = argparse.ArgumentParser(description="True Kelly vs Pseudo Kelly A/B comparison")
    parser.add_argument("--trace-path", required=True)
    parser.add_argument("--regime-audit", default="src/engine/v11/resources/regime_audit.json")
    parser.add_argument("--output-dir", default="artifacts/kelly_ab")
    args = parser.parse_args(argv)

    with open(args.regime_audit) as f:
        audit = json.load(f)
    regime_sharpes = dict(audit["regime_sharpes"])

    trace = _load_trace(args.trace_path)
    trace = _compute_all_variant_decisions(trace, regime_sharpes)
    metrics = _compute_metrics(trace)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "ab_summary.json").write_text(json.dumps(metrics, indent=2))
    _render_markdown_report(metrics, output_dir / "ab_report.md")
    print(f"[kelly_ab] Report saved to {output_dir}")


if __name__ == "__main__":
    main()
```

### 4.6 `docker-compose.yml`（追加 service，不修改现有内容）

在文件末尾追加以下 service：

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

---

## 5. TDD 实施顺序（必须严格遵守）

```
Step 1: 先创建 test_kelly_criterion.py（完整）
Step 2: 运行 pytest → 确认所有 TC-K01~K20 FAIL（Expected RED）
Step 3: 实现 src/engine/v11/core/kelly_criterion.py
Step 4: 运行 pytest → 确认所有 TC-K* PASS（GREEN）
Step 5: 先创建 test_kelly_deployment_policy.py（完整）
Step 6: 运行 pytest → 确认 TC-P01~P07 FAIL（Expected RED）
Step 7: 实现 src/engine/v11/signal/kelly_deployment_policy.py
Step 8: 运行 pytest → 确认 TC-P* PASS（GREEN）
Step 9: 运行全量回归 pytest tests/ → 确认原有测试无回归（GREEN）
Step 10: 实现 scripts/kelly_ab_comparison.py
Step 11: 追加 docker-compose.yml kelly-ab service
Step 12: 运行 docker-compose run test → 最终验收
```

---

## 6. 验收标准 (Acceptance Criteria)

### AC-1: 全量测试 GREEN
```bash
docker-compose run test
# 要求: 0 failures, 0 errors
```

### AC-2: 数学单元测试 GREEN
所有 TC-K01 ~ TC-K20 通过，无跳过。

### AC-3: 接口兼容性 GREEN
所有 TC-P01 ~ TC-P07 通过。

### AC-4: 原有测试无回归
`test_deployment_policy.py` 中的原有两个测试仍然通过。

### AC-5: A/B 脚本可运行
```bash
docker-compose run kelly-ab
# 要求: 不报错，生成 artifacts/kelly_ab/ab_summary.json 和 ab_report.md
```

---

## 7. 禁止事项（红线）

| 禁止的行为 | 原因 |
|:---|:---|
| 修改 `deployment_policy.py` | 需要保留假凯利用于 A/B 对比 |
| 修改 `conductor.py` | SRD scope 边界 |
| 修改任何现有测试 | 不允许通过修改测试让测试变绿 |
| 使用线性混合代替除法 | 违反真凯利定义（分子/分母） |
| 修改 `regime_audit.json` | 数值源不得由 coding agent 擅自修改 |
| 修改 `deployment_multiplier_for_state()` | 共享函数，不属于本 SRD 范围 |

---

© 2026 QQQ Entropy AI Governance — True Kelly SRD v1.0
