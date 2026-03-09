# QQQ Buy-Signal Monitor v2.0 - 敏捷开发规划 (User Stories & Tasks)

本文档基于 `docs/divergence_features.md` (v2.0 PRD)，将宏观基本面过滤与技术背离特性拆解为可执行的敏捷研发 User Stories 与 Technical Tasks。

---

## Epic 1: 数据基建升级与时序化 (Data Infrastructure Upgrade)

**Epic 描述**: 为支撑“底背离”所需的历史极值对比，以及低频宏观基本面数据的接入，重构当前无状态的单日爬虫逻辑，引入时序化查询能力与低频任务调度。

### User Story 1.1: 现货与情绪数据的时序化支持
> **作为** 量化分析引擎，
> **我想要** 能够查询过去 N 天（如 60 天）的 QQQ 价格、VIX 和市场广度的历史序列，
> **以便于** 计算出前期的波段极值（High/Low），用于做当天的“背离”判定。

**Technical Tasks**:
- [ ] `Task 1.1.1`: 扩展 `src/store/db.py`，增加 `get_historical_series(days: int)` 方法，以 DataFrame 或结构化序列返回过去 N 天的完整因子数据。
- [ ] `Task 1.1.2`: 在 `MarketData` 模型中引入 `history_window` 属性，在程序启动抓取今日数据结束后，一并从本地 DB（或 yfinance 补充补齐）加载近 60 日数据。

### User Story 1.2: 宏观与基本面低频数据采集 (Macro & Fundamentals Scraper)
> **作为** 系统数据采集模块，
> **我想要** 定期（周度/月度）获取美联储信用利差 (Credit Spread)、指数 PE 与 Forward PE，
> **以便于** 将其作为宏观级别的状态（Regime）缓存供高频日度引擎读取，而无需每天去低频 API 浪费请求包。

**Technical Tasks**:
- [ ] `Task 1.2.1`: 创建 `src/collector/macro.py`，集成 FRED API（美联储经济数据），拉取 `BAMLH0A0HYM2` (高收益债信用利差) 的每日/每周数据，处理 T+2 的延迟对齐问题。
- [ ] `Task 1.2.2`: 创建 `src/collector/fundamentals.py`，评估并接入免费或稳定廉价的 API (如 AlphaVantage 或爬取 Invesco QQQ 特定表格) 获取 QQQ 板块级的 Trailing PE 和 Forward PE。
- [ ] `Task 1.2.3`: 设计并实现分离的缓存表 `macro_states`，用于异步落盘并服务于 `main.py` 的主干流程读取。

---

## Epic 2: 技术底背离计算引擎 (Technical Divergence Engine)

**Epic 描述**: 在原有的绝对数值阈值之上，赋予系统捕捉价格创新低但指标拒绝创新低的“背离内能”洞察力，作为强加分项。

### User Story 2.1: 市场广度与恐慌情绪背离判定
> **作为** 交易信号引擎，
> **我想要** 识别出现货价格新低但 VIX 与跌涨比（Breadth）未出新低的“底背离”形态，
> **以便于** 在市场因为惯性下杀但机构做空能量衰竭时，勇敢发出加分的买入信号。

**Technical Tasks**:
- [ ] `Task 2.1.1`: 创建 `src/engine/divergence.py` 核心计算模块。
- [ ] `Task 2.1.2`: 实现 `check_price_breadth_divergence` 函数：对比当前 QQQ 收盘价是否低于过去 60 天波段低点，若是，进一步比对当时的 Breadth 极值与今日 Breadth。
- [ ] `Task 2.1.3`: 实现 `check_price_vix_divergence` 函数：同上逻辑，检测 VIX 的峰值是否在降低。
- [ ] `Task 2.1.4`: 设计背离红利系统 (Bonus Score，如 +15 分)，并在 `Tier1Result` 中新增 `divergence_bonus` 字段承载这些加分。

### User Story 2.2: 传统动能 RSI 辅助背离
> **作为** 交易信号引擎，
> **我想要** 计算大级别的 RSI (如 14日) 并比对历史低点，
> **以便于** 辅助判定单纯动能上的下杀衰竭。

**Technical Tasks**:
- [ ] `Task 2.2.1`: 引入轻量级技术指标库 (如 `pandas-ta` 或纯 `NumPy` 手写)，基于 User Story 1.1 提供的时间序列计算日线 RSI。
- [ ] `Task 2.2.2`: 在 `divergence.py` 中实现 `check_rsi_divergence` 返回 `bool` 及加分值（如 +5 分）。

---

## Epic 3: 宏观与估值防御层 (Macro & Valuation Filter)

**Epic 描述**: 通过引入大级别的宏观与基本面安全垫，防止我们在史诗级大崩盘或“杀估值”熊市中过早接飞刀。

### User Story 3.1: 信用利差熔断器 (Tier-0 Credit Spread Blowout Filter)
> **作为** 系统架构控制器，
> **我想要** 优先检查底层信用管线是否破裂（信用利差垂直狂飙），
> **以便于** 触发 Tier-0 宏观危机熔断开关，一票否决所有的技术面买入信号，保障资金在金融危机初期的绝对安全。

**Technical Tasks**:
- [ ] `Task 3.1.1`: 在 `src/engine/tier0_macro.py` 中实现 `check_macro_regime()`，计算信用利差近期斜率和绝对阈值（如 > 500 bps）。
- [ ] `Task 3.1.2`: 修改 `aggregator.py` 的信号组合入口，如果 Tier-0 报危，直接将输出强制短路为 `NO_SIGNAL` / `CRISIS_WARNING`，并在 explanation 中置顶警告。

### User Story 3.2: 动态基础估值加权 (Forward PE Z-Score Weighting)
> **作为** 系统架构控制器，
> **我想要** 根据当前 QQQ Forward PE 处于历史（如 5/10年）的分位点（Z-Score），
> **以便于** 在极端泡沫期时收紧技术面买点抓取（扣基础分），而在历史性极度便宜的估值坑里放宽买点抓取（加基础分）。

**Technical Tasks**:
- [ ] `Task 3.2.1`: 在 `src/engine/fundamentals.py` 开发 `calculate_pe_zscore(current_pe, hist_pe_series)`。
- [ ] `Task 3.2.2`: 定义估值加权映射矩阵（例如：最低 10% 分位 -> 给 Tier-1 基础分 +10；最高 10% 泡沫区间 -> 扣除 -10 分）。
- [ ] `Task 3.2.3`: 将此估值基准分集成入 `Tier1Result` 的底分逻辑。

---

## Epic 4: 评估与交付体系重构 (Validation & Delivery)

**Epic 描述**: 确保新引擎在复杂的宏观历史走势中有效，并升级 Discord 推送使得新维度数据可视化。

### User Story 4.1: 千禧年双向盲测验证
> **作为** 策略验证者，
> **我想要** 针对 2000 年互联网泡沫（极度高估值）与 2008 年金融海啸（极度宏观信用危机）两段极端历史进行专项回测，
> **以便于** 验证我们在 Epic 3 中开发的防御拦截机制是否能在真实核弹危机下生效。

**Technical Tasks**:
- [ ] `Task 4.1.1`: 更新 `src/backtest.py`，打通历史数据的 FRED API 静态时序文件读取能力（以避免回测时触发几千次远端 API）。
- [ ] `Task 4.1.2`: 运行并输出带/不带宏观防御开关（Tier-0）对比资产净值曲线图表，出具误报率分析报告。

### User Story 4.2: 报警面板可视化升级
> **作为** 最终用户，
> **我想要** 在 Discord 的每日推空中看到独立的【背离奖励分】和【底盘估值/宏观环境】展示，
> **以便于** 直观理解这套新逻辑在背后为我“踩刹车”或“踩油门”的具体原因。

**Technical Tasks**:
- [ ] `Task 4.2.1`: 重构 `src/output/cli.py` 和 JSON 结构，新增 `── Tier-0 宏观与基本面 ──` 展示块。
- [ ] `Task 4.2.2`: 若触发背离，高亮输出“🔥 捕捉到底部动能背离：奖励 +15 分”。
