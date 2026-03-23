# GEMINI.md - QQQ 个人资产配置监控系统 (v6.4)

## 项目综述
`qqq-monitor` 在 v6.4 中从“机构级战略”进化为“个人投资者决策引擎”。它在原有 TAA 镜像技术基础上，引入了以 **30% 最大可承受回撤 (Drawdown Budget)** 为硬约束的动态搜索机制。系统不再使用静态矩阵，而是通过在多个候选比例带（Candidate Bands）之间进行实时回测评分，自动选择最优的 `QQQ:QLD:Cash` 配置。

### 核心架构 (Personal Allocation Logic)
- **Personal Layer (v6.4 New):** 个人资产配置层。基于 SRD-6.4 预设比例带，在 `aggregate()` 运行中执行 **Live Path Candidate Scoring**。
- **Dynamic Selection Engine:** 针对每个市场状态枚举候选配置，通过 mini-backtest 评分（CAGR、MDD、Turnover、Beta Fidelity）选出最优解。
- **30% MDD Hard Constraint:** 所有配置必须服务于长期 30% 回撤预算（AC-5），在回测搜索中剔除 MDD > 30% 的候选。
- **AC-3 NAV Integrity:** 实时审计资产净值完整性，杜绝硬编码占位，确保模拟仓位与现金流严格对齐。
- **Tier 0 (Macro Commander):** 宏观指挥官。通过信用、流动性、融资压力三重确认决定结构性制度。

### 核心数据口径 (SSoT)
- **Net Liquidity:** WALCL - WDTGAL - RRPONTSYD (以 10 亿美元为单位)。
- **Credit Spread:** ICE BofA US High Yield Index OAS (BAMLH0A0HYM2)。
- **ERP (Equity Risk Premium):** (100 / Forward PE) - Real Yield (10Y DFII10)。
- **Beta Fidelity (AC-4):** 跨区间实现贝塔与目标偏差均值必须 $\le 0.05$ (当前实现: 0.0015)。

---

## 运行与操作

### 1. 实时监控与动态配置搜索
```bash
docker-compose run --rm app python -m src.main
```

### 2. 全样本回测与保真度审计 (AC-4)
```bash
docker-compose run --rm backtest
```

### 3. 全量单元/集成测试
```bash
docker-compose run --rm test
```

---

## 质量与合规准则 (Guardrails)
- **AC-5 风险预算:** 任何配置候选若在历史回测中 MDD > 30%，必须被硬约束过滤（除非所有候选均不达标，则取 least bad）。
- **AC-4 Beta 保真性:** 每日 T+0 再平衡确保实际敞口与搜索出的理想模型偏差 $\le 0.05$。
- **AC-3 数据真实性:** NAV 审计必须基于真实持仓计算，严禁使用硬编码 Integrity。
- **持久化审计:** `current_portfolio`、`target_allocation`、`interval_beta_audit` 必须完整入库。
