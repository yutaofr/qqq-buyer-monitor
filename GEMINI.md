# GEMINI.md - QQQ 个人资产配置监控系统 (v6.4)

## 项目综述
`qqq-monitor` 在 v6.4 中从“机构级战略”进化为“个人投资者决策引擎”。它在原有 TAA 镜像技术基础上，引入了以 **30% 最大可承受回撤 (Drawdown Budget)** 为硬约束的动态搜索机制。系统不再使用静态矩阵，而是通过在多个候选比例带（Candidate Bands）之间进行历史回测评分，自动选择最优的 `QQQ:QLD:Cash` 配置。

### 核心架构 (Personal Allocation Logic)
- **Personal Layer (v6.4 New):** 个人资产配置层。基于 SRD-6.4 预设比例带，执行 **Deterministic Candidate Selection**。
- **Candidate Search:** 针对每个市场状态枚举 2-3 个候选配置，并通过回测评分（CAGR、MDD、Turnover、Beta Fidelity）选出最优解。
- **30% MDD Hard Constraint:** 所有配置必须服务于长期 30% 回撤预算，在极端风险下强制 QLD 归零。
- **Tier 0 (Macro Commander):** 宏观指挥官。通过信用、流动性、融资压力三重确认决定结构性制度（Structural Regime）。
- **Effective Exposure Audit:** 实时审计 `Portfolio Reality` (当前持仓) vs `Ideal Model` (搜索出的最优模型)，输出有效敞口偏差。

### 核心数据口径 (SSoT)
- **Net Liquidity:** WALCL - WDTGAL - RRPONTSYD (以 10 亿美元为单位)。
- **Credit Spread:** ICE BofA US High Yield Index OAS (BAMLH0A0HYM2)。
- **ERP (Equity Risk Premium):** (100 / Forward PE) - Real Yield (10Y DFII10)。
- **Beta Fidelity (AC-4):** 跨区间实现贝塔与目标偏差均值必须 $\le 0.05$。

---

## 运行与操作

### 1. 实时监控与配置搜索
```bash
docker-compose run --rm app python -m src.main
```

### 2. 全样本回测与贝塔审计
```bash
docker-compose run --rm backtest
```

### 3. 全量单元/集成测试
```bash
docker-compose run --rm test
```

---

## 质量与合规准则 (Guardrails)
- **30% 回撤预算:** 系统默认配置搜索以个人长期持有为前提，防守状态严禁配置 QLD。
- **Beta 保真性 (AC-4):** 每日 T+0 再平衡确保实际敞口偏差 $\le 0.05$。
- **持久化审计:** `current_portfolio`、`target_allocation` 与 `interval_beta_audit` 必须完整入库。
- **TDD 强制性:** 所有逻辑修改必须通过 `tests/unit/test_backtest_v6_4.py` 及相关套件验证。
