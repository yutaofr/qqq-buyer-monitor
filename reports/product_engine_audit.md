# Product Engine Audit

## Decision
`ENGINE_AUDIT_IDENTIFIES_CLEAR_REFACTOR_PATH`

## Summary
The repository still contains automatic-policy ancestry, but the new product path isolates it and classifies beta/allocation layers as frozen or translation-only.

## Product Boundary
This launch artifact defines a daily post-close cycle stage probability dashboard. It does not restore automatic leverage targeting, automatic orders, or exact turning-point prediction.

## Machine-Readable Snapshot
```json
{
  "component_classifications": [
    {
      "classification": "ALIGNED_WITH_STAGE_PROBABILITY_PRODUCT",
      "component": "scripts/product_cycle_dashboard.py",
      "reason": "Distribution-first product path with no target leverage field."
    },
    {
      "classification": "ALIGNED_WITH_STAGE_PROBABILITY_PRODUCT",
      "component": "src/regime_dynamics.py",
      "reason": "Computes probability level, first derivative, and second derivative."
    },
    {
      "classification": "REQUIRES_TRANSLATION_REFACTOR",
      "component": "scripts/cycle_stage_navigator.py",
      "reason": "Useful prior navigator, but label/confidence-first rather than probability-distribution-first."
    },
    {
      "classification": "REQUIRES_TRANSLATION_REFACTOR",
      "component": "src/engine/v11/conductor.py runtime_result",
      "reason": "Contains probabilities and dynamics, but still foregrounds target_beta, allocation, and execution policy fields."
    },
    {
      "classification": "LEGACY_AUTO_POLICY_ARTIFACT",
      "component": "src/models.SignalResult / TargetAllocationState",
      "reason": "Schemas center target_beta and target allocation; freeze outside product dashboard path."
    },
    {
      "classification": "REMOVE_OR_FREEZE",
      "component": "src/engine/v11/core/execution_pipeline.py",
      "reason": "Primary role is beta floor, overlay beta, and deployment readiness; not a dashboard output layer."
    },
    {
      "classification": "LEGACY_AUTO_POLICY_ARTIFACT",
      "component": "src/engine/v11/core/expectation_surface.py",
      "reason": "Maps posterior regimes to beta and allocation reference paths."
    },
    {
      "classification": "ALIGNED_WITH_STAGE_PROBABILITY_PRODUCT",
      "component": "src/engine/v11/stress_phase4/*",
      "reason": "Interpretable stress, transition, healing, and boundary evidence can feed the stage dashboard."
    },
    {
      "classification": "REQUIRES_TRANSLATION_REFACTOR",
      "component": "app.py / legacy web panels",
      "reason": "UI still references beta-oriented fields and needs product dashboard ordering."
    }
  ],
  "decision": "ENGINE_AUDIT_IDENTIFIES_CLEAR_REFACTOR_PATH",
  "hard_rule_result": "Automatic leverage targeting components are not part of the user-facing product path.",
  "old_optimization_assumptions_remaining": [
    "base_betas and regime_sharpes still exist in the conductor",
    "execution pipeline still computes floor, protected beta, overlay beta, and target allocation",
    "some UI/docs still discuss beta mechanics and must not be used as launch copy"
  ],
  "summary": "The repository still contains automatic-policy ancestry, but the new product path isolates it and classifies beta/allocation layers as frozen or translation-only."
}
```
