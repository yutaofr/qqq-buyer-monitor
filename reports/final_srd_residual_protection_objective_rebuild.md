# Final SRD Residual Protection Objective Rebuild

## Decision
`MULTIPLE_RESIDUAL_OBJECTIVES_DEFINED_BUT_NOT_PRIORITIZED`

## Target Event Classes
- 2020-like fast cascades with dominant overnight gaps
- 2015-style flash / liquidity vacuum events
- slower structural stress events

## Residual Damage Band
```json
{
  "2015-style flash / liquidity vacuum events": {
    "structural_loss_score": 0.0669246353861856,
    "target": "liquidity-vacuum jump losses"
  },
  "2020-like fast cascades with dominant overnight gaps": {
    "structural_loss_score": 0.09338159604169755,
    "target": "overnight gap shock"
  },
  "slower structural stress events": {
    "structural_loss_score": 0.16608490711490367,
    "target": "severe convex crash residuals"
  }
}
```
