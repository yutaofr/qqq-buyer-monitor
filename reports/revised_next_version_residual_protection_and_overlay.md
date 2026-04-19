# Revised Residual Protection Objective & Convex Overlay Feasibility

## Objective
overnight gap shock band and liquidity-vacuum jump losses that daily signals cannot trade after realization

## QQQ OTM put overlays
- Verdict: `PARTIALLY_FEASIBLE_WITH_HEAVY_COSTS`
- `carry_cost_theta_bleed_burden`: high recurring carry drag
- `liquidity_execution_feasibility`: high
- `hedge_alignment`: high for overnight QQQ gap shock band
- `survivability_improvement_target_events`: meaningful but cost-sensitive
- `benign_period_degradation`: material drag
- `implementation_complexity`: medium
- `governance_auditability_complexity`: medium

## put spreads / collars / capped hedges
- Verdict: `FEASIBLE_AS_TARGETED_RESIDUAL_PROTECTION`
- `carry_cost_theta_bleed_burden`: lower than outright puts, with capped protection or upside give-up
- `liquidity_execution_feasibility`: high in QQQ options
- `hedge_alignment`: high for defined crash residual band
- `survivability_improvement_target_events`: best fit for bounded residual shock band
- `benign_period_degradation`: upside cap or moderate carry drag
- `implementation_complexity`: medium-high
- `governance_auditability_complexity`: medium-high

## VIX call overlays
- Verdict: `PARTIALLY_FEASIBLE_WITH_HEAVY_COSTS`
- `carry_cost_theta_bleed_burden`: very high and term-structure dependent
- `liquidity_execution_feasibility`: medium-high
- `hedge_alignment`: imperfect due to basis risk against QQQ gap losses
- `survivability_improvement_target_events`: can help severe volatility spikes, not all QQQ gaps
- `benign_period_degradation`: severe drag if held continuously
- `implementation_complexity`: medium
- `governance_auditability_complexity`: high
