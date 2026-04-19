# Final SRD Structural Boundary Rebuild

## Top-Level Verdict
`STRUCTURAL_NON_DEFENDABILITY_CONFIRMED_FOR_2020_LIKE_EVENTS`

## Computations
- `gap_adjusted_survivability`: `{'rows': 51, 'cumulative_return': -0.06540906474654162, 'absolute_loss': 0.8067543893263802, 'negative_gap_loss': 0.5850925790055248, 'negative_regular_session_loss': 0.42606117339748517, 'gap_loss_share': 0.5786385874700565, 'max_drawdown': -0.2855936032087112, 'largest_overnight_gap': -0.09457197522013183, 'mean_stress_score': 0.5592889408409644, 'source': 'data/qqq_history_cache.csv'}`
- `idealized_vs_gap_adjusted_comparison`: `{'idealized_signal_day_return_sum': -0.037918514949041075, 'next_session_executable_return_sum': -0.07283161629940305, 'executable_gap_component': -0.062020499428548134, 'idealized_minus_executable': 0.03491310135036197}`
- `earlier_trigger_counterfactuals`: `{'lead_1_trading_days': {'return_sum': -0.204845143301319, 'gap_component': -0.1924995265359504, 'largest_gap_date': '2020-03-16'}, 'lead_2_trading_days': {'return_sum': -0.13607678984634994, 'gap_component': -0.1420566148561102, 'largest_gap_date': '2020-03-16'}, 'lead_3_trading_days': {'return_sum': -0.10341059559350849, 'gap_component': -0.12456607935655867, 'largest_gap_date': '2020-03-16'}, 'lead_5_trading_days': {'return_sum': -0.09215023360761423, 'gap_component': -0.10135748502557834, 'largest_gap_date': '2020-03-16'}}`
- `execution_gap_contribution_share`: `0.5786385874700565`

## Event-Class Boundaries
- `2020-like fast cascades with dominant overnight gaps`: `STRUCTURALLY_NON_DEFENDABLE_UNDER_CURRENT_ACCOUNT_CONSTRAINTS` gap_share=0.5786
- `2015-style flash / liquidity vacuum events`: `RESIDUAL_PROTECTION_LAYER_REQUIRED` gap_share=0.4738
- `2018-style partially containable drawdowns`: `POLICY_LAYER_REMAINS_MEANINGFUL` gap_share=0.3086
- `slower structural stress events`: `RESIDUAL_PROTECTION_LAYER_REQUIRED` gap_share=0.3505
- `rapid V-shape ordinary corrections`: `EXECUTION_LAYER_DOMINATES` gap_share=0.3398
- `recovery-with-relapse events`: `POLICY_LAYER_REMAINS_MEANINGFUL` gap_share=0.4157
