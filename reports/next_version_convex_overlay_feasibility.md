# Convex Overlay Feasibility Audit

## QQQ OTM put overlays
- **Verdict**: `FEASIBLE_AS_TARGETED_RESIDUAL_PROTECTION`
- **carry cost / theta bleed burden**: High but bounded if smartly rolled.
- **liquidity / execution feasibility**: Excellent
- **hedge alignment with the defined residual damage objective**: High
- **survivability improvement in target event classes**: Significant gap coverage
- **degradation in benign / non-stress periods**: Measurable drag
- **implementation complexity**: Moderate
- **governance / auditability complexity**: Moderate

## VIX call overlays
- **Verdict**: `PARTIALLY_FEASIBLE_WITH_HEAVY_COSTS`
- **carry cost / theta bleed burden**: Very high, extremely steep contango
- **liquidity / execution feasibility**: Good
- **hedge alignment with the defined residual damage objective**: Imperfect due to basis risk
- **survivability improvement in target event classes**: Strong during volatility spikes
- **degradation in benign / non-stress periods**: Severe drag
- **implementation complexity**: Moderate
- **governance / auditability complexity**: High

## put spreads / collars / capped hedge structures
- **Verdict**: `FEASIBLE_AS_TARGETED_RESIDUAL_PROTECTION`
- **carry cost / theta bleed burden**: Low/neutral if collared
- **liquidity / execution feasibility**: Good
- **hedge alignment with the defined residual damage objective**: High (covers the exact gap down band)
- **survivability improvement in target event classes**: Capped but highly effective within the band
- **degradation in benign / non-stress periods**: Opportunity cost on upside (if collared)
- **implementation complexity**: High
- **governance / auditability complexity**: High
