# v11 Black-Box Backtest Audit Report

**Audit Date**: `2026-04-06`  
**Audit Mode**: production `V11Conductor` black-box replay  
**Primary Goal**: 治理 `MID_CYCLE` 引力塌缩、灰犀牛漏报、回测侧数据污染与隐藏参数漂移

## 1. Governance Verdict

本次治理把回测链路重新收口到一条主线：

- 回测默认只重放生产 `V11Conductor`
- 禁止回测侧覆盖 `var_smoothing / posterior_mode / probability_seeder / audit_overrides`
- 缺失价格缓存时默认 fail closed
- 每个回放日保存 runtime forensics，并由回测工件反向引用

这意味着回测不再拥有一套“看上去像生产”的第二实现。

## 2. Root Cause Findings

### 2.1 `MID_CYCLE` gravitational collapse

旧系统的失真来自三层叠加：

1. `anchor_likelihood_floor=0.01` 对稳定市况下的 `MID_CYCLE` 有硬编码托底。  
2. `transition_weight=0.55` 且惯性高达 `0.85`，使先验像泥地拖拉机一样转不动身。  
3. `price_topology` 只做后置线性 blend，2018Q4 这类价格先崩、信用后滞后的灰犀牛场景里，宏观 `MID_CYCLE` 概率把价格信号淹没了。

### 2.2 Beta kinetic friction

旧版 `InertialBetaMapper` 同时做了两件互相冲突的事：

- 熵高时把跳转阈值抬得极高
- 熵高时又把每日动量更新压得很小

结果是 beta 会在 `0.75` 左右来回横跳，但迟迟无法有效切换到 `0.5` 防御位。

### 2.3 Data leakage / backtest pollution

旧回测入口允许：

- 回测自己重写 Bayesian 主流程
- 回测偷偷切换 feature subset / posterior mode / smoothing
- 价格缓存缺失时 live download

这三点都会让“回测结论”与“生产行为”发生结构性背离。

## 3. Implemented Remediation

### 3.1 Black-box backtest contract

- `run_v11_audit()` 现在默认只接受生产链路控制参数
- `use_canonical_pipeline=False` 视为非法
- live price refresh 必须显式提供 pinned `end_date`
- 回测工件新增 `forensic_trace.jsonl` 与 `forensic_snapshot_path`

### 3.2 Posterior / prior / topology governance

- `price_topology` 升级为 **likelihood penalty / veto**
- `MID_CYCLE` anchor 只在更严格的稳定条件下才生效
- runtime prior 从固定混合改成 **stress-aware dynamic blend**
- `transition_weight` 在压力上升时自动衰减

### 3.3 Execution-layer physical repair

- beta inertia 改成 **非对称动力学**
- 去风险路径快于再风险路径
- 低 beta 防御切换不再被高熵锁死
- Mahalanobis guard 数值稳定性增强，降低极端状态漂移

## 4. 2018Q4 Probe Result

使用修复前后的同一生产 conductor 探针，2018Q4 出现了明显改善。

### 修复前

- `MID_CYCLE > 0.75` 占比：`0.8165`
- `beta <= 0.6` 占比：`0.0000`
- 最低 beta：`0.6961`

### 修复后

- `MID_CYCLE > 0.75` 占比：`0.0092`
- `beta <= 0.6` 占比：`0.3853`
- 最低 beta：`0.5073`

### 关键日期

- `2018-12-20`: `stable=BUST`, `beta=0.550`, `prob_BUST=0.873`
- `2018-12-24`: `stable=BUST`, `beta=0.530`, `prob_BUST=0.948`
- `2018-12-26`: `stable=BUST`, `beta=0.525`, `prob_BUST=0.945`
- `2019-01-04`: `stable=BUST`, `beta=0.520`, `prob_BUST=0.972`

结论：灰犀牛治理已经不再依赖“把贝叶斯核调到能看穿黑天鹅”，而是通过 topology coupling + execution constraints 实现了更可解释的防御切换。

## 5. Regression Evidence

已验证：

- `tests/integration/test_era_phase_transitions.py`
- `tests/unit/test_backtest_v11.py`
- `tests/unit/test_backtest_v13_overlay.py`
- `tests/unit/test_web_exporter.py`
- `tests/integration/test_web_alignment.py`

其中 `2020 COVID` 的 `BUST` / `RECOVERY` 动量切换仍保持通过，说明这次治理没有用 2018Q4 定向过拟合换来新的退化。

## 6. Cold Start Policy

生产冷启动不应每次都跑 8 年回演。

当前推荐策略：

- 生产默认读取已校准的 hydrated prior
- 只有当特征契约或先验结构变化时，才重建 hydration
- 回测为每个 walk-forward 窗口创建本地 prior state，不污染生产文件

这比“每次开机先 replay 8 年”更优雅，也更符合 CI / release 工程现实。

## 7. Output Artifacts

认证工件应包含：

- `summary.json`
- `probability_audit.csv`
- `execution_trace.csv`
- `full_audit.csv`
- `forensic_trace.jsonl`
- 回测可视化 PNG

推荐产物目录：

- `artifacts/v11_black_box_audit_2026-04-06/`

## 8. Final Verdict

本次治理的核心成果不是单一参数调优，而是把系统从“回测和生产两套物理宇宙”拉回到一套物理宇宙：

- 生产是唯一真相源
- 回测只允许重放生产
- 诊断链条可追溯
- 2018Q4 的 `MID_CYCLE` 塌缩已被显著压制
- beta 的防御切换不再陷于 `0.75` 平庸平台
