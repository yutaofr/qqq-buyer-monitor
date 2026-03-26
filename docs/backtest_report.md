# Linear Pipeline Backtest Report (v8.1, current main)

本报告记录当前 `main` 上的线性决策流水线在 1999-2026 全样本上的最新回测结果。
执行命令：

```bash
docker compose run --rm backtest
```

执行日期：`2026-03-26`

## 双回测审计

生产验收现在分成两条独立审计线，分别对应存量资产 beta 和增量资金部署节奏。

执行命令：

```bash
python scripts/run_signal_acceptance_report.py
```

### 存量 beta 对齐

| 指标 | 当前表现 | 状态 | 说明 |
| :--- | :--- | :--- | :--- |
| Target Beta MAE | `0.0559` | ✅ PASS | 日频期望矩阵对齐误差 |
| Target Beta RMSE | `0.1688` | ✅ PASS | 日频期望矩阵均方误差 |
| Within Tolerance | `88.97%` | ✅ PASS | 目标 beta 贴近率 |
| Beta Floor | `0.5` | ✅ PASS | 底仓约束持续生效 |
| Beta Cap | `1.2` | ✅ PASS | 上限约束持续生效 |

### 增量部署对齐

| 指标 | 当前表现 | 状态 | 说明 |
| :--- | :--- | :--- | :--- |
| Deployment Exact Match | `99.96%` | ✅ PASS | 期望状态完全匹配 |
| Within One Step | `99.99%` | ✅ PASS | 邻近等级匹配率 |
| CRISIS Deployment Breaches | `0` | ✅ PASS | 危机窗口未越级部署 |

## 混合研究回测核心指标

| 指标 | 当前表现 | 状态 | 说明 |
| :--- | :--- | :--- | :--- |
| Tactical Max Drawdown | `-28.2%` | ✅ PASS | 低于 `30%` 风险预算 |
| Baseline DCA Max Drawdown | `-35.1%` | — | 对照组 |
| MDD Improvement | `6.9%` | ✅ PASS | 相对 Baseline DCA 的绝对改善 |
| Realized Beta | `0.19` | ✅ PASS | staged deployment + risk ceiling 后的全样本实现 beta |
| Mean Interval Beta Deviation | `0.0403` | ✅ PASS | AC-4 保真度通过 |
| NAV Integrity | `1.000000` | ✅ PASS | 独立重放一致 |
| Turnover Ratio | `119.58` | ✅ PASS | 仍低于旧版滚动搜索路径的无界抖动风险 |
| RICH_TIGHTENING left-side windows | `647` | ✅ PASS | 证明软约束没有锁死左侧入场 |
| CRISIS deployment breaches | `0` | ✅ PASS | 危机窗口没有高于 `DEPLOY_PAUSE` 的部署状态 |

## 结果解读

### 0. 双回测已对齐

当前 `main` 的验收口径已经分离为：

- `target_beta` 只看存量资产 beta 是否贴近期望矩阵
- `deployment_state` 只看增量资金部署节奏是否贴近期望矩阵

这两条审计线共享同一套生产决策链，但不再混用一个 NAV 结果作为验收标准。

### 1. 回撤预算已满足

当前 main 的 staged deployment 与 Tier-0 / Risk / Deployment 三段式约束已经把全样本最大回撤控制在 `-28.2%`。
这满足了 SDT 中 `TC-BT-003` 对 `MDD <= 30%` 的要求。

### 2. 左侧窗口被保留

`RICH_TIGHTENING left-side windows = 647`，说明在宏观偏紧阶段，只要价格超跌足够深，部署速度仍可从默认 `DEPLOY_SLOW` 提升到 `DEPLOY_BASE` 或更高。
这满足 `TC-BT-001 / AC-15`。

### 3. 危机窗口被锁死

`CRISIS deployment breaches = 0`，说明在 Tier-0=`CRISIS` 时，系统没有出现任何 `DEPLOY_SLOW / BASE / RECOVER / FAST` 的违规部署状态。
这满足 `TC-BT-002 / AC-13`。

### 4. 回测实现已与生产架构对齐

回测主路径已经不再依赖 v6.4 的 nested mini-backtest / rolling oracle。
当前逻辑与生产一致：

```text
Tier-0 -> Risk Controller -> Candidate Registry -> Beta Recommendation
                    \
                     -> Deployment Controller
```

### 5. 图表已同步

当前 DCA timing 图表已刷新到：

- [docs/images/v8.1_dca_performance.png](images/v8.1_dca_performance.png)
- [artifacts/dca_timing_performance.png](../artifacts/dca_timing_performance.png)

## 结论

当前 main 回测已通过：

- spec compliance
- architecture 对齐
- AC-13 / AC-15 / AC-16 / AC-17 / AC-19 相关回测验证
- 全样本 `MDD <= 30%`
