# pi_stress Rollout and Monitoring Plan

## Purpose

Use the repaired pi_stress posterior as a calibrated systemic stress posterior, not as a standalone trading rule.

## Scope

In scope: posterior scoring, threshold-policy evaluation, diagnostics, shadow comparison, monitoring, and rollback.

Out of scope: beta-surface repair, raw beta delta repair, portfolio execution redesign, and raw macro or market-internal hard gates in conductor.py.

## Key Assumptions

- Stress labels are transparent proxies, not perfect economic truth.
- Current improvements are measured on the fresh current-branch trace and registry.
- Threshold policy is a separate governed layer.

## Known Failure Modes

- Legacy 0.50 policy misses prolonged stress, especially 2022 H1.
- Isotonic calibration can create posterior plateaus.
- Proxy-label mismatch can inflate false-positive readings inside stressed windows.
- Missing market-internal data can degrade S_market back toward topology fallback.
- Downstream beta instability may persist because beta-surface repair is separate.

## Rollout Stages

| Stage | Entry Criteria | Metrics Monitored | Exit Criteria | Rollback Trigger |
|---|---|---|---|---|
| Research branch acceptance | Tests and governance artifacts complete | Brier, ECE, AUC, mean gap, 2023 FP, 2022 H1 recall | Model risk review package accepted | Inconsistent decision taxonomy |
| Shadow / parallel run | Research acceptance complete | Posterior drift, trigger rate drift, legacy-vs-new divergence | Stable for agreed validation window | Trigger rate inflation or data degradation |
| Controlled validation period | Shadow diagnostics clean | Episode capture, miss rate, ordinary-correction FP, calibration drift | Reviewer sign-off | Recall degradation or calibration drift |
| Reviewer sign-off gate | Validation complete | Full governance checklist | Quant, model risk, strategy owner, production engineering approval | Any mandatory reviewer rejects |
| Limited production activation | Sign-offs complete | Threshold triggers, hedge path, beta delta, feature health | No alert breach over limited activation | False-positive inflation, unstable threshold behavior, beta instability |
| Full activation or rollback | Limited activation clean | All monitoring categories | Production owner approval | Any hard rollback threshold breach |

## Monitoring Framework

| Category | Metric Definition | Alert Threshold | Cadence | Owner / Reviewer |
|---|---|---|---|---|
| Posterior distribution drift | PSI or quantile shift of pi_stress vs validation baseline | PSI > 0.20 or p95 shift > 0.15 | Daily / weekly review | Quant research / model risk |
| Threshold trigger drift | Fraction above 0.25, 0.35, 0.50 | 2x validation trigger rate for 5 trading days | Daily | Strategy owner |
| Episode capture / miss tracking | Captured stress episodes / labeled stress episodes | Episode capture below 0.70 over review window | Weekly | Quant research |
| Calibration drift | Rolling Brier, ECE, reliability bins | ECE > 0.08 or Brier degrades by 30% | Weekly | Model risk |
| Ordinary-correction false-positive drift | Non-stress avg pi and trigger rate in correction basket | FP avg exceeds baseline by 20% | Weekly | Quant research |
| Downstream beta / hedge pathology | raw beta delta, target beta instability, hedge flips | Worsening vs legacy by agreed tolerance | Daily | Strategy owner / production engineering |
| Missing-data / degraded-feature monitoring | Missing or fallback rate for S_market and S_macro_anom inputs | fallback_used > 20% for 5 days | Daily | Production engineering |

## Change Management

All threshold changes require a policy artifact update, registry update, reviewer sign-off, and rollback note. No raw market or macro feature gates may be added to conductor.py.

## Required Reviewer Sign-Offs

- Quant research
- Model risk
- Strategy owner
- Production engineering
