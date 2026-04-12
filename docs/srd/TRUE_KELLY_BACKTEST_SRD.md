# SRD: True Kelly 历史 PnL 回测与 ERP 修复
# (面向初级 AI Coding Agent 的补充规格书)

> **版本**: v1.0 (Supplementary)
> **状态**: REQUIRED BEFORE PRODUCTION MERGE
> **前提**: `feature/true-kelly-deployment` 分支所有代码已实现且 29/29 测试 GREEN
> **目标 Branch**: `feature/true-kelly-deployment`（在原分支继续）

---

## 0. 问题诊断汇总

### BUG-1: ERP Weight 实验无效

**根因**: `kelly_ab_comparison.py` 中，当 trace 没有 `erp_percentile` 列时，默认填 `0.5`：

```python
# scripts/kelly_ab_comparison.py L49-50
if "erp_percentile" not in df.columns:
    df["erp_percentile"] = 0.5  # ← 导致 value_tilt 永远为 1.0
```

`regime_process_trace.csv` 确实没有 `erp_percentile` 列，所有 ERP weight 实验因此退化为完全相同的结果。

**真实列名确认**: `regime_process_trace.csv` 包含 `entropy`, `deployment_state`, `deployment_multiplier`, `actual_regime`, `prob_*` 系列列，**无 `erp_percentile`**。

### GAP-1: 缺少历史 PnL 对比

当前 A/B 报告仅包含状态分布和 regime 对齐率，**没有**：
- 模拟净值曲线（PnL Curve）
- CAGR / MDD / Sharpe / Sortino
- 交易成本估算（状态切换 8.2% 是否带来过多摩擦）
- Kelly Fraction 时序图

---

## 1. 修复范围（Scope）

### 1.1 你可以修改的文件

- ✅ `scripts/kelly_ab_comparison.py`（修复 ERP 数据源 + 新增 PnL 计算）
- ✅ `scripts/kelly_pnl_backtest.py`（新建，PnL 回测专用脚本）
- ✅ `docker-compose.yml`（末尾追加 `kelly-pnl` service，不修改现有 service）

### 1.2 绝对不可修改

- ❌ `src/engine/v11/core/kelly_criterion.py`（数学核心，AC 已验收）
- ❌ `src/engine/v11/signal/kelly_deployment_policy.py`（接口 AC 已验收）
- ❌ 任何 `tests/` 文件
- ❌ `src/engine/v11/signal/deployment_policy.py`（原始假凯利）

---

## 2. ERP 数据源修复规格

### 2.1 ERP 来源分析

`regime_process_trace.csv` 中没有 `erp_percentile`，但有：

- `actual_regime`：可用来推断 ERP 代理
- `beta_expectation`, `target_beta`, `entropy`

**正确的 ERP 来源**：`artifacts/v12_audit/execution_trace.csv` 中也没有 `erp_percentile`，但主 backtest 通过 `_resolve_erp_percentile()` 计算它，结果被遗弃了（未写入 trace）。

**解决方案**: 在 A/B 脚本中使用 **ERP 代理变量**，而不是依赖一个不存在的列：

用 `target_beta` 作为倒置的 ERP 代理（高 beta 对应低 ERP/贵市场，低 beta 对应高 ERP/便宜市场）：

```python
# 代理关系：target_beta ∈ [0.5, 1.2]
# 映射: erp_percentile = 1.0 - (target_beta - 0.5) / 0.7
# 说明: target_beta=0.5 (防御) → erp_percentile=1.0 (高ERP=便宜)
#       target_beta=1.2 (激进) → erp_percentile=0.0 (低ERP=昂贵)
```

> ⚠️ 注意：这是代理变量，不是真实 ERP 百分位。但它消除了 erp_percentile 固定为 0.5 的问题，让 ERP 权重实验产生差异化结果。

### 2.2 `_load_trace()` 修复规格

```python
def _load_trace(trace_path: str) -> pd.DataFrame:
    df = pd.read_csv(trace_path)
    required = ["actual_regime", "entropy", "prob_MID_CYCLE", "prob_LATE_CYCLE", "prob_BUST", "prob_RECOVERY"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required col: {col}")

    # 修复 BUG-1: 使用 target_beta 代理 erp_percentile
    if "erp_percentile" not in df.columns:
        if "target_beta" in df.columns:
            beta_min = 0.5
            beta_max = 1.2
            beta_norm = (df["target_beta"].clip(beta_min, beta_max) - beta_min) / (beta_max - beta_min)
            # 高 beta = 贵市场 = 低 ERP percentile
            df["erp_percentile"] = (1.0 - beta_norm).clip(0.0, 1.0)
        else:
            # 只有当两者都不存在时才用 0.5
            df["erp_percentile"] = 0.5

    return df
```

---

## 3. PnL 回测规格

### 3.1 核心设计原理

**PnL 模拟逻辑**：使用 `deployment_multiplier` 作为"每日可部署资金比例"的放大器：

```
daily_deploy_fraction = D × deployment_multiplier_today
```

其中 D = 基准日均入场比例（默认 1%）。

**模拟对象**：两条独立的净值曲线：
1. **Pseudo Kelly curve**：使用原 trace 中的 `deployment_multiplier`
2. **True Kelly curve** (最优变体): 使用 `half_erp_*` 的重算 `kelly_deployment_multiplier`

**简化假设**：
- 资金完全在 QQQ 上投入（不区分 QQQ/QLD/Cash bucket）
- 每日入场额 = `base_daily_deploy × deployment_multiplier`
- QQQ 收益使用 trace 中的 `close` 列（直接差分计算日收益率）
- 交易成本摩擦率 = 0.05%（单向），当 `deployment_multiplier` 发生变化时计算

### 3.2 `scripts/kelly_pnl_backtest.py` 规格

```python
"""
Kelly PnL Backtest: True Kelly (half_erp_low/mid/high) vs Pseudo Kelly.

Usage:
    python scripts/kelly_pnl_backtest.py \
        --trace-path artifacts/v14_panorama/mainline/regime_process_trace.csv \
        --regime-audit src/engine/v11/resources/regime_audit.json \
        --output-dir artifacts/kelly_ab

Output:
    artifacts/kelly_ab/pnl_summary.json    -- CAGR/MDD/Sharpe/Sortino/Turnover
    artifacts/kelly_ab/pnl_curves.csv      -- 日期×变体的净值序列
    artifacts/kelly_ab/pnl_report.md       -- 人类可读报告
"""
```

**函数规格**:

```python
def _compute_pnl_curve(
    trace: pd.DataFrame,
    multiplier_col: str,  # "deployment_multiplier" (pseudo) or "{variant}_multiplier" (kelly)
    base_daily_deploy: float = 0.01,  # 1% 基准日均入场
    transaction_cost: float = 0.0005,  # 0.05% 单向
) -> pd.Series:
    """
    模拟净值曲线。

    逻辑:
    1. 起始净值 = 1.0
    2. 每天: 如果 QQQ close 可计算日收益率:
        - daily_return = close_t / close_{t-1} - 1
        - deployed_fraction = base_daily_deploy * deployment_multiplier_t (clip to [0, 1])
        - pnl_contribution = deployed_fraction * daily_return
    3. 状态切换时扣除 transaction_cost
    4. 累积净值: NAV_t = NAV_{t-1} * (1 + pnl_contribution - cost_t)

    参数:
        trace: 包含 'close', multiplier_col, 'date' 的 DataFrame
        multiplier_col: 使用哪一列作为部署乘数
        base_daily_deploy: 基准每日入场比例 (1% = 0.01)
        transaction_cost: 每次状态切换的单向交易成本

    返回:
        pd.Series[float], index=date, 从 1.0 开始的净值序列

    健壮性要求:
        - trace 中可能有 NaN close 值，跳过（return 0 contribution）
        - 第一行没有 daily_return，跳过
        - NAV 不能为负（理论上不会，但 clip 到 0.0）
    """
    ...


def _compute_performance_metrics(
    nav_series: pd.Series,
    risk_free_rate: float = 0.045,
) -> dict:
    """
    从净值序列计算量化性能指标。

    返回 dict 包含:
        cagr: float        -- 年化复合收益率
        max_drawdown: float -- 最大回撤（负数）
        sharpe: float      -- 年化 Sharpe (超额收益/波动率)
        sortino: float     -- 年化 Sortino (超额收益/下行波动率)
        calmar: float      -- CAGR / |max_drawdown|
        total_return: float -- 总收益率

    计算方法:
        - CAGR = (NAV_final / NAV_0)^(252/n_days) - 1
        - daily_returns = NAV_t / NAV_{t-1} - 1
        - Sharpe = mean(daily_excess) / std(daily_returns) * sqrt(252)
        - daily_excess = daily_returns - risk_free_rate/252
        - Sortino 分母只用 downside = returns[returns < 0]
        - MDD: running max minus current / running max
    """
    ...


def main(argv=None):
    """
    主流程:
    1. 加载 trace（复用 kelly_ab_comparison._load_trace）
    2. 计算 True Kelly 所有 half_* 变体的乘数列（复用 _compute_all_variant_decisions）
    3. 对 pseudo_kelly + half_erp_low/mid/high 共 4 条曲线调用 _compute_pnl_curve
    4. 对每条曲线调用 _compute_performance_metrics
    5. 输出 pnl_summary.json, pnl_curves.csv, pnl_report.md
    """
    ...
```

### 3.3 `pnl_report.md` 必须包含的内容

```markdown
# True Kelly PnL Backtest Report

## Performance Summary

| Variant | CAGR | Max DD | Sharpe | Sortino | Calmar | Total Return |
|---------|------|--------|--------|---------|--------|--------------|
| half_erp_low | ... | ... | ... | ... | ... | ... |
| half_erp_mid | ... | ... | ... | ... | ... | ... |
| half_erp_high | ... | ... | ... | ... | ... | ... |
| pseudo_kelly | ... | ... | ... | ... | ... | ... |

## Key Findings

[自动生成，必须包含:]
- 最优 True Kelly 变体名称与指标
- 与 pseudo_kelly 的 CAGR/MDD 差值
- 是否存在 True Kelly 的 MDD 更大（交易频率过高的代价）

## Conclusion

[自动生成，基于数据推导并入建议:]
- 如果 True Kelly Sharpe > pseudo_kelly Sharpe: 推荐并入
- 如果 True Kelly MDD > pseudo_kelly MDD * 1.5: 需要降低 kelly_scale
```

---

## 4. docker-compose 追加 service

在 `docker-compose.yml` **末尾追加**（不修改任何现有 service）：

```yaml
  kelly-pnl:
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
      python scripts/kelly_pnl_backtest.py
      --trace-path artifacts/v14_panorama/mainline/regime_process_trace.csv
      --regime-audit src/engine/v11/resources/regime_audit.json
      --output-dir artifacts/kelly_ab
```

---

## 5. 新增单元测试规格

新建 `tests/unit/engine/v11/test_kelly_pnl.py`（新文件）：

```python
"""TDD tests for Kelly PnL backtest computation."""
import pandas as pd
from scripts.kelly_pnl_backtest import _compute_pnl_curve, _compute_performance_metrics


def test_pnl_flat_market_zero_return():
    """价格不变时，净值接近 1.0（仅扣交易成本）"""
    ...


def test_pnl_rising_market_generates_positive_nav():
    """价格持续上涨时，净值 > 1.0"""
    ...


def test_pnl_higher_multiplier_amplifies_return():
    """更高的 deployment_multiplier 在上涨市场中产生更高净值"""
    ...


def test_performance_metrics_known_steady_return():
    """已知稳定收益率序列 → 验证 CAGR/Sharpe 计算正确性"""
    # 已知: 每天 0.04% 收益, 1年252天
    # expected CAGR ≈ 1.0004^252 - 1 ≈ 10.5%
    ...


def test_max_drawdown_is_correct():
    """已知先涨后跌序列 → 验证 MDD 计算"""
    # NAV: 1.0 → 1.2 → 0.9 → MDD = (0.9-1.2)/1.2 = -25%
    ...
```

---

## 6. TDD 实施顺序

```
Step 1: 先创建 tests/unit/engine/v11/test_kelly_pnl.py（5个测试，全部 FAIL）
Step 2: 实现 scripts/kelly_pnl_backtest.py 中的 _compute_pnl_curve + _compute_performance_metrics
Step 3: pytest test_kelly_pnl.py → 全部 PASS (GREEN)
Step 4: 修复 scripts/kelly_ab_comparison.py 中的 _load_trace ERP bug
Step 5: 实现 kelly_pnl_backtest.main()
Step 6: 追加 docker-compose.yml kelly-pnl service
Step 7: docker-compose run kelly-ab (验证 ERP 变体现在有差异)
Step 8: docker-compose run kelly-pnl (生成 PnL 报告)
Step 9: docker-compose run test (全量回归，确认 0 failures)
```

---

## 7. 验收标准

### AC-6: ERP 实验差异性验证

重跑 `docker-compose run kelly-ab` 后，`ab_summary.json` 中：
```
half_erp_low.regime_alignment ≠ half_erp_mid.regime_alignment ≠ half_erp_high.regime_alignment
```
（ERP weight 现在会产生可测量的分化结果）

### AC-7: PnL 报告生成

```bash
docker-compose run kelly-pnl
# 要求:
# - 0 Python 异常
# - artifacts/kelly_ab/pnl_summary.json 存在且包含4个变体
# - artifacts/kelly_ab/pnl_report.md 包含对比表格
```

### AC-8: PnL 单元测试 GREEN

```bash
docker-compose run test -k test_kelly_pnl
# 要求: 5个测试全部 PASS
```

### AC-9: 全量回归无退化

```bash
docker-compose run test
# 要求: 0 failures, 0 errors
# 包含原有 29 个 Kelly 测试仍然通过
```

---

## 8. 生产并入最终条件

满足以下条件后，`feature/true-kelly-deployment` 可并入 `main`：

| 条件 | 验收命令 |
|:---|:---|
| AC-6: ERP 实验有效 | `docker-compose run kelly-ab` → 变体产生差异结果 |
| AC-7: PnL 报告生成 | `docker-compose run kelly-pnl` → 报告存在 |
| AC-8: PnL 测试 GREEN | `docker-compose run test -k test_kelly_pnl` |
| AC-9: 全量回归 GREEN | `docker-compose run test` |
| PnL 结论支持并入 | Sharpe or Calmar ≥ pseudo_kelly（至少一项不差于基准） |

---

© 2026 QQQ Entropy AI Governance — True Kelly Backtest Supplementary SRD v1.0
