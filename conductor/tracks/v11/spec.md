# SRD: QQQ Probabilistic Monitor (v11.0)

> 版本: v11.0
> 状态: Accepted Production Baseline
> 日期: 2026-03-30
> 适用范围: `src/engine/v11/`、`src/main.py --engine v11`、`src/backtest.py --mode v11`
> 规范优先级: 本文件与 `conductor/tracks/v11/add.md` 为 v11 唯一正式基线

## 1. Purpose

v11 是面向 `QQQ / QLD / Cash` 的**概率优先、抗噪、强行为约束**推荐引擎。

系统边界锁定如下：

1. 输出推荐，不自动执行交易。
2. 一等公民 contract 是 `target_beta`，而不是离散状态名本身。
3. 离散 bucket 只服务于执行摩擦控制与用户行为约束。
4. 生产范围不包含期权凸性、跨品种保证金模拟或“现金核爆”叙事。

## 2. Functional Requirements

### FR-1 概率优先
系统必须先输出 regime posterior，再由 posterior 生成连续目标 beta。

### FR-2 抗噪
系统必须显式处理：

1. 脏数据与幽灵报价。
2. 缺失字段代理填补。
3. 特征历史非平稳。
4. 后验不确定性升高时的自动缩仓。

### FR-3 行为约束
系统必须在连续 sizing 之后施加执行级约束：

1. 死区与 bucket 迟滞。
2. 常规调仓后的 `T+1` 结算锁。
3. Kill-switch 触发后的 `30` 个交易日 resurrection 锁。
4. 单日 beta 变化上限。

### FR-4 美元锚定
风险预算必须锚定到 `reference_capital` 与 `current_nav`，不能只看当前净值百分比。

### FR-5 可解释与可审计
运行结果必须包含：

1. posterior 概率分布。
2. entropy / uncertainty 信息。
3. 参考配置路径。
4. data-quality 审计明细。
5. execution decision 明细。

### FR-6 入口一致性
以下入口必须对齐到同一套 v11 runtime：

1. `python -m src.main --engine v11`
2. `python -m src.backtest --mode v11`
3. `src/output/cli.py`
4. `src/store/db.py`

## 3. Architecture Principles

### P-1 Posterior Before Policy
任何离散 bucket 决策都不得绕过 posterior 直接由阈值状态机产出。

### P-2 Exogenous Memory
分位数记忆衰减必须由外生信用压力驱动，禁止由价格或 VIX 自指驱动。

### P-3 Uncertainty Must Cost Capital
后验 entropy 越高，可分配 beta 必须越低。v11 通过 uncertainty penalty 缩减 raw beta。

### P-4 Behavior Is Downstream
行为守卫是执行层，不是推断层。推断先连续，执行后离散。

### P-5 Safety Overrides Are Authoritative
数据降级覆写与 kill-switch 拥有高于普通 bucket 迁移的优先级。

## 4. Runtime Architecture

生产流水线固定为：

`Raw Data -> DataDegradationPipeline -> FeatureLibraryManager -> CalibrationService -> BayesianInferenceEngine -> DynamicZScoreKillSwitch -> ProbabilisticPositionSizer -> BehavioralGuard -> SignalDegradationOverrider -> CLI/DB`

### 4.1 DataDegradationPipeline

职责：

1. VIX / term structure 物理常识校验。
2. 尖刺清洗。
3. `vix` / `vix3m` 影子代理。
4. 输出 `quality_score` 与 `quality_audit`。

约束：

1. `quality_score < 0.5` 时强制 `CASH`。
2. `0.5 <= quality_score < 0.8` 时禁用 `QLD`。
3. 降级动作必须显式把 `action_required` 置为 `True`。

### 4.2 FeatureLibraryManager + ExogenousMemoryOperator

职责：

1. 维护 v11 时序特征库。
2. 计算以下 stress 特征的自适应分位数：
   `spread_stress`、`liquidity_stress`、`vix_stress`、`drawdown_stress`、`breadth_stress`、`term_structure_stress`
3. 输出 EWMA percentile 与 momentum 特征。

### 4.3 CalibrationService + BayesianInferenceEngine

职责：

1. 使用 percentile 特征做标准化、PCA、KDE。
2. 用 sigmoid credit tension 调整 base priors。
3. 产出五态 posterior：
   `MID_CYCLE`、`BUST`、`CAPITULATION`、`RECOVERY`、`LATE_CYCLE`

### 4.4 DynamicZScoreKillSwitch

职责：

1. 仅在 blackout 环境中工作。
2. 当期限结构 3 日修复动量在滚动窗口中出现显著正向断裂，且 VIX 一阶导转负时触发 resurrection。

### 4.5 ProbabilisticPositionSizer

职责：

1. 将 posterior 映射为 `raw_target_beta`。
2. 使用 normalized entropy 形成 uncertainty penalty。
3. 施加 `max_daily_beta_shift`。
4. 输出美元锚定的 `QQQ / QLD / Cash` 参考路径。

### 4.6 BehavioralGuard

职责：

1. 将连续 beta 映射为 bucket。
2. 管理 `T+1` settlement lock。
3. 管理 `30d` resurrection lock。
4. 保持 bucket deadband，避免日频洗盘。

当前 bucket 边界：

1. `QLD -> QQQ` 当 `target_beta < 0.95`
2. `QQQ -> CASH` 当 `target_beta < 0.45`
3. `QQQ -> QLD` 当 `target_beta > 1.05`
4. `CASH -> QQQ` 当 `target_beta > 0.55`
5. `CASH -> QLD` 当 `target_beta > 1.05`

## 5. Output Contract

v11 runtime 必须输出：

1. `target_beta`
2. `raw_target_beta`
3. `probabilities`
4. `entropy`
5. `signal.target_bucket`
6. `signal.action_required`
7. `signal.lock_active`
8. `target_allocation`
9. `data_quality`
10. `quality_audit`

## 6. Acceptance Criteria

### AC-1 Regression Safety

以下命令必须通过：

1. `pytest tests/unit/engine/v11 -q`
2. `pytest tests/integration/engine/v11/test_v11_workflow.py -q`
3. `pytest tests/unit/test_main_v11.py -q`
4. `pytest tests/unit/test_backtest_v11.py -q`

### AC-2 Probability Audit

`python -m src.backtest --mode v11` 必须输出可复现的概率审计结果，并满足：

1. `top1_accuracy >= 0.50`
2. `mean_actual_regime_probability >= 0.55`
3. `mean_brier <= 0.90`

2026-03-30 参考结果：

1. `points=31`
2. `top1_accuracy=58.06%`
3. `mean_actual_regime_probability=57.93%`
4. `mean_brier=0.7982`

### AC-3 Execution Audit

同一审计必须满足：

1. `2020-03-09` 前已离开 `QLD`
2. `2020-03-17` 至 `2020-03-31` 期间存在 resurrection 命中并返回 `QLD`
3. `lock_days >= 1`

2026-03-30 参考结果：

1. `left_escape=PASS`
2. `resurrection=PASS`
3. `lock_days=12`

### AC-4 Degradation Safety

脏数据注入时：

1. 不得崩溃。
2. 代理字段必须降低质量分。
3. 强制降级必须同步 execution state。

## 7. Documentation Policy

以下文件是研究归档，不是生产规范：

1. `docs/roadmap/QQQ_PCE_SRD_v11.0.md`
2. `docs/roadmap/v11_*report*.md`
3. `docs/roadmap/v11_design_and_execution_plan.md`

生产实现以本文件、ADD、SOP 和 acceptance report 为准。
