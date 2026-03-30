# v11 Acceptance Report

> 日期: 2026-03-30
> 基线: `conductor/tracks/v11/spec.md`

## 1. 验收目标

确认 v11 已经从研究态蓝图收敛为可运行、可解释、可回归的统一架构。

## 2. 验收命令

```bash
pytest tests/unit/engine/v11 -q
pytest tests/integration/engine/v11/test_v11_workflow.py -q
pytest tests/unit/test_main_v11.py -q
pytest tests/unit/test_backtest_v11.py -q
python -m src.backtest --mode v11
```

## 3. 当前参考结果

### 3.1 概率审计

1. `points=31`
2. `top1_accuracy=58.06%`
3. `mean_actual_regime_probability=57.93%`
4. `mean_brier=0.7982`

### 3.2 执行审计

1. `left_escape=PASS`
2. `resurrection=PASS`
3. `lock_days=12`

## 4. 已验证修复

1. `T+1` 锁不再被同日清零。
2. 降级覆写会正确触发 `action_required` 并同步内部 bucket。
3. 单行输入不再因 duplicate index 崩溃。
4. 代理字段会降低质量分，不再伪装成完美数据。

## 5. 生产边界

当前 v11 生产边界仅包括：

1. posterior inference
2. entropy-aware sizing
3. behavior constraints
4. CLI / JSON / DB 输出

以下内容明确排除在生产验收之外：

1. 期权凸性变现
2. 跨品种保证金资金池
3. 夸张的 POC 现金曲线
