# Linear Pipeline Backtest Report (v8.0)

本报告记录 v8.0 线性决策流水线在 1999-2026 全样本上的回测结果。
执行命令：

```bash
docker compose run --rm backtest
```

执行日期：`2026-03-25`

## 核心指标

| 指标 | v8.0 表现 | 状态 | 说明 |
| :--- | :--- | :--- | :--- |
| Tactical Max Drawdown | `-6.6%` | ✅ PASS | 明显低于 `30%` 风险预算 |
| Baseline DCA Max Drawdown | `-35.1%` | — | 对照组 |
| MDD Improvement | `28.6%` | ✅ PASS | 相对 Baseline DCA 的绝对改善 |
| Realized Beta | `0.04` | ✅ PASS | staged deployment + risk ceiling 后的全样本实现 beta |
| Mean Interval Beta Deviation | `0.0004` | ✅ PASS | AC-4 保真度通过 |
| NAV Integrity | `1.000000` | ✅ PASS | 独立重放一致 |
| Turnover Ratio | `2.13` | ✅ PASS | 显著低于旧版滚动搜索路径 |
| RICH_TIGHTENING left-side windows | `513` | ✅ PASS | 证明软约束没有锁死左侧入场 |
| CRISIS deployment breaches | `0` | ✅ PASS | 危机窗口没有高于 `DEPLOY_PAUSE` 的部署状态 |

## 结果解读

### 1. 回撤预算已满足

v8.0 的 staged deployment 与 Tier-0 / Risk / Deployment 三段式约束已经把全样本最大回撤压到 `-6.6%`。
这满足了 SDT 中 `TC-BT-003` 对 `MDD <= 30%` 的要求。

### 2. 左侧窗口被保留

`RICH_TIGHTENING left-side windows = 513`，说明在宏观偏紧阶段，只要价格超跌足够深，部署速度仍可从默认 `DEPLOY_SLOW` 提升到 `DEPLOY_BASE`。
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

## 结论

v8.0 回测已通过：

- spec compliance
- architecture 对齐
- AC-13 / AC-15 / AC-16 / AC-17 / AC-19 相关回测验证
- 全样本 `MDD <= 30%`
