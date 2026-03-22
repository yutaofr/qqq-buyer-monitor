# GEMINI.md - QQQ 资产分配监控系统 (v6.2)

## 项目综述
`qqq-monitor` 是一款主权/养老金风格的市场监控与资本分配系统。它不再仅仅寻找买入点，而是通过识别信贷周期转向、流动性引力和融资压力，实现资产负债表级别的风险防御。

### 核心架构 (The Institutional Logic)
- **Tier 0 (Macro Commander - v6.2 Upgrade):** 系统的最高指挥部。通过“信用、流动性、融资压力”三重确认机制执行防御旁路。
    - **L1 (WATCH_DEFENSE):** 信用利差加速度预警。
    - **L2 (DELEVERAGE):** 信用与流动性共振，启动减仓。
    - **L3 (CASH_FLIGHT):** 三重共振危机，强制现金占比 >50%。
- **Portfolio State (存量管理):** 核心新增组件。系统不仅监控流量（买入），更监控存量（现金占比、杠杆率、净敞口）。
- **Tier 1 (Tactical Sentiment):** 追踪 VIX、恐慌贪婪与底背离。在防御状态下受 Tier 0 强力约束。
- **Tier 2 (Market Structure):** 期权墙（Put/Call Walls）与 Volume POC 确认。

### 核心数据口径 (SSoT)
- **Net Liquidity:** WALCL - WDTGAL - RRPONTSYD。
- **Credit Spread:** ICE BofA US High Yield Index OAS (BAMLH0A0HYM2)。
- **Funding Stress:** Chicago Fed NFCI & CPFF。

---

## 运行与操作

### 1. 实时监控流水线
```bash
docker-compose run --rm app python -m src.main
```

### 2. 压力测试与历史仿真 (Institutional Grade)
运行包含宏观注入与 NAV 追踪的全量历史回测：
```bash
docker-compose run --rm backtest python -m src.stress_test_runner
```

### 3. 全量测试回归
```bash
docker-compose run --rm test
```

---

## 质量与合规准则 (Guardrails)
- **叙事红线:** 在任何防御状态下，系统禁止输出“抄底、加仓”等诱导性多头词汇，必须解释为“资产负债表防御”。
- **TDD 强制性:** 所有针对分配逻辑的修改必须通过 `tests/integration/test_triple_confirmation.py`。
- **数据稳健:** FRED 接口必须具备 fallback 到 Chicago Fed NFCI 的鲁棒性。
