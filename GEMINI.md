# GEMINI.md - QQQ 个人资产配置监控系统 (v8.2)

## 项目综述
`qqq-monitor` 在 v8.2 中进化为“个人投资者决策引擎”，采用 **v8.2 线性流水线架构**。它集成了宏观层 (Tier-0)、战术层 (Tier-1) 与市场结构层 (Tier-2)，输出纯净的 Beta 建议与增量资金入场节奏。

### 核心架构 (Personal Allocation Logic)
- **Tier 0 (Macro Commander):** 宏观指挥官。通过信用利差与 ERP 决定结构性制度 (`CRISIS | TRANSITION_STRESS | RICH_TIGHTENING | NEUTRAL | EUPHORIC`)，作为 Beta 上限与入场节奏的顶层约束。
- **Risk Controller:** 风险控制层。基于 Class A 宏观数据与 Tier-0 状态，动态调整风险敞口上限与现金底仓。
- **Deployment Controller:** 资金部署引擎。基于 Class B 战术数据，在满足风险约束的前提下，优化新增资金的入场节奏 (`FAST | BASE | SLOW | PAUSE`)。
- **Search & Recommendation:** 搜索与推荐引擎。在认证候选库中检索符合 Beta 上限的最优配置，输出不含金额的纯净建议。

### 4. Web 分发系统 (Public Distribution)
- **Endpoint**: Vercel Blob 基于边缘存储的静态快照。
- **Governance**: 离散化映射保护 Alpha，3-State 机自愈感知流水线故障。

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
- **持久化审计:** `target_allocation`、`interval_beta_audit` 必须完整入库。
