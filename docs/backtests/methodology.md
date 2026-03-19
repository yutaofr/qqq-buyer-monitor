# Backtest Methodology

This backtest evaluates QQQ as an allocation process, not as a labeling system.
The goal is to measure whether the allocator improves long-term entry quality
and drawdown behavior relative to simple alternatives.

## What It Measures

- Forward returns at `T+5`, `T+20`, and `T+60` trading days.
- Max adverse excursion after each add.
- Average cost improvement versus baseline weekly DCA.
- Cost comparison versus a lump-sum alternative.
- Fraction of capital deployed before the final low in the sample window.

## Allocation Model

- Baseline weekly DCA always runs.
- Tactical states speed up or slow down the weekly add schedule.
- `PAUSE_CHASING` trims deployment below baseline DCA instead of acting as a no-op.
- The simulation compares the tactical allocator against:
  - pure weekly DCA
  - lump-sum deployment on the first add date

## Historical Feature Policy

The methodology explicitly excludes unavailable or untrustworthy historical
features rather than inventing them.

- `fear_greed`: excluded because historical values are not sourced here.
- `short_vol_ratio`: excluded because the old backtest fabricated it.

No synthetic fear/greed series is created in the backtest path, and no
fabricated short-volume proxy is used in the methodology.

## Intended Use

This backtest is a methodology check, not a trading recommendation engine.
It is designed to answer:

- Does faster accumulation happen before the worst drawdown?
- Does the allocator improve average entry cost versus DCA?
- How much capital is deployed before the final low?
