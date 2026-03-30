# Implementation Plan: v11 Probabilistic Monitor

> 状态: Executed Baseline
> 日期: 2026-03-30

## 1. 已执行的收敛步骤

1. 修复结算锁被同日清零的问题。
2. 修复数据降级后 `action_required` 与内部状态不同步的问题。
3. 修复单行 DataFrame 输入触发的 duplicate-index / broadcast 崩溃。
4. 将 v11 主链路收敛为：
   `degradation -> adaptive features -> calibration -> posterior -> sizing -> behavior guard -> override`
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
