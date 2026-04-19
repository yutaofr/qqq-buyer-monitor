# Convergence Structural Boundary Consolidation

## Summary
Boundary map separates structural gap ceilings from policy-improvable stress paths.

## Provenance
All numeric fields in this file are recomputed by `scripts/convergence_research.py` from repository price and macro inputs. Prior artifacts are not used as numeric truth.

## Machine-Readable Snapshot
```json
{
  "event_classes": [
    {
      "account_constraint_dependency": {
        "daily_signal_regular_session_execution": true,
        "spot_only_no_derivatives": true
      },
      "dominant_category": "STRUCTURALLY_NON_DEFENDABLE_CORE",
      "event_class": "2020-like fast-cascade / dominant overnight gap",
      "execution_dominated_share": 0.7786385874700565,
      "model_improvable_share": 0.11249999999999999,
      "policy_improvable_share": 0.1375,
      "quantitative_basis": {
        "average_gap_loss_share": 0.5786385874700565,
        "average_stress_score": 0.5525299552208676,
        "largest_overnight_gap": -0.09457197522013183
      },
      "residual_protection_only_share": 0.5,
      "structural_non_defendability_share": 0.75
    },
    {
      "account_constraint_dependency": {
        "daily_signal_regular_session_execution": true,
        "spot_only_no_derivatives": true
      },
      "dominant_category": "EXECUTION_DOMINATED",
      "event_class": "2015-style liquidity vacuum / flash impairment",
      "execution_dominated_share": 0.7300094029398392,
      "model_improvable_share": 0.21149576867707237,
      "policy_improvable_share": 0.2584948283830885,
      "quantitative_basis": {
        "average_gap_loss_share": 0.5300094029398391,
        "average_stress_score": 0.348612723253442,
        "largest_overnight_gap": -0.07978545145332883
      },
      "residual_protection_only_share": 0.0,
      "structural_non_defendability_share": 0.5300094029398391
    },
    {
      "account_constraint_dependency": {
        "daily_signal_regular_session_execution": true,
        "spot_only_no_derivatives": true
      },
      "dominant_category": "MODEL_AND_POLICY_MIXED",
      "event_class": "2018-style partially containable drawdown",
      "execution_dominated_share": 0.30864608846047376,
      "model_improvable_share": 0.31110926019278673,
      "policy_improvable_share": 0.38024465134673946,
      "quantitative_basis": {
        "average_gap_loss_share": 0.30864608846047376,
        "average_stress_score": 0.3367449202811666,
        "largest_overnight_gap": -0.03425712903956579
      },
      "residual_protection_only_share": 0.0,
      "structural_non_defendability_share": 0.30864608846047376
    },
    {
      "account_constraint_dependency": {
        "daily_signal_regular_session_execution": true,
        "spot_only_no_derivatives": true
      },
      "dominant_category": "POLICY_IMPROVABLE_PRIMARY",
      "event_class": "slower structural stress",
      "execution_dominated_share": 0.5504889395502244,
      "model_improvable_share": 0.29227997720239896,
      "policy_improvable_share": 0.3572310832473766,
      "quantitative_basis": {
        "average_gap_loss_share": 0.3504889395502244,
        "average_stress_score": 0.5713015882990709,
        "largest_overnight_gap": -0.07412312053926129
      },
      "residual_protection_only_share": 0.0,
      "structural_non_defendability_share": 0.3504889395502244
    },
    {
      "account_constraint_dependency": {
        "daily_signal_regular_session_execution": true,
        "spot_only_no_derivatives": true
      },
      "dominant_category": "MODEL_AND_POLICY_MIXED",
      "event_class": "recovery-with-relapse",
      "execution_dominated_share": 0.41568350935889076,
      "model_improvable_share": 0.2629424207884991,
      "policy_improvable_share": 0.32137406985261013,
      "quantitative_basis": {
        "average_gap_loss_share": 0.41568350935889076,
        "average_stress_score": 0.3908667284727596,
        "largest_overnight_gap": -0.028769673392014528
      },
      "residual_protection_only_share": 0.0,
      "structural_non_defendability_share": 0.41568350935889076
    },
    {
      "account_constraint_dependency": {
        "daily_signal_regular_session_execution": true,
        "spot_only_no_derivatives": true
      },
      "dominant_category": "POLICY_IMPROVABLE_PRIMARY",
      "event_class": "rapid V-shape ordinary correction",
      "execution_dominated_share": 0.339815158527497,
      "model_improvable_share": 0.42912014695712697,
      "policy_improvable_share": 0.23106469451537603,
      "quantitative_basis": {
        "average_gap_loss_share": 0.339815158527497,
        "average_stress_score": 0.112740983576046,
        "largest_overnight_gap": -0.01208839590080013
      },
      "residual_protection_only_share": 0.0,
      "structural_non_defendability_share": 0.339815158527497
    }
  ],
  "summary": "Boundary map separates structural gap ceilings from policy-improvable stress paths."
}
```
