# QQQ Daily Cycle Stage Probability Dashboard

This repository's terminal product is a daily post-close cycle-stage probability dashboard for QQQ regime review.

It is not an automatic leverage engine, not an order generator, and not a turning-point predictor. The user remains the final beta decision-maker. The product helps answer, once per US market close:

- Where are we in the cycle right now?
- How stable is that judgment?
- Is transition pressure building?
- Is this a meaningful regime migration or ordinary noise?

## Product Boundary

The launch product is `scripts/product_cycle_dashboard.py`.

It outputs:

- a probability distribution over `EXPANSION`, `LATE_CYCLE`, `STRESS`, `RECOVERY`, and `FAST_CASCADE_BOUNDARY`
- dominant and secondary stage
- transition urgency
- stage stability and concentration
- relapse pressure for repair-state interpretation
- evidence panel
- boundary warning when gap/cascade conditions dominate
- qualitative action-relevance band for discretionary review

The product does not output hard target leverage, automatic policy orders, or execution instructions.

## Daily Product Contract

The dashboard is designed for a 60-second post-close read.

Top section:

- dominant stage
- secondary stage
- full stage probability distribution
- transition urgency
- action-relevance band

Middle section:

- concentration / stability
- change versus yesterday
- 5-day and 20-day probability distribution changes
- short rationale

Evidence section:

- hazard score and percentile context
- breadth health
- volatility regime
- structural stress
- repair / relapse state
- boundary pressure / gap stress

Expectation section:

- what the system can help with: cycle-stage interpretation and transition review
- what it cannot do: exact timing, automatic beta targeting, or gap execution control

## Allowed Stage Set

- `EXPANSION`: healthy breadth, contained volatility, low hazard.
- `LATE_CYCLE`: pressure is rising but structural stress is not fully confirmed.
- diffuse `LATE_CYCLE` cases should be read as a transition zone, not forced certainty.
- `STRESS`: structural damage, persistent stress, weak breadth, or elevated volatility.
- `RECOVERY`: repair is visible after recent stress, but relapse risk remains explicit.
- `FAST_CASCADE_BOUNDARY`: gap/cascade conditions where account and execution physics dominate ordinary stage inference.

`FAST_CASCADE_BOUNDARY` is a warning layer. It must not be read as the system knowing what to do.

## Recovery And Transition Safety

- `RECOVERY` must always be read together with `relapse_pressure`.
- `relapse_pressure = LOW` means repair looks comparatively clean.
- `relapse_pressure = ELEVATED` or `HIGH` means the dashboard is explicitly warning against treating recovery as a clean all-clear.
- diffuse `LATE_CYCLE` cases should foreground directional drift:
  - drifting toward `STRESS`
  - drifting back toward `EXPANSION`
  - unresolved / mixed

This is a presentation rule, not a request to artificially harden the probabilities.

## Forward OOS Monitoring

True out-of-sample evidence is not solved retrospectively. It starts accumulating only from deployment forward.

The final product now maintains a forward monitoring log under:

- `artifacts/final_product/forward_oos_monitoring_log.jsonl`

Each row records the daily stage distribution, dominant and secondary stage, urgency, action band, relapse pressure, hazard state, breadth state, volatility state, boundary flag, rationale summary, and forward outcome fields for later evaluation. Reruns do not duplicate the same `market_date` unless `product_version`, `calibration_version`, or `ui_version` differs.

`recovery_relapsed` is frozen exactly as an OR-triggered 10-trading-day forward outcome:

- after any day with `dominant_stage == RECOVERY`
- observe next 10 trading days
- mark `true` if any of:
  - `dominant_stage` returns to `STRESS`
  - `FAST_CASCADE_BOUNDARY` is triggered
  - `relapse_pressure == HIGH` and `secondary_stage == STRESS` for at least 2 consecutive trading days
- mark `false` if the window completes without any trigger
- keep `null` if the window is incomplete
- this definition may not be changed retroactively

## Validation Discipline

The product is validated as a probability product, not as a policy-PnL optimizer.

Current generated artifacts include:

- `artifacts/product/probability_calibration_quality.json`
- `artifacts/product/stage_process_stability_audit.json`
- `artifacts/product/historical_probability_validation.json`
- `artifacts/product/final_verdict.json`

Current generated reports include:

- `reports/product_probability_calibration_quality.md`
- `reports/product_stage_process_stability_audit.md`
- `reports/product_historical_probability_validation.md`
- `reports/product_acceptance_checklist.md`
- `reports/product_final_verdict.md`

## Running The Product Audit

```bash
python3 scripts/product_cycle_dashboard.py
```

This regenerates the product reports and machine-readable artifacts under:

- `reports/product_*.md`
- `artifacts/product/*.json`

## Testing

```bash
python3 -m pytest tests/unit/test_product_cycle_dashboard.py -q
```

The test suite verifies:

- full five-stage probability distribution
- dominant and secondary stage ordering
- urgency/action separation
- boundary warning honesty
- required reports and artifacts
- probability quality thresholds
- stage-process stability thresholds
- historical validation windows
- final verdict vocabulary

## Legacy Engine Boundary

The repository still contains historical research and execution-era modules. Those modules can provide evidence, diagnostics, and archived context, but they are not the terminal product path.

Any component whose primary role is target beta, allocation, deployment pacing, or automatic execution must be treated as frozen or translation-only unless it is explicitly refactored into the probability-dashboard contract.
