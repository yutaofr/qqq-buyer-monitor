# v11 Roadmap

> 更新日期: 2026-03-30
> 状态: Baseline Implemented

## 1. 已完成

### 1.1 架构收敛

已完成从“多份蓝图并存”到单一基线的收敛：

1. SRD/ADD 统一到 `conductor/tracks/v11/`
2. live runtime 统一到 `python -m src.main --engine v11`
3. audit runtime 统一到 `python -m src.backtest --mode v11`

### 1.2 核心执行级修复

已完成：

1. `T+1` 冷却锁生效
2. degradation override 与 execution state 同步
3. duplicate-index 导致的单行崩溃修复
4. 代理字段会真实降低 data quality

### 1.3 统计与行为升级

已完成：

1. posterior-first 推断
2. entropy-aware continuous sizing
3. dollar-anchored risk budget
4. deadband + settlement lock + resurrection lock

## 2. 当前验收事实

`python -m src.backtest --mode v11` 当前参考结果：

1. `points=31`
2. `top1_accuracy=58.06%`
3. `mean_actual_regime_probability=57.93%`
4. `mean_brier=0.7982`
5. `left_escape=PASS`
6. `resurrection=PASS`
7. `lock_days=12`

## 3. 文档分层

### 3.1 规范层

1. `conductor/tracks/v11/spec.md`
2. `conductor/tracks/v11/add.md`
3. `conductor/tracks/v11/design_decisions.md`

### 3.2 运维层

1. `docs/roadmap/v11_production_sop.md`
2. `docs/roadmap/v11_acceptance_report_2026-03-30.md`

### 3.3 研究归档层

以下文档保留，但不再指导实现：

1. `docs/roadmap/QQQ_PCE_SRD_v11.0.md`
2. `docs/roadmap/v11_design_and_execution_plan.md`
3. `docs/roadmap/v11_*report*.md`

## 4. 下一阶段研究

这些任务有价值，但不阻塞当前基线：

1. 更长窗口的 walk-forward 再标定
2. kill-switch 单窗口 vs 多窗口比较
3. live monitoring dashboard
4. 更完整的特征库自动刷新
