# GEMINI.md - QQQ Bayesian Orthogonal Factor Monitor (v12.0)

## 项目综述
`qqq-monitor` 在 v12.0 中全面进化为“贝叶斯正交因子引擎”。系统通过三层 10 因子的正交矩阵，利用信息熵控制与 Gram-Schmidt 正交化算法实现全天候宏观风险定价。

### 核心架构 (Bayesian Orthogonal Engine)
- **Orthogonal Matrix (v12):** 三层因子架构（贴现层、实体层、情绪层），彻底消除信息近亲繁殖。
- **Gram-Schmidt Engine:** 在线正交化。通过 Expanding Window 残差提取，确保 MOVE 与利差等因子的条件独立。
- **PIT Integrity Layer:** 点时合规层。严格对齐金融 (T+1)、实体 (Release+30d) 与盈利 (MonthEnd+30d) 的物理发布滞后。
- **Shannon Entropy Controller:** 风险调节层。基于后验分布熵值对敞口执行惩罚 (Haircut)，实现信息诚实性。
- **Inertial Beta Mapper:** 决策平滑层。在确保敞口符合贝叶斯期望的前提下，通过惯性机制减少无谓换手。

### 质量与合规准则 (Guardrails)
- **AC-6 PIT 完整性:** 严禁在回测中使用任何形式的未来函数或事后修正数据。必须模拟历史真实可见性。
- **AC-8 10 因子三层正交:** 所有因子必须归属于 Discount, Real Economy 或 Sentiment 层，严禁层间混淆。
- **AC-10 Gram-Schmidt 正交化:** MOVE 与信用利差必须执行残差化处理，以满足朴素贝叶斯的独立性假设。
- **AC-7 熵增诚实性:** 承认高维空间的稀疏性。严禁为追求虚高准确率而下调 `var_smoothing`。
- **AC-3 验证先于定论:** 任何代码变更必须通过 `src.backtest` 的全量 PIT 因果回归审计（Gate 3）。
- **AC-4 意志与行动分离:** 信号接口必须同时包含 `raw_target_beta` 与 `target_beta`，严禁隐藏推断黑盒。

---

## 运行与操作

### 1. 生产运行
```bash
python -m src.main
```

### 2. 性能审计与全量回测 (Fidelity Audit)
```bash
python -m src.backtest --evaluation-start 2010-01-01
```

### 3. 核心测试
```bash
pytest tests/unit/engine/v11 -q
pytest tests/integration/engine/v11 -q
```

---

## 开发与审计入口 (SSoT)
- **数据集 (Macro):** `data/macro_historical_dump.csv` (10-Factor PIT Schema)
- **基准标签 (Regime):** `data/v11_poc_phase1_results.csv`
- **审计档案 (Resources):** `src/engine/v11/resources/regime_audit.json`
- **架构规格:** `docs/V12_ORTHOGONAL_FACTOR_SPEC.md`

