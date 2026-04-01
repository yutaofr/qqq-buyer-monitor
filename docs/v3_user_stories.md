> [DEPRECATED: LEGACY PRE-V11 CONTEXT]
> 本文档属于 v3.0 的 ERP/阈值时代拆解记录，保留作历史追踪，不代表 v11.5 的全概率贝叶斯规范。
> 当前生产实现禁止将本文中的固定阈值逻辑直接回流到主链。

# QQQ Buy-Signal Monitor v3.0 - User Stories & Tasks

This document translates the [v3.0 PRD](./fundamental_macro_v3.md) into actionable Epics, User Stories, and technical tasks for standard GitHub tracking.

---

## Epic 1: 低频宏观态基础设施 (Macro State Data Infrastructure)
**说明**: v3.0 引入了 ERP, FCF Yield, Earnings Revisions 等低频基本面指标，需要构建从数据采集到本地持久化缓存的完整基建体系。

### User Story 1.1: 宏观状态定时任务
**As a** 系统, **I want** 能够每周或每日更新一次低频宏观数据包，**so that** 高频价格引擎不需要每次都发起耗时的基本面请求。
*   **Acceptance Criteria**:
    *   新增宏观采集脚本，能从 YCharts / AlphaVantage / MacroMicro 等替代数据源（或模拟数据）抓取 US10Y 利率、QQQ FCF Yield 和上修分析师比例。
    *   在 SQLite 数据库 `macro_states` 表中扩展字段（`us10y`, `fcf_yield`, `earnings_revisions_breadth`）。

**Tasks**:
- [ ] `Task 1.1.1`: 扩展 `src/store/db.py` 及 `macro_states` 表的 Schema。
- [ ] `Task 1.1.2`: 编写 `src/collector/macro_v3.py`，实现爬取或 API 获取低频指标逻辑。

---

## Epic 2: ERP 时代环境开关 (Regime Switch)
**说明**: 利用股权风险溢价 (ERP = 1/Forward PE - US10Y) 作为系统环境开关，在“防御”与“激进”模式间切换。

### User Story 2.1: 动态阈值漂移系统
**As an** 投资者, **I want** 系统在 ERP < 1% 时变得极度保守，在 ERP > 5% 时变得激进，**so that** 我不会在估值泡沫期接飞刀，且能在百年大底时吃饱。
*   **Acceptance Criteria**:
    *   `src/engine/tier0_macro.py` 中引入 `check_erp_regime` 逻辑。
    *   当处于防守模式时（ERP < 1%），`aggregator.py` 中的 `TRIGGERED` 阈值从 70 提高至 85，或者否决一切不带“底背离”红利的买点。
    *   当处于激进模式时（ERP > 5%），在 CLI 和 Discord 追加输出【百年一遇系统性低估】的高亮标识。

**Tasks**:
- [ ] `Task 2.1.1`: 计算 ERP (基于 v2.0已有的 Forward PE 与新抓取的 US10Y)。
- [ ] `Task 2.1.2`: 在 `aggregator.py` 补充动态阈值的重打分机制。
- [ ] `Task 2.1.3`: 在 `cli.py` 和 JSON 报告中渲染 Regime 状态标识。

---

## Epic 3: FCF 绝对估值地基 (FCF Valuation Baseline)
**说明**: 基于自由现金流收益率 (FCF Yield) 为长线定投赋予无条件的基础加分。

### User Story 3.1: FCF 黄金击球区奖励
**As a** 价值投资者, **I want** 系统能在科技头牌展现出极高现金流回报（FCF Yield > 4.5%）时自动加分，**so that** 我可以提前建仓，不用死等恐慌极值的出现。
*   **Acceptance Criteria**:
    *   在 `src/engine/fundamentals.py` 追加 FCF Bonus 计算。
    *   如果 FCF Yield > 4.5%，则给予 Tier-1 额外 +15 分。
    *   将该得分叠加到 `Tier1Result` 中。

**Tasks**:
- [ ] `Task 3.1.1`: 在 `fundamentals.py` 实现 `calculate_fcf_bonus`。
- [ ] `Task 3.1.2`: 将 FCF 因素汇入 `Tier1Result`，并加入到单元覆盖测试。

---

## Epic 4: 盈利预期底背离 (Earnings Revision Divergence)
**说明**: 利用分析师上修广度（Earnings Revisions Breadth）寻找基本面前置拐点。

### User Story 4.1: 基本面底背离引擎
**As a** 波段交易员, **I want** 系统发现“价格创新低但分析师在默默上调利润预期”时能拉响警报，**so that** 我能精准买在“杀业绩假摔”的深坑里。
*   **Acceptance Criteria**:
    *   在 `src/engine/divergence.py` 增加基于 Earnings Revision 的背离逻辑。
    *   条件：价格跌破近期低点，但 Earnings Revisions Breadth > 50% 且环比改善。
    *   触发该条件且 Tier 2 期权未破位时，产生 `Strong Buy` 顶级标签。

**Tasks**:
- [ ] `Task 4.1.1`: 在 `MarketData` 及回测流程中透传 Revision Breadth 指标。
- [ ] `Task 4.1.2`: 扩展 `divergence.py` 支持 `price_revision` 背离监测 (+20 分)。
- [ ] `Task 4.1.3`: 更新 Aggregator 和 CLI 输出，实现 `Strong Buy` 的视觉呈现。
