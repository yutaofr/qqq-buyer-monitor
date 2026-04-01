> [PARALLEL TRACK]
> 本文档描述 allocator-first 并行产品线，不是 v11.5 Bayesian production baseline，也不是当前生产发布判定依据。
> 若进行 v11.5 主链架构审计，请以 `V11_5_EXPERT_SPEC.md`、`architecture.md`、`V11_5_ARCHITECT_MANUAL.md` 与 `v11_bayesian_production_baseline_2026-03-30.md` 为准。

# PRD: QQQ Long-Term Allocation Engine

> 版本: 2026-03 allocator-first refactor
> 状态: Active
> 日期: 2026-03-19

## 1. 产品定义

`qqq-monitor` 已从“买点信号监控器”重构为“长期资金仓位分层引擎”。

核心原则：
- 主输出是仓位动作，不是抄底标签。
- 宏观结构优先于短线情绪。
- 数据不可得时宁可缺失，也不伪造。
- 用户界面必须降低戏剧化表达，避免诱发过度自信。

## 2. 目标

| 编号 | 目标 | 当前解释 |
|---|---|---|
| G1 | 避免宏观流动性失真下的错误加仓 | `CRISIS` 时转入 `RISK_CONTAINMENT` |
| G2 | 区分恐慌超跌与漫长阴跌 | `stress / capitulation / persistence` 分层输出 |
| G3 | 把输出从标签机改成 allocator | 输出 `allocation_state`、tranche、confidence |
| G4 | 明确显示数据质量 | live / cache / stale_days 显式呈现 |

## 3. 决策流水线

### Tier 0: Structural Regime

输入：
- `credit_spread`
- ERP (`1 / forward_pe - real_yield`)

输出：
- `EUPHORIC`
- `RICH_TIGHTENING`
- `NEUTRAL`
- `TRANSITION_STRESS`
- `CRISIS`

作用：
- 决定当前允许的仓位动作上限。

### Tier 1: Tactical Engine

核心输入：
- `drawdown_52w`
- `ma200_deviation`
- `vix`
- `fear_greed`
- `breadth`

公开加法面：
- `stress_score`
- `capitulation_score`
- `persistence_score`
- `short_flow_bonus`

作用：
- 在结构框架内决定应维持定投、仅小幅试探，还是允许提高加仓速度。

### Tier 2: Options Overlay

当前定义：
- 作为软约束层，而不是硬买卖开关。
- 可以降低 tranche、削弱 confidence、延长冷却。
- 不能让兼容 `signal` 比 `allocation_state` 更激进。

## 4. 输出面

### 主输出

| `allocation_state` | 含义 | 用户动作 |
|---|---|---|
| `BASE_DCA` | 常规环境 | 维持基础定投 |
| `SLOW_ACCUMULATE` | 有压力但未到极值 | 仅小幅试探 |
| `FAST_ACCUMULATE` | 中性结构下的明显超跌 / 恐慌 | 允许提高加仓速度 |
| `PAUSE_CHASING` | 价格抬升过快，不宜追高 | 暂停追高 |
| `RISK_CONTAINMENT` | 流动性或结构风险升高 | 进入风险控制 |

### 兼容输出

`signal` 仍保留，用于兼容旧接口：
- `NO_SIGNAL`
- `WATCH`
- `TRIGGERED`
- `STRONG_BUY`
- `GREEDY`

约束：
- `signal` 不能表达得比 `allocation_state` 更激进。
- CLI、JSON、history 输出都以 `allocation_state` 为先。

## 5. 数据质量要求

`data_quality` 必须对以下字段明确给出：
- `value`
- `source`
- `usable`
- `stale_days`
- `category`

特别要求：
- live 值与 cached 值必须可区分。
- cached 宏观值必须显式标记 `cache:macro_state`。
- `stale_days` 反映缓存记录日期与当前 market snapshot 的差异。

## 6. 回测要求

回测口径为 allocator-style。

必须满足：
- baseline weekly DCA 始终存在
- tactical states 只改变投入节奏
- 禁止使用 synthetic fear/greed
- 禁止使用 fabricated short-volume

回测指标：
- `T+5 / T+20 / T+60` forward return
- `max adverse excursion`
- average cost vs baseline DCA
- fraction of capital deployed before final low

不再使用：
- “±10 天内是否命中底部”
- “98.1% 捕捉率”类 headline

## 7. 验收标准

1. `allocation_state` 是一切用户动作的主接口。
2. 兼容 `signal` 不得比 `allocation_state` 更激进。
3. CLI / JSON / history 必须显式显示 tranche、confidence、data-quality summary。
4. `data_quality` 必须正确标识 cached 宏观字段的来源和滞后。
5. 回测必须完成 allocator-style smoke run，且不依赖 synthetic live-path assumptions。

## 8. 设计决策

- ERP 继续保留，但作用从“鼓励抄底”转为“约束允许的仓位动作上限”。
- Tier 2 从 hard veto 降级为 soft overlay，避免长期资金被短期期权噪音主导。
- 旧版强情绪话术被替换为操作性语言，减少“高确定性重仓点”幻觉。
