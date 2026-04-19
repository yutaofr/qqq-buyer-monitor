# Final SRD Research Budget Allocation

## Allocation Verdict
`CONTINUE_WITH_WEIGHTED_POLICY_LAYER_RESEARCH`

## retained_asymmetric_ratchet
- `budget_status`: `PRIMARY`
- `target_class_type`: `policy-improvable class`
- `loss_weighted_importance`: `['slower structural stress events', '2015-style flash / liquidity vacuum events']`
- `worst_slice_evidence`: `recomputed drawdown/loss windows; must be validated against 2018 and 2022 relapse slices`
- `bounded_or_uncertain`: `uses price-derived proxy here, not restored candidate safety`
- `aggregate_last`: `no pooled-score optimization`

## retained_execution_aware_policy
- `budget_status`: `PRIMARY`
- `target_class_type`: `policy-improvable plus execution-dominated class`
- `loss_weighted_importance`: `['slower structural stress events', '2020-like fast cascades with dominant overnight gaps']`
- `worst_slice_evidence`: `recomputed gap-adjusted contribution and executable-vs-idealized comparison`
- `bounded_or_uncertain`: `cannot remove overnight gap ceiling`
- `aggregate_last`: `aggregate return is secondary`

## hybrid_capped_transfer
- `budget_status`: `PRIMARY`
- `target_class_type`: `policy-improvable gap-relevant class`
- `loss_weighted_importance`: `depends on recomputed non-gap contribution`
- `worst_slice_evidence`: `hybrid decomposition rebuilt from policy returns`
- `bounded_or_uncertain`: `gap uplift dominates in this rebuild, but post-gap recovery miss is material and 2020-like structural breach risk is not removed`
- `aggregate_last`: `gap and non-gap attribution reported before aggregate`

## discrete_gearbox
- `budget_status`: `BOUNDED`
- `target_class_type`: `policy-improvable transition class`
- `loss_weighted_importance`: `limited by recomputed signal quality`
- `worst_slice_evidence`: `flapping, false upshift/downshift, threshold sensitivity by event class`
- `bounded_or_uncertain`: `not primary unless signal quality is sufficient`
- `aggregate_last`: `no aggregate-only justification`

## residual_protection
- `budget_status`: `BOUNDED`
- `target_class_type`: `residual class`
- `loss_weighted_importance`: `{'2020-like fast cascades with dominant overnight gaps': {'structural_loss_score': 0.09338159604169755, 'target': 'overnight gap shock'}, '2015-style flash / liquidity vacuum events': {'structural_loss_score': 0.0669246353861856, 'target': 'liquidity-vacuum jump losses'}, 'slower structural stress events': {'structural_loss_score': 0.16608490711490367, 'target': 'severe convex crash residuals'}}`
- `worst_slice_evidence`: `2020-like and liquidity-vacuum gap residuals`
- `bounded_or_uncertain`: `objective rebuilt; convex overlay feasibility metrics not yet rebuilt`
- `aggregate_last`: `only target residual damage, not full strategy replacement`
