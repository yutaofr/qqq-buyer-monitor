> [DEPRECATED: LEGACY PRE-V11 CONTEXT]
> 本文档属于 v5.0 及更早时期的硬阈值/分层过滤架构记录，不代表 v11.5 的全概率贝叶斯主链。
> 请勿将本文约束直接用于当前生产实现或发布审计。

# QQQ Buy-Signal Monitor v5.0 - 核心需求与架构概览

## 1. 业务愿景
`qqq-monitor` 旨在为 QQQ ETF 提供一个多维度的、具备宏观风险识别能力的智能买点监控系统。通过整合宏观环境、市场情绪、机构流向和期权市场微观结构，系统能够识别高概率的波段底部，并对系统性崩塌和阴跌陷阱进行有效过滤。

## 2. 核心架构 (四层过滤体系)

### Tier 0: 宏观熔断与环境识别 (Regime Filter)
- **信用利差熔断**: 监控高收益债利差，识别系统性流动性危机 (>500bps 强制静默)。
- **ERP 环境开关**: 基于股权风险溢价 (ERP) 切换防御/激进模式，动态调整触发门槛。

### Tier 1: 情绪与自适应引擎 (Sentiment & Adaptive)
- **自适应阈值**: 基于 VIX 和回撤的 Z-Score 识别市场 Regime (STORM/QUIET)，动态调整评分权重。
- **速度过滤器 (Velocity Filter)**: 区分 **Panic (恐慌杀跌)** 与 **Grind (缩量阴跌)**。
- **核心指标**: 52w 回撤、MA200 偏离、VIX、Fear & Greed、市场广度。

### Tier 1.5: 机构确认与背离红利 (Institutional & Divergence)
- **背离监测**: 价格与广度、价格与 VIX、价格与分析师上修的底背离确认。
- **流向代理**: 利用 FINRA Short Volume 识别机构空头回补与吸筹区域。
- **价值补偿**: 基于 FCF Yield 和 Forward PE 的绝对估值溢价。

### Tier 2: 期权确认与硬约束 (Options Wall)
- **Put Wall 硬否决**: 价格跌破 Put Wall 时，严禁输出买入信号，防止 Delta 对冲引发的踩踏。
- **Gamma Flip 确认**: 识别波动率分水岭，区分收敛与发散行情。

## 3. 三态到五态的演进
系统输出不再仅限于买/卖，而是细化为五种市场状态：
1. **STRONG_BUY**: 多重背离共振下的高置信度买点。
2. **TRIGGERED**: 标准量化买点触发。
3. **WATCH**: 观察区，结构待修复或信号不全。
4. **NO_SIGNAL**: 市场常态或处于熔断/阴跌。
5. **GREEDY**: 极端过热，分批止盈预警。

## 4. 关键技术指标
- **语言**: Python 3.12
- **数据源**: yfinance, FRED, CNN (Scraper)
- **核心算法**: Black-Scholes (Fallback Gamma), Z-Score Stats, Time-Decay Modeling
- **部署**: Docker / Docker Compose
