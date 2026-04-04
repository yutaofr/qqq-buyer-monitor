# v13.7-ULTIMA Coding Standards & AC Criteria

> **The "How" - Production Mandate & Guardrails**

## Mandatory AC (Acceptance Criteria)
Every PR must strictly adhere to the following v13.7-ULTIMA standards:

- **AC-0 No Hardcoding**: All weights and parameters must reside in `v13_4_weights_registry.json`.
- **AC-1 Causal Isolation**: Sequential Causality. T+0 observability only.
- **AC-4 Intent-Action Separation**: Return `raw_target_beta_pre_floor` vs `target_beta`.
- **AC-11 Feature Lineage Norm**: Redundant features must share root factor weights (Lineage Partitioning).
- **AC-12 Physical Redline**: 0.5 Beta Floor is the absolute business boundary.
- **AC-13 Deep Hydration**: Systems must not initialize with less than 2000 PIT samples.
- **AC-14 Asymmetric Sharpening**: Use factor-specific Tau mappings (default Tau=3.0) to prevent Naive Bayes overconfidence.
- **AC-15 Bayesian Integrity**: Strict product-based update ($P \propto Prior \times Likelihood$). Mixture models are strictly forbidden in the inference layer.

## Numerical Integrity
- **Bayesian Multiplication**: Always sum logs or multiply raw probabilities. Avoid arithmetic blending of state vectors.
- **Log-Sum-Exp Compliance**: Probabilities must be calculated using log-likelihood summation to prevent overflow.
- **Epsilon Smoothing**: Harmonic means for quality scoring must include $\epsilon=0.01$ to prevent hard-crashes.
- **Anti-Drift**: All inputs must pass through PIT-aligned Rolling Z-Score pre-processors.

## Code Quality
- **Docker-Locked**: Compilations and tests must exclusively run via `docker run`.
- **Ruff Strictness**: 0 warnings allowed for `F (Logic)` and `B (Bugs)` categories.
- **Spec-to-Code Parity**: Code changes without corresponding SRD updates will be rejected.

---
© 2026 QQQ Entropy AI Governance.
