# v11 Likelihood Audit

> 日期: 2026-03-30
> 主题: 为什么 live likelihood 曾经塌缩到 `MID_CYCLE`
> 相关代码: `src/main.py`, `src/engine/v11/probability_seeder.py`, `src/output/web_exporter.py`

## 1. 结论

2026-03-30 盘后的 `MID_CYCLE 100%` 不是先验库单独导致的。

真正的直接原因是：

1. live collector 返回的是百分数单位
   - `real_yield = 2.13`
   - `ERP = 1.97`
2. v11 训练语料和 seeder 当前假定的是小数单位
   - `real_yield_10y_pct = 0.0213`
   - `erp_pct = 0.0197`
3. 旧代码把 live 值直接按历史小数口径喂给了 seeder
4. 结果 `erp_absolute` 与 `yield_absolute` 直接被 clip 到 `8.0`
5. `GaussianNB` 在极端 OOD 向量上退化为“谁最不不可能”，当日恰好是 `MID_CYCLE`

修正单位后，真实 live posterior 立即从：

- `MID_CYCLE = 100%`

回到：

- `LATE_CYCLE = 99.1%`
- `MID_CYCLE = 0.9%`
- `RECOVERY = 0.02%`

所以这次问题的主因是 **单位错配导致的 likelihood 失真**，不是 prior 库本身。

## 2. 直接证据

### 2.1 旧口径输入

当日 live 导出的宏观量大致为：

- `credit_spread_bps = 342.0`
- `net_liquidity_usd_bn = 5818.972`
- `real_yield = 2.13`
- `ERP = 1.9717`

在旧代码里，这些值直接进入：

- `erp_pct`
- `real_yield_10y_pct`

而训练集里的典型尾值是：

- `erp_pct ≈ 0.048`
- `real_yield_10y_pct ≈ 0.017`

### 2.2 旧口径特征向量

旧口径下重建出的当日 6 因子约为：

- `spread_21d = 3.0536`
- `liquidity_252d = -5.4550`
- `real_yield_structural_z = 15.6479`
- `erp_absolute = 8.0`
- `spread_absolute = -0.08`
- `yield_absolute = 8.0`

对应 `GaussianNB.predict_proba()`：

- `MID_CYCLE = 1.0`
- `LATE_CYCLE ≈ 1.36e-24`
- `RECOVERY ≈ 2.60e-116`
- `BUST ≈ 9.55e-307`

这不是“正常 macro 判断”，而是典型的 out-of-distribution collapse。

### 2.3 修正单位后的特征向量

把 live 值归一到训练基线口径后：

- `erp_pct = 0.0197`
- `real_yield_10y_pct = 0.0213`

同一天重建出的 6 因子变成：

- `spread_21d = 3.0536`
- `liquidity_252d = -5.4550`
- `real_yield_structural_z = -0.5891`
- `erp_absolute = -1.0141`
- `spread_absolute = -0.08`
- `yield_absolute = -0.6850`

对应 `GaussianNB.predict_proba()`：

- `LATE_CYCLE = 0.99998`
- `MID_CYCLE = 0.00002`
- `RECOVERY ≈ 4.34e-10`
- `BUST ≈ 4.27e-15`

这个结果与“当前更像周期末端/下行压力”的直觉一致得多。

## 3. 次级风险：runtime feedback CSV 被写坏

这次审计还发现了第二个独立问题：

- 旧代码把 5 列 `v11` feedback 行直接 append 到 17 列 canonical `data/macro_historical_dump.csv`
- 结果生成了形如：

```text
2026-03-30,1.9717,2.13,342.0,5818.972
```

这样的残缺行

这会在后续日期把：

- `erp_pct`
- `real_yield_10y_pct`
- `credit_spread_bps`
- `net_liquidity_usd_bn`

全部错位污染。

注意：

- 这不是 2026-03-30 当天 `MID_CYCLE 100%` 的直接原因
- 因为当天运行时会排除同日历史行
- 但它会污染下一交易日开始的历史上下文

所以它必须修。

## 4. 本次修复

### 4.1 live 单位归一

`src/main.py` 现在在进入 `V11Conductor` 之前做显式归一：

- `real_yield_pct_points / 100 -> real_yield_10y_pct`
- `erp_pct_points / 100 -> erp_pct`

也就是说：

- collector 层保留“百分数”语义
- v11 seeder/训练层统一使用“小数”语义

### 4.2 macro feedback 改为 full-schema upsert

`data/macro_historical_dump.csv` 不再 append 5 列残缺行，而是：

1. 读取现有 canonical schema
2. 清理明显损坏的非日期行
3. 按 `observation_date` upsert
4. 用 full-width row 写回

这样：

- 不会再破坏 canonical CSV
- 同日重跑也不会继续堆重复脏行

### 4.3 web contract 对齐

`status.json` 和 `index.html` 现在明确区分：

- `stable_regime`
- `raw_regime`
- `deployment_state`
- `deployment_readiness`
- `priors`
- `v11_probabilities`
- `logic_trace`
- `feature_values`

避免把：

- “稳定态”
- “当日 posterior top-1”
- “新增资金节奏”
- “Kelly 就绪度”
混成一个字段。

同时前端必须真正消费 `logic_trace + feature_values`，提供可展开的证据下钻，而不是只把它们停留在导出 JSON 中。

## 5. 运行后验证

修复后真实 live 运行结果：

- `stable_regime = LATE_CYCLE`
- `raw_regime = LATE_CYCLE`
- `target_beta ≈ 0.80x`
- `deployment_state = DEPLOY_SLOW`
- `deployment_readiness ≈ 20.0%`
- `runtime_priors`
  - `MID_CYCLE ≈ 57.6%`
  - `LATE_CYCLE ≈ 16.3%`
  - `BUST ≈ 13.7%`
  - `RECOVERY ≈ 12.3%`
- `posterior`
  - `LATE_CYCLE ≈ 99.1%`
  - `MID_CYCLE ≈ 0.9%`

这再次说明：

1. prior 仍然偏 `MID_CYCLE`
2. 但修正 live 单位后，likelihood 足以把 posterior 拉回 `LATE_CYCLE`
3. 所以当日异常首先是输入口径问题，不是 prior book 本身失控

## 6. 后续建议

1. 对所有 live collector 输出建立显式单位契约
2. 不允许再让训练语料和 live runtime 在 `%` / decimal 间隐式混用
3. 将 `real_yield` 和 6 因子向量纳入 `status.json` 审计面板
4. 对 `macro_historical_dump.csv` 增加 schema 守卫测试，防止残缺行再次混入
