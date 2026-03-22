# GEMINI.md - QQQ 资产分配监控系统 (v6.3)

## 项目综述
`qqq-monitor` 是一款主权/养老金风格的市场监控与资本分配系统。在 v6.3 中，系统完成了从“信号监控”向“战略资产配置（Strategic Asset Allocation）”的跨越。通过 **TAA Mirroring (战略镜像)** 技术，系统不仅识别风险，更能实时审计并对齐投资组合的风险敞口。

### 核心架构 (Institutional Strategic Logic)
- **Strategic Layer (v6.3 New):** 核心战略层。将市场状态映射至 TAA 矩阵（Cash/QQQ/QLD），并执行 **Daily T+0 Risk Rebalancing**。
- **Tier 0 (Macro Commander):** 三重确认机制（信用、流动性、融资压力）决定结构性制度（Structural Regime）。
    - **L1 (WATCH_DEFENSE):** 信用利差加速度预警。
    - **L2 (DELEVERAGE):** 资产负债表收缩，削减 QLD 敞口。
    - **L3 (CASH_FLIGHT):** 强制现金占比 >50%，对冲极端宏观风险。
- **Portfolio Reality vs. Ideal:** 系统通过 `CurrentPortfolioState` 获取现实快照，通过 `TargetAllocationState` 计算理想模型，实时输出 **Effective Exposure (有效敞口)** 审计。
- **Tier 1 & Tier 2:** 战术情绪与市场结构层，在战略层约束下提供加仓节奏建议。

### 核心数据口径 (SSoT)
- **Net Liquidity:** WALCL - WDTGAL - RRPONTSYD (以 10 亿美元为单位)。
- **Credit Spread:** ICE BofA US High Yield Index OAS (BAMLH0A0HYM2)。
- **ERP (Equity Risk Premium):** (100 / Forward PE) - Real Yield (10Y DFII10)。
- **Beta Fidelity (AC-4):** 跨区间实现贝塔与目标偏差均值必须 $\le 0.05$。

---

## 运行与操作

### 1. 实时监控与再平衡审计
```bash
docker-compose run --rm app python -m src.main
```

### 2. 机构级保真度测试 (AC-4 Audit)
运行包含实现贝塔归因的压力测试：
```bash
docker-compose run --rm backtest python scripts/stress_test_runner.py
```

### 3. 全量单元/集成测试
```bash
docker-compose run --rm test
```

---

## 质量与合规准则 (Guardrails)
- **Beta 保真性:** 系统必须通过每日风险对齐确保实际敞口与 TAA 目标一致，严禁跨日杠杆漂移。
- **持久化审计:** 所有区间贝塔审计数据（`interval_beta_audit`）必须完整落库，确保历史风控可回溯。
- **TDD 强制性:** 所有针对分配逻辑的修改必须通过 `tests/unit/test_backtest_v6_3.py` 的 0.05 偏差闸门。
- **数据稳健:** FRED 接口必须具备 Treasury XML 对 Real Yield 的 Fallback 能力。
