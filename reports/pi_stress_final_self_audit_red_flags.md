# pi_stress Final Self-Audit Red Flags

The red-flag audit is a hard deployment gate.

| Red Flag | Triggered | Evidence | Resolution | Blocks Deployability |
|---|---|---|---|---|
| red_flag_1_conditional_language_disguised_as_finality | NO | Final reports use binary go/no-go language. | No blocker. | NO |
| red_flag_2_posterior_improvement_masking_policy_weakness | YES | Posterior quality passes, but policy stability, ordinary correction, or downstream gates fail. | Blocks unless every deployment gate passes. | YES |
| red_flag_3_threshold_migration_doing_all_the_work | YES | Prolonged-stress capture requires moving below legacy 0.50, and +/-0.10 robustness is not clean. | Blocks direct deployment. | YES |
| red_flag_4_menu_masquerading_as_decision | NO | One tested configuration is named: C9 architecture, Platt calibrator, 0.35 fixed threshold. | No blocker. | NO |
| red_flag_5_ordinary_correction_weakness_ignored | YES | Ordinary basket evidence is explicit and fails the hard tolerance. | Blocks direct deployment. | YES |
| red_flag_6_proxy_label_mismatch_as_excuse | NO | False positives are quantified and not excused by label ambiguity. | No blocker. | NO |
| red_flag_7_calibrator_instability_near_operating_threshold | YES | Platt is smooth (2058 levels), but threshold-local policy behavior fails +/-0.10 checks. Isotonic plateau reference: 0.1762. | Blocks direct deployment. | YES |
| red_flag_8_downstream_beta_risk_waved_away | YES | Downstream beta safety was quantified and fails tolerance. | Blocks direct deployment. | YES |
| red_flag_9_hidden_top_level_hard_gates | NO | No raw market or macro feature hard gate is introduced by this package. | No blocker. | NO |
| red_flag_10_binary_outcome_not_binary | NO | Machine outcome is DEPLOYABLE or DO_NOT_DEPLOY only. | No blocker. | NO |
