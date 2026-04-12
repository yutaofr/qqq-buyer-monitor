# QLD Left-Side Entry Design

## Problem

The current `QLDPermissionEvaluator` is designed to open QLD after repair is already confirmed. That is consistent with process safety, but it is too late for a true left-side buy like October 2022. The current gate requires:

- `topology_recovery == True`
- `effective_entropy <= threshold`
- calm `tractor/sidecar`
- active `fundamental_override`

That design prevents reckless leverage, but it structurally misses the "still ugly, but no longer getting worse" regime. In other words, it captures early right-side repair, not left-side exhaustion.

The goal is not to loosen the whole engine. The goal is to add a distinct left-side permission regime that:

- only activates in washout-to-repair transitions
- allows small, sub-1x QLD exposure before full recovery confirmation
- never overrides the 0.5 beta floor or process-band discipline
- remains PIT-safe and auditable inside the existing runtime chain

## Recommended Approach

Add a new `LEFT_SIDE_PROBE` branch inside `QLDPermissionEvaluator`, separate from the current `SUB1X_READY` and `FUNDAMENTAL_OVERRIDE_RELEASE` paths.

This branch should only open when the market is still in `BUST` or transition-heavy `LATE_CYCLE`, but the process shows exhaustion rather than continued decay. The logic should rely on existing topology fields rather than new ad hoc indicators:

- `damage_memory` must be high enough to prove prior washout
- `recovery_impulse` must be positive
- `recovery_prob_delta >= 0`
- `recovery_prob_acceleration >= 0`
- `repair_persistence` must clear a lower bar than full recovery
- `bust_pressure` must be falling enough to show stress relief
- `bullish_divergence` should contribute positively when present
- `tractor/sidecar` must be non-accelerating, not necessarily fully calm

The key distinction is this:

- full recovery gate says "repair is confirmed"
- left-side gate says "damage is extreme, selling pressure is exhausting, and repair has started"

## Why This Matches The Worldview

The repo's current worldview already says process matters more than raw payoff ranking. That implies a real left-side design cannot be "buy because it is down a lot." It must be "buy because the downtrend's second derivative has flipped."

That is exactly what October 2022 looked like:

- deep damage already existed
- macro stress was still bad, but no longer worsening at the same rate
- RSI and breadth damage were still ugly, yet exhaustion was visible
- full trend confirmation came later

The left-side layer should therefore be based on process curvature, not level alone. In this codebase, the best PIT-safe proxies are already present in `PriceTopologyState`: `recovery_impulse`, `repair_persistence`, `recovery_prob_delta`, `recovery_prob_acceleration`, `damage_memory`, and `bust_pressure`.

This avoids regime cheating. We are not adding hindsight labels. We are recognizing when the existing process says the market has moved from "active collapse" to "exhausted collapse."

## Decision Design

Introduce two different QLD entry modes.

### 1. Left-Side Probe

Purpose:
- allow a first QLD foothold before full `RECOVERY` confirmation

Conditions:
- topology regime in `BUST` or `LATE_CYCLE`
- `damage_memory >= 0.45`
- `recovery_impulse >= 0.18`
- `repair_persistence >= 0.24`
- `recovery_prob_delta >= 0.0`
- `recovery_prob_acceleration >= -0.002`
- `bust_pressure <= 0.55`
- entropy below a looser but still defensive ceiling
- `tractor/sidecar` valid and non-accelerating
- no binding `SELL_QLD`

Output:
- `qld_allowed = True`
- `allow_sub1x_qld = True`
- `forced_bucket = "QLD"` only if `target_beta >= 0.62`
- `relaxed_entry_signal` capped below the full recovery path

Interpretation:
- this is not a full risk-on signal
- this is a controlled probe when downside momentum is fading

### 2. Recovery Expansion

Purpose:
- keep the current stronger path for confirmed repair

Conditions:
- current existing sub-1x gate and fundamental override logic

Output:
- unchanged behavior for stronger, cleaner re-risking

## Sizing Rules

Left-side must be explicitly smaller than recovery expansion.

Rules:
- left-side can only authorize `QLD` if `0.62 <= target_beta < 0.78`
- if `target_beta >= 0.78`, use the existing recovery gate, not the left-side gate
- left-side `relaxed_entry_signal` should have a lower ceiling, for example `0.72`
- if entropy rises back above the left-side ceiling, force the bucket back to `QQQ`

This keeps left-side logic from turning into a disguised right-side override.

## Invalidations

The left-side probe must be easy to revoke. It should fail closed on any of these:

- `SELL_QLD` binding with no full override release
- `recovery_prob_delta < 0`
- `recovery_prob_acceleration < -0.004`
- `bust_pressure > 0.60`
- `tractor/sidecar` probability jumps above the left-side risk ceiling
- entropy re-expands above the left-side ceiling

This captures the core left-side truth: the first entry should be fragile until repair confirms.

## Proposed Implementation Shape

Keep the implementation inside the existing permission layer, not inside `BehavioralGuard`.

Changes:

- extend `QLDPermissionDecision` with `entry_mode`
- add `_evaluate_left_side_probe(...)`
- compute a `left_side_probe` payload before the existing full-recovery branch
- return `reason_code = "LEFT_SIDE_PROBE"` when active
- pass the lower `relaxed_entry_signal` into `BehavioralGuard`
- keep `BehavioralGuard` generic; do not teach it market semantics

This preserves clean separation:

- topology decides process state
- permission layer decides whether QLD is allowed
- behavioral guard decides bucket switching mechanics

## Acceptance Criteria

We should not accept the feature because it adds more `QLD` days. We should accept it if it improves the specific left-tail transition window without breaking the main process.

Primary checks:

- `2022-09-15` to `2022-11-30`: first QLD authorization must appear earlier than current `all_on`
- `2023-02-01` to `2023-06-30`: no meaningful degradation in process-band metrics
- no floor breach
- no deterioration in `posterior_vs_benchmark_process`
- `2022_defense` mean beta must stay within current tolerance

Secondary checks:

- left-side QLD days increase modestly in late-2022
- churn does not spike
- `SELL_QLD` still dominates during renewed stress

## Non-Goals

This design is not trying to:

- make QLD aggressive in every rebound
- maximize QLD days
- override beta process with discretionary bottom calling
- replace the full recovery gate

It is intentionally a narrow bridge between panic and confirmation.
