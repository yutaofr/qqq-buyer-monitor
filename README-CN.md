# QQQ Monitor

这是一个面向 `QQQ / QLD / Cash` 的推荐引擎。

当前仓库同时保留两条运行时：

1. 兼容性保留的 `v10` 线性运行时
2. 已收敛为统一基线的 `v11` 概率化运行时

新开发与验收一律以 `v11` 为准。

## 兼容性说明

仓库里仍保留旧版文档与测试约束，相关术语继续有效：

1. 旧版 `Risk Controller` 负责约束 beta 上限与杠杆准入。
2. 旧版 `Deployment Controller` 只管理 **新增现金** 如何进入 `QQQ`。
3. 系统对外仍然保留“只推荐 **组合级目标 beta**”这一核心 contract。

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

运行 v11：

```bash
python -m src.main --engine v11
python -m src.main --engine v11 --json
```

运行 v11 审计：

```bash
python -m src.backtest --mode v11
```

运行 v11 回归：

```bash
pytest tests/unit/engine/v11 -q
pytest tests/integration/engine/v11/test_v11_workflow.py -q
pytest tests/unit/test_main_v11.py -q
pytest tests/unit/test_backtest_v11.py -q
```

## v11 架构

v11 的主链路是：

`原始数据 -> 数据降级审计 -> 自适应分位数特征 -> PCA/KDE 后验概率 -> 熵惩罚连续仓位 -> 行为守卫 -> 安全覆写 -> CLI/DB`

对外 contract 是：

1. `target_beta`
2. posterior 概率分布
3. 执行 bucket
4. 参考 `QQQ / QLD / Cash` 路径
5. 数据质量审计

系统只做推荐，不自动交易。

## 已验证的审计快照

2026-03-30 参考结果：

```text
--- v11 Probabilistic Audit ---
Probability: points=31 | top1_accuracy=58.06% | mean_actual_regime_probability=57.93% | mean_brier=0.7982
Execution:   left_escape=PASS | resurrection=PASS | lock_days=12
```

## 目录说明

1. `src/engine/` 决策逻辑
2. `src/collector/` 数据采集
3. `src/models/` 共享领域模型
4. `src/store/` 持久化
5. `src/output/` CLI 与报告输出
6. `tests/unit/` 与 `tests/integration/`
7. `conductor/tracks/v11/` v11 正式规范
8. `docs/roadmap/` 运维文档、验收报告与研究归档

## 文档分层

v11 正式文档：

1. `conductor/tracks/v11/spec.md`
2. `conductor/tracks/v11/add.md`
3. `conductor/tracks/v11/design_decisions.md`
4. `docs/roadmap/v11_production_sop.md`
5. `docs/roadmap/v11_acceptance_report_2026-03-30.md`

`docs/roadmap/` 下的旧版 `v11_*report*` 文档保留为历史研究材料，不再作为实现依据。
