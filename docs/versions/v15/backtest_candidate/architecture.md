# Architecture: True Kelly Historical PnL Extension (v1.0)
> 支撑文档: `TRUE_KELLY_BACKTEST_SRD.md` | 关联 PRD: `PRD.md`

---

## 1. 模块划分

```
scripts/
├── [EXISTING] kelly_ab_comparison.py       # 🔓 修改解锁：仅限加载层的 ERP surrogate_fix
└── [NEW] kelly_pnl_backtest.py             # ✅ 全新：执行 PnL 和指标衍生

tests/
└── unit/
    └── engine/
        └── v11/
            └── [NEW] test_kelly_pnl.py     # ✅ TDD: 量化财务指标计算核验

docker-compose.yml
└── [APPEND] kelly-pnl service              # ✅ 末尾追加，挂载 PNL_backtest
```

---

## 2. 数据流向

```
[ execution_trace.csv ] 
         │      (含 close, actual_regime, target_beta, prob_*, etc.)
         ▼
 ┌───────────────────────────────────────────────┐
 │ _load_trace() 处理层                            │
 │ (解析 target_beta -> 反向插补 erp_percentile) │
 └───────────────────────┬───────────────────────┘
                         │ 
                         ▼
[ _compute_all_variant_decisions() 处理层 ] ---> 各个 Kelly 变体产生的 Deployment 乘数组
                         │
                         ▼
 ┌───────────────────────────────────────────────┐
 │ _compute_pnl_curve() 财务核心                     │
 │ (基于: base_deploy, friction_costs)           │
 └───────────────────────┬───────────────────────┘
                         │
        生成: Dictionary of pd.Series (NAV 时序曲线)
                         │
                         ▼
 ┌───────────────────────────────────────────────┐
 │ _compute_performance_metrics()                │
 │ (输出 CAGR, MDD, Sharpe, Sortino，Calmar)     │
 └───────────────────────┬───────────────────────┘
                         │
   ┌─────────────────────┴─────────────────────┐
   ▼                                           ▼
pnl_summary.json (持久化结构体)              pnl_report.md (推荐报告)
```

---

## 3. 接口契约（API Contracts）

### 3.1 `kelly_ab_comparison.py` — `_load_trace()` 接口升级
- **签名保证**: 一致
- **逻辑更改**: 
  1. 检测 DataFrame 是否缺少 `erp_percentile`。
  2. 如果缺少但具有 `target_beta` 列，使用以下公式填补：
     `beta_norm = (df['target_beta'].clip(0.5, 1.2) - 0.5) / 0.7`
     `df['erp_percentile'] = (1.0 - beta_norm).clip(0.0, 1.0)`
  3. 若两者皆无，后备回落处理为 0.5。

### 3.2 `scripts/kelly_pnl_backtest.py` — 函数接口

#### `_compute_pnl_curve`
```python
def _compute_pnl_curve(
    trace: pd.DataFrame,
    multiplier_col: str, 
    base_daily_deploy: float = 0.01,
    transaction_cost: float = 0.0005,
) -> pd.Series:
    # 状态保证：
    # - 初始 NAV = 1.0
    # - day_t: multiplier_changed ? cost_t = transaction_cost : cost_t = 0.0
    # - PnL_Contrib = (base_daily_deploy * multiplier_t) * Return_t
    # - NAV_t = max(0.0, NAV_t-1 * (1 + PnL_Contrib - cost_t))
    # 返回类型： pd.Series (index=date, values=float NAV)
    pass
```

#### `_compute_performance_metrics`
```python
def _compute_performance_metrics(
    nav_series: pd.Series,
    risk_free_rate: float = 0.045,
) -> dict:
    # CAGR = (NAV_final/NAV_init) ^ (252/Trading_Days) - 1
    # Sharpe = mean_excess_return / std_return * sqrt(252)
    # 约定返回 Keys: ['cagr', 'max_drawdown', 'sharpe', 'sortino', 'calmar', 'total_return']
    pass
```

---

## 4. 绝对禁区

| 禁区 | 级别 | 原因 |
|:---|:---|:---|
| `src/engine/v11/core/kelly_criterion.py` | 🔴 绝对禁止 | 第一阶段计算逻辑已锁定 |
| `src/engine/v11/signal/kelly_deployment_policy.py` | 🔴 绝对禁止 | First-Pass 集成已通过隔离测试 |
| 原有的回测体系和旧版的测试集 | 🔴 绝对禁止 | 不可篡改已固化的 baseline |

---

© 2026 QQQ Entropy AI Governance — True Kelly PnL Architecture v1.0
