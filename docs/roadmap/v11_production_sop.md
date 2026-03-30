# v11 生产运行 SOP

> 版本: 2026-03-30
> 适用入口: `python -m src.main --engine v11`

## 1. 执行时点

1. 每个美股交易日收盘后运行一次。
2. 推荐时间窗口：`16:30-17:00 ET`。

## 2. 运行命令

```bash
python -m src.main --engine v11
python -m src.main --engine v11 --json
python -m src.main --engine v11 --json --no-save
```

## 3. 当日数据口径

最小必需输入：

1. `QQQ price`
2. `VIX`
3. `VIX3M`
4. `credit_spread_bps`
5. `liquidity_roc_pct_4w`
6. `breadth_proxy`

运行时补充字段：

1. `reference_capital`
2. `current_nav`
3. `drawdown_pct`

## 4. 每日流水线

### Step 1: 数据清洗与质量审计

执行 `DataDegradationPipeline`：

1. 清洗幽灵报价与异常期限结构。
2. 对缺失 `vix / vix3m` 使用代理。
3. 生成 `quality_score` 和 `quality_audit`。

### Step 2: 特征库更新

将当日行追加到 `FeatureLibraryManager`，计算自适应 percentile 特征。

### Step 3: 概率推断

运行 `CalibrationService` 与 `BayesianInferenceEngine`，得到 posterior。

### Step 4: 逆转审计

运行 `DynamicZScoreKillSwitch`，只在 blackout 条件下判断 resurrection。

### Step 5: 连续 sizing

运行 `ProbabilisticPositionSizer`，得到：

1. `raw_target_beta`
2. `target_beta`
3. `risk_budget_dollars`
4. 参考 `QQQ / QLD / Cash`

### Step 6: 行为守卫

运行 `BehavioralGuard`：

1. bucket 迁移
2. `T+1` settlement lock
3. `30d` resurrection lock

### Step 7: 安全覆写

运行 `SignalDegradationOverrider`：

1. `quality < 0.5` 强制 `CASH`
2. `0.5 <= quality < 0.8` 禁用 `QLD`

### Step 8: 渲染与持久化

1. CLI 展示 posterior、bucket、lock、quality audit
2. DB 保存 `SignalResult` 的 v11 surface

## 5. 每日检查清单

1. `quality_score` 是否异常下降。
2. 是否出现 `proxy_fields` 或 `anomalies`。
3. `lock_active` 是否与当日动作一致。
4. posterior 是否出现极端单点塌缩。
5. `target_beta` 是否被 uncertainty penalty 显著压缩。

## 6. 故障处置

### 场景 A: VIX3M 缺失

结果：代理补齐，质量分下降，但系统继续运行。

### 场景 B: VIX 鬼价

结果：标记 anomaly，优先使用代理或前向填充；若关键列仍不可用则强制 `CASH`。

### 场景 C: 调仓后再次反向信号

结果：`BehavioralGuard` 保持结算锁，拒绝同日洗盘。

## 7. 生产口径声明

POC 报告中的期权凸性、双桶现金放大与极端资金曲线不属于当前生产 SOP。
