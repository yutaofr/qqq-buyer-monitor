# GEMINI.md - QQQ Bayesian Probabilistic Monitor (v11.5)

## 项目综述
`qqq-monitor` 在 v11.5 中全面收敛至“贝叶斯全概率引擎”。系统彻底移除了 v8/v9 的硬阈值流水线，采用贝叶斯推断 (Bayesian Inference) 与信息熵控制 (Entropy Controller) 实现风险定价。

### 核心架构 (Bayesian Probabilistic Engine)
- **Probabilistic Core (v11):** 核心推断引擎。通过 GaussianNB 计算宏观状态的后验概率分布。
- **Entropy Controller:** 风险调节层。基于概率分布的 Shannon 熵计算信息不确定性，并对敞口执行惩罚 (Haircut)。
- **Inertial Beta Mapper:** 决策平滑层。在确保敞口符合贝叶斯期望的前提下，通过惯性机制减少换手。
- **Behavioral Guard:** 行为保护层。防止系统在极端不确定性下频繁调仓，确保策略执行的物理可行性。

### 质量与合规准则 (Guardrails)
- **AC-0 无硬编码参数:** 所有决策基准 (Base Betas, Sharpe Ratios) 必须源自 `regime_audit.json` 的实证审计结果。
- **AC-1 因果隔离:** 严禁在特征提取 (ProbabilitySeeder) 或推断过程中引入任何形式的未来函数。
- **AC-2 数值一致性:** 数据管道产出的所有宏观指标必须采用小数单位 (Decimal Normalize)，严禁使用百分点 (Percent Points) 以防止 KDE 溢出。
- **AC-3 验证先于定论:** 任何代码变更必须通过 `src.backtest` 的全量因果回归审计。
- **AC-4 意志与行动分离 (Intent-Action Separation):** 所有对外的信号接口必须同时包含 `raw_target_beta` (原始贝叶斯期望) 与 `target_beta` (经过惯性平滑后的执行目标)，严禁隐藏推断黑盒。
- **AC-5 冷启动智能对齐 (Smart Priming):** 系统在缺失历史执行状态 (T0) 时，必须直接对齐首日原始期望值，严禁使用硬编码默认值 (如 1.0) 产生启动滞后。

---

## 运行与操作

### 1. 生产运行
```bash
python -m src.main
```

### 2. 性能审计与全量回测 (Fidelity Audit)
```bash
python -m src.backtest --evaluation-start 2018-01-01
```

### 3. 核心测试
```bash
pytest tests/unit/engine/v11 -q
pytest tests/integration/engine/v11 -q
```

---

## 开发与审计入口 (SSoT)
- **数据集 (Macro):** `data/macro_historical_dump.csv`
- **基准标签 (Regime):** `data/v11_poc_phase1_results.csv`
- **审计档案 (Resources):** `src/engine/v11/resources/regime_audit.json`
