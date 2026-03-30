# v11 生产运行 SOP

> 版本: 2026-03-30
> 适用入口: `python -m src.main --engine v11`
> 生产基线: `docs/v11_bayesian_production_baseline_2026-03-30.md`
> 存储契约: `docs/v11_runtime_storage_contract_2026-03-30.md`
> 似然审计: `docs/v11_likelihood_audit_2026-03-30.md`

## 1. 执行时点

1. 每个美股交易日收盘后运行一次。
2. 推荐时间窗口：`16:30-17:00 ET`。

## 2. 运行命令

```bash
python -m src.main --engine v11
python -m src.main --engine v11 --json
python -m src.main --engine v11 --json --no-save
```

## 3. GitHub Actions 边界

当前自动化分三层：

1. `ci-v11.yml`：离线确定性验证，负责 lint、v11 tests、audit backtest。
2. `deploy-web.yml`：生产 dashboard export。
3. `discord-signal.yml`：生产 Discord push。

约束：

1. 生产 workflow 不替代 CI。
2. `deploy-web.yml` 与 `discord-signal.yml` 通过共享的 `v11-runtime.yml` 复用同一套 bootstrap。
3. 任何新的生产 workflow 必须先说明它属于验证层还是执行层，禁止混层。

## 4. 当日数据口径

生产运行中真正进入 `V11Conductor` 的核心字段只有：

1. `erp_pct`
2. `real_yield_10y_pct`
3. `credit_spread_bps`
4. `net_liquidity_usd_bn`

运行时还会携带：

1. `reference_capital`
2. `current_nav`
3. `qqq_close`
4. `vix / vix3m`
5. `breadth_proxy`
6. `fear_greed`
7. `drawdown_pct`

其中第 4-7 项主要用于展示、兼容和上层运行输入，不是当前 regime seeder 的生产特征源。

## 5. 每日流水线

### Step 1: 运行时记忆加载

在 CI 中先从 Vercel Storage pull 最小 mutable runtime state：

1. `data/signals.db`
2. `data/macro_historical_dump.csv`
3. `data/v11_prior_state.json`

然后加载 `data/v11_prior_state.json`：

1. base prior
2. last posterior
3. transition prior
4. beta inertia state
5. stable regime state
6. deployment pacing state
7. execution bucket evidence

### Step 2: 生产特征生成

运行 `ProbabilitySeeder`，当前生产特征只有 6 个：

1. `spread_21d`
2. `liquidity_252d`
3. `real_yield_structural_z`
4. `erp_absolute`
5. `spread_absolute`
6. `yield_absolute`

### Step 3: 贝叶斯后验推断

运行 `GaussianNB.predict_proba()`，再由 `BayesianInferenceEngine` 用：

1. training priors
2. runtime priors

做显式重加权，得到最终 posterior。

### Step 4: 双稳态输出

运行：

1. `RegimeStabilizer` 生成 `raw_regime` 与 `stable_regime`
2. `EntropyController` + `InertialBetaMapper` 生成连续 `target_beta`
3. `ProbabilisticDeploymentPolicy` 生成独立的 `deployment_state`

注意：

1. `target_beta` 用于资产组合风险暴露
2. `deployment_state` 用于增量资金买入节奏
3. 二者禁止重新混成一个输出

### Step 5: 执行桶映射

运行 `BehavioralGuard`：

1. 使用自然边界 `0.5 / 1.0`
2. 使用 entropy-aware evidence accumulation
3. 保留 `T+1` settlement lock
4. 输出 `CASH / QQQ / QLD` 执行桶

### Step 6: 持久化与反馈

1. 保存 `SignalResult`
2. 回写 posterior 与 execution state 到 `data/v11_prior_state.json`
3. 追加宏观四因子到 `data/macro_historical_dump.csv`
4. 更新 `data/signals.db`
5. 在 CI 中 push 最小 mutable runtime state
6. 单独上传 `status.json`

## 6. 每日检查清单

1. `quality_score` 是否异常下降。
2. `stable_regime` 是否与 `raw_regime` 出现合理分离，而不是日内来回翻。
3. `deployment_state` 是否与 `target_beta` 被错误地重新耦合。
4. `lock_active` 是否与当日动作一致。
5. posterior 是否出现极端单点塌缩。
6. `target_beta` 是否被 entropy penalty 显著压缩。

## 7. 故障处置

### 场景 A: 宏观输入缺失或 collector 降级

结果：collector 使用中性回退值；`conductor` 仍然必须保持 deterministic。

### 场景 B: posterior 出现数值异常

结果：回退到 runtime priors，不允许输出 NaN posterior。

### 场景 C: 调仓后再次反向信号

结果：`BehavioralGuard` 保持结算锁；若只是边界附近轻微漂移，先累计 evidence，不立刻翻桶。

### 场景 D: Vercel Storage 首跑为空

结果：

1. blob miss 时先退回本地 checked-in seed
2. 若 `data/v11_prior_state.json` 不存在，则从 regime history deterministic bootstrap
3. 若 macro/regime seed 也损坏，才允许 synthetic bootstrap 兜底

## 8. 生产口径声明

以下内容不属于当前生产 SOP：

1. `DataDegradationPipeline`
2. `SignalDegradationOverrider`
3. `HysteresisBetaMapper`
4. 任何基于固定 delta threshold 的旧调参脚本
5. POC 报告中的期权凸性、双桶现金放大与极端资金曲线
