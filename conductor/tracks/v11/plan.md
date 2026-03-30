# Implementation Plan: v11 Probabilistic Monitor

> 状态: Executed Baseline
> 日期: 2026-03-30

## 1. 已执行的收敛步骤

1. 修复结算锁被同日清零的问题。
2. 修复数据降级后 `action_required` 与内部状态不同步的问题。
3. 将 v11 主链路收敛为：
   `degradation -> adaptive features -> calibration -> posterior -> sizing -> behavior guard -> override`
4. **V11.1 动量集成 (Momentum Integration)**: 
   - 修改 `CalibrationService` 支持 `_momentum` 特征自动筛选。
   - 引入 Howard Marks 评审建议，将“导数”维度引入贝叶斯推断。
   - 通过回测验证 Brier Score 优化率达 42.44%。
   - PCA 载荷平衡审计 (水位 0.24 vs 动量 0.21) 通过。
5. 对齐 `src.main`、`src.backtest`、CLI、DB blob 的 v11 contract。
6. 为 sizing、behavior guard、feature library、degradation、main/backtest 入口补齐回归测试。

## 2. 已落地模块

1. `src/engine/v11/core/position_sizer.py`
2. `src/engine/v11/signal/behavioral_guard.py`
3. `src/engine/v11/conductor.py`
4. `src/main.py --engine v11`
5. `src/backtest.py --mode v11`

## 3. 当前验收口径

1. 概率审计通过。
2. 2020 高压执行审计通过。
3. v11 单元与集成测试通过。

## 4. 后续只保留增量研究

1. walk-forward 再标定
2. 更长历史库的 live refresh
3. kill-switch 多窗口比较实验

这些属于下一阶段优化，不阻塞当前 v11 基线。
