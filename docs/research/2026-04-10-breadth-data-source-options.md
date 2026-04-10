# Breadth Data Source Options

日期: `2026-04-10`

## 背景

当前生产线 `breadth` 因子主源依赖 Yahoo Finance 的 `^ADD` / `^ADDN`。
这条链的问题不是单纯 cron 时间，而是：

- `^ADD` / `^ADDN` 本身不稳定，跨环境可用性差
- 现有日志过去会把“主源失败但 proxy 已接管”误报成“breadth unavailable”
- 这类单点 ticker 方案不适合作为生产主源

当前代码已修正日志语义，但数据源架构本身仍建议升级。

## 结论

最稳的方案不是继续找另一个单点 breadth ticker，而是改成“可重建的 breadth”：

1. 用稳定的股票日线源
2. 用稳定的成分股清单
3. 自己计算 breadth 指标

对本系统，优先级如下。

## 方案排序

### 方案 A: 强化现有 `QQQ/QQEW` proxy

定义:
- 继续保留 `QQQ` vs `QQEW` 的相对强弱/相对 50D 偏离，映射为 breadth proxy

优点:
- 不依赖 `^ADD` / `^ADDN`
- 实现最小，和现有生产线最兼容
- 对 Nasdaq 大盘集中度、抱团和广度恶化有直接解释力

缺点:
- 它不是严格的 advance/decline breadth
- 更像 concentration / equal-weight participation proxy
- 对 NYSE 全市场广度代表性不足

适用:
- 作为短期生产修复最优
- 适合作为主 fallback，甚至可以升为主源

结论:
- 短期最值得落地

### 方案 B: 基于 `QQQ` 成分股自建 breadth

定义:
- 拉取 `QQQ` 官方 holdings
- 对成分股日线计算:
  - advances / declines
  - pct above 20D / 50D / 200D
  - equal-weight return breadth
  - up/down volume participation

优点:
- 比 `QQQ/QQEW` 更接近真实 breadth
- 比 `^ADD` 更稳定、可复现、可审计
- 和本系统关注的 Nasdaq 风格风险最一致

缺点:
- 需要维护 holdings 抓取/缓存
- 需要批量成分股历史行情
- 计算链更长

推荐数据输入:
- 成分股清单: Invesco QQQ holdings
- 单股日线: Tiingo / FMP / 现有可缓存 EOD 源

适用:
- 中期正式替代方案

结论:
- 中期最佳主方案

### 方案 C: 基于更大全市场股票池自建 breadth

定义:
- 用 Nasdaq 全市场或 NYSE 全市场股票列表，自建真正市场 breadth

优点:
- 最接近传统 breadth 定义
- 可扩展到更完整的市场结构审计

缺点:
- 数据工程成本最高
- delisted / symbol mapping / survivorship 处理更复杂
- 对当前 QQQ 系统未必值得第一时间做

适用:
- 后续研究扩展

结论:
- 不是当前优先级

## 外部数据源比较

### Yahoo Finance `^ADD` / `^ADDN`

结论:
- 不建议继续作为生产主源

原因:
- symbol 稳定性差
- 环境差异大
- 无法作为高可靠生产数据契约

### Tiingo

适合:
- 单股历史日线
- 用于自建 breadth

优点:
- 接口稳定性通常好于 Yahoo
- 更适合工程化缓存

缺点:
- 不是现成 breadth feed
- 仍需自己聚合

结论:
- 适合方案 B / C

### Financial Modeling Prep

适合:
- 股票列表
- 历史 EOD
- 批量股票覆盖

优点:
- 数据面更全
- 做 breadth 重建顺手

缺点:
- 免费层有限制
- 不是开源，只是可公开调用的 API

结论:
- 适合方案 B / C

### Alpha Vantage

适合:
- 小规模时间序列

缺点:
- 免费限速偏紧
- 不适合大规模 breadth 批处理

结论:
- 可用，但不是首选

## 建议路线

### 第一阶段

目标:
- 让生产线不再依赖 `^ADD` / `^ADDN`

动作:
- 将 `QQQ/QQEW` proxy 升为正式一级来源
- `^ADD` / `^ADDN` 降为 opportunistic source
- 明确记录:
  - `source_breadth_proxy`
  - `breadth_quality_score`
  - `primary_ticker_failures`

### 第二阶段

目标:
- 建立可审计、可回放的真实 breadth pipeline

动作:
- 增加 `QQQ` holdings 缓存
- 对成分股自建 breadth:
  - `adv_dec_ratio`
  - `pct_above_50d`
  - `equal_weight_participation`
  - `up_volume_share`

### 第三阶段

目标:
- 把 breadth 从单指标升级为结构化族群指标

动作:
- 区分:
  - participation breadth
  - concentration breadth
  - momentum breadth
  - drawdown breadth

## 推荐决策

直接建议:

1. 立即把 `QQQ/QQEW` proxy 提升为生产主源
2. 将 `^ADD` / `^ADDN` 保留为补充观测，不再作为主契约
3. 下一步排期实现 `QQQ` 成分股 breadth 重建

这条路线最符合当前系统：

- 先稳住生产
- 再提升真实性
- 最后扩展全市场 breadth
