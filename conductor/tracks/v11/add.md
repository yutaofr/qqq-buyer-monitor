# ADD: QQQ Probabilistic Monitor (v11.0)

> 状态: Accepted Implementation Design
> 关联 SRD: `conductor/tracks/v11/spec.md`
> 日期: 2026-03-30

## 1. High-Level Design

v11 不是“纯状态机”，也不是“纯连续凯利”。

最终实现采用**混合架构**：

1. 上游用 Bayesian posterior 表达连续不确定性。
2. 中游用 entropy-aware sizing 生成连续 beta。
3. 下游用 BehavioralGuard 将连续 beta 投影到有限 bucket，并施加行为约束。

拓扑如下：

`Raw Row -> Scrub/Audit -> Adaptive Percentile Features -> PCA/KDE Posterior -> Kill-Switch -> Continuous Sizing -> Behavioral Guard -> Safety Override -> Persist/Render`

## 2. Core Design Choices

### 2.1 Why Posterior Instead of Hard Threshold States

原因：

1. 状态边界在真实市场中并不稳定。
2. 后验分布可以显式表达不确定性。
3. uncertainty 可直接进入 beta shrinkage，而不是靠人工口头解释。

### 2.2 Why Continuous Sizing Before Bucket Mapping

原因：

1. 直接离散状态机会在边界产生跳跃与洗盘。
2. 纯连续输出又无法对齐散户执行摩擦。
3. 先连续后离散，可以同时保留统计平滑性与行为纪律。

### 2.3 Why Dollar Anchor Instead of Current-NAV-Only Ratios

`risk_budget_dollars` 基于 `reference_capital` 与 `current_nav` 的较大者计算。

这样做的目的：

1. 避免亏损后仅因 NAV 缩小而机械失去全部再配置能力。
2. 让回测与实时运行拥有一致的资金语义。

### 2.4 Why Safety Override Runs After Execution Guard

原因：

1. posterior 与 sizing 应先反映“正常世界”的统计判断。
2. 数据质量问题属于执行安全层，不应污染 posterior 本身。
3. 覆写发生后必须回写 guard 状态，避免“显示无需动作但目标 bucket 已变化”的错误。

### 2.5 Why Current Kill-Switch Uses Single Rolling Z-Score

当前实现选择 `60d` rolling z-score + `VIX` 一阶导确认，而不是多锚点复杂门控。

取舍：

1. 参数更少，样本外更稳。
2. 在 2020 高压窗内能够满足 resurrection 验收。
3. 若未来 walk-forward 证据证明双锚点更稳，再升级为下一版，不在当前基线硬塞更多旋钮。

## 3. Module Mapping

### 3.1 `src/engine/v11/signal/data_degradation_pipeline.py`

负责数据清洗、质量计分、代理字段审计、强制降级。

### 3.2 `src/engine/v11/core/feature_library.py`

负责时序特征库、增量注入、stress feature 生成和自适应 percentile 特征。

### 3.3 `src/engine/v11/core/calibration_service.py`

负责：

1. 选择 `_pct` 特征列。
2. 标准化。
3. PCA 降维。
4. 各 regime KDE 训练。

### 3.4 `src/engine/v11/core/bayesian_inference.py`

负责 posterior 推断与 credit-spread prior tension。

### 3.5 `src/engine/v11/core/position_sizer.py`

负责把 posterior 映射为：

1. `raw_target_beta`
2. `target_beta`
3. `risk_budget_dollars`
4. `QQQ / QLD / Cash` 参考路径

### 3.6 `src/engine/v11/signal/behavioral_guard.py`

负责 bucket deadband、结算锁、复活锁、状态同步。

### 3.7 `src/engine/v11/conductor.py`

负责统一 orchestrate 全链路，并对外输出 runtime payload。

## 4. User Entry Alignment

### 4.1 Live Runtime

`python -m src.main --engine v11`

输出：

1. CLI 审计版面
2. JSON surface
3. DB 持久化 blob

### 4.2 Audit Runtime

`python -m src.backtest --mode v11`

输出：

1. posterior 质量指标
2. 2020 高压执行指标
3. 无副作用审计总结

## 5. Rejected Alternatives

### 5.1 纯离散状态机

拒绝原因：边界抖动太大，且无法显式惩罚高 entropy。

### 5.2 纯 Kelly / Markowitz

拒绝原因：输入噪声、样本不稳和散户执行摩擦会让连续最优解在现实里失真。

### 5.3 期权凸性现金放大器

拒绝原因：研究 POC 可做，生产口径不可接受。此前相关报告已归档，不进入 v11 基线。

## 6. Verification Baseline

当前实现验收以以下事实为准：

1. `python -m src.backtest --mode v11`
   `points=31 | top1_accuracy=58.06% | mean_actual_regime_probability=57.93% | mean_brier=0.7982`
2. 同一审计下执行结果：
   `left_escape=PASS | resurrection=PASS | lock_days=12`
3. 单元与集成回归覆盖 degradation、feature library、sizing、behavior guard、main、backtest 入口。
