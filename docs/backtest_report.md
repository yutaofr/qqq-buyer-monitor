# Allocator-Style Backtest Report

这份文档不再记录旧版“信号捕捉率”口径。
当前回测已经切换为 allocator-style，重点评估的是长期资金部署效率，而不是 `TRIGGERED/WATCH` 对历史底部的命中次数。

## 当前权威口径

请以 [docs/backtests/methodology.md](./backtests/methodology.md) 为准。

当前回测关心的指标是：

- `T+5 / T+20 / T+60` forward return
- add 后最大不利波动 (`max adverse excursion`)
- 相对 baseline weekly DCA 的平均成本变化
- 最终低点前已部署资金比例

## 2026-03-19 Smoke Run 示例

执行命令：

```bash
python3 -m src.backtest
```

示例输出：

- `Weekly add events: 1360`
- `Forward returns: T+5=0.3%, T+20=1.2%, T+60=3.8%`
- `Max adverse excursion after add: -48.8%`
- `Average cost vs baseline DCA: -26.0% improvement`
- `Average cost vs lump-sum: 305.9% penalty`
- `Capital deployed before final low: 12.9%`

## 解释方式

- 这类结果用于判断 allocator 是否改善了长期入场节奏。
- 它不代表“系统成功捕捉了多少次市场底部”。
- 它也不应被解读为未来收益承诺。
