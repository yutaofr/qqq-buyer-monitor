> [DEPRECATED: LEGACY PRE-V11 CONTEXT]
> 本文档总结 v5.0 时代的交付与硬约束逻辑，属于历史版本材料，不代表 v11.5 的生产基线。
> 当前发布与审计应以 v11.5 文档集为准，而非本文中的阈值式叙事。

# QQQ Buy-Signal Monitor v5.0 - User Stories & Progress

This document summarizes the user stories and technical epics delivered in version 5.0. It builds upon the foundations laid in [v2.0 (Divergence)](./v2_user_stories.md) and [v3.0 (Macro/Fundamentals)](./v3_user_stories.md).

---

## Epic 1: 宏观生存引擎 (Macro Survival Engine / Tier 0)
**状态**: ✅ 已完成 (v5.0)

### US-1.1: 信用利差熔断器
**As a** 系统, **I want** 在信用利差突破 500bps 时强制静默，**so that** 我能在系统性崩盘（如 2008 年）中保护本金，不接下跌初期的飞刀。
*   **实现**: `tier0_macro.py` 中实现了基于 FRED 数据的 `check_macro_regime` 逻辑。

### US-1.2: ERP 动态门槛切换
**As an** 投资者, **I want** 系统能根据股权风险溢价 (ERP) 调整买点灵敏度，**so that** 在低溢价环境下保持警惕，在高溢价（百年大底）时更积极。
*   **实现**: `aggregator.py` 整合了 ERP Regime (Defense / Normal / Aggressive)。

---

## Epic 2: 自适应情绪与速度过滤 (Adaptive Tier 1 & Velocity)
**状态**: ✅ 已完成 (v5.0)

### US-2.1: 区分阴跌与恐慌 (Velocity Filter)
**As a** 交易者, **I want** 系统能识别下行速度，**so that** 避开慢速缩量阴跌 (Grind)，精准捕捉带量恐慌杀跌 (Panic) 后的 V 反转。
*   **实现**: `tier1.py` 的 `calculate_descent_velocity` 模块，并与 `aggregator.py` 动态触发门槛耦合。

### US-2.2: VIX & 回撤 Z-Score 补偿
**As a** 系统, **I want** 在低波动环境下基于历史统计量 (Z-Score) 补偿绝对阈值，**so that** 在安静市场中的微小波动也能触发观察，而不必非要等到绝对值达到高位。
*   **实现**: `tier1.py` 中实现了 VIX/Drawdown 的 Z-Score 梯度。

---

## Epic 3: 机构流向与背离红利 (Institutional Proxy / Tier 1.5)
**状态**: ✅ 已完成 (v5.0)

### US-3.1: FINRA 短线流向代理
**As an** 投资者, **I want** 利用 FINRA 短线成交占比识别机构抛售峰值，**so that** 发现潜在的空头挤压区域。
*   **实现**: `tier1.py` 整合了 `short_vol_ratio` 信号并给予 Bonus 加分。

### US-3.2: 多重底背离聚合
**As a** 波段交易员, **I want** 系统能自动识别价格与广度、VIX、RSI 的多重背离，**so that** 将置信度极高的买点标记为 `STRONG_BUY`。
*   **实现**: `divergence.py` 实现了 5 类背离判定逻辑。

---

## Epic 4: 期权确认与硬约束 (Options Wall / Tier 2)
**状态**: ✅ 已完成 (v5.0)

### US-4.1: Put Wall 绝对防线
**As a** 系统, **I want** 在价格跌破 Put Wall 时一票否决买入信号，**so that** 规避因做市商 Delta 对冲产生的加速下行风险。
*   **实现**: `aggregator.py` 中加入了 `not tier2.support_broken` 作为 TRIGGERED 的硬前置条件。

### US-4.2: Pivot Wall 与 Gamma 识别
**As a** 交易者, **I want** 知道价格是否处于正负 Gamma 区以及 Pivot Wall 状态，**so that** 评估当前波动率环境是否利于持仓。
*   **实现**: `tier2.py` 的 Gamma Flip 计算与 `aggregator.py` 的中文解释构建。

---

## Epic 5: 止盈预警与滞后干预 (Greedy & Hysteresis)
**状态**: ✅ 已完成 (v5.0)

### US-5.1: 极端贪婪止盈 (Greedy Signal)
**As an** 投资者, **I want** 在市场极度过热时收到减仓信号，**so that** 锁定利润并规避后续回撤。
*   **实现**: `aggregator.py` 加入了基于 MA50 偏离与 F&G > 75 的 `GREEDY` 状态。

### US-5.2: 信号防抖 (Schmitt Trigger)
**As a** 系统, **I want** 信号在阈值边缘时有一定的记忆性，**so that** 避免在一天之内频繁切换信号状态，产生交易噪音。
*   **实现**: `aggregator.py` 引入了 `current_triggered_thresh` 与 `current_watch_thresh` 的滞后性调整。
