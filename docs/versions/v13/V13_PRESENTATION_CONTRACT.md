# v13 Presentation Contract

**Status**: LOCKED FOR IMPLEMENTATION  
**Version**: v13.0  
**Date**: 2026-04-03  
**Parent Spec**: `V13_EXECUTION_OVERLAY_SRD.md`

---

## 1. Scope

This document defines how `v13` adapts:

- `src/output/web_exporter.py`
- `src/web/public/index.html`
- `src/output/discord_notifier.py`

The goal is to surface execution overlay behavior without changing the current visual identity or misleading the user about what changed in the engine.

---

## 2. Non-Goals

This document does not authorize:

- a redesign of the landing page
- a new design system
- a new frontend framework
- a denser or noisier Discord notification format
- any UI wording that implies sentiment or tape data changed posterior belief

---

## 3. Style Invariance Rules

The page style must remain materially unchanged.

Frozen UI characteristics:

- same single-file `index.html` delivery model
- same overall card hierarchy and mobile layout
- same dark glass aesthetic and current color family
- same typography direction and motion language
- same primary hero metrics: stable regime, entropy, deployment rhythm, target beta

Allowed change:

- add overlay-aware information blocks using the existing visual language

Not allowed:

- replacing the page shell
- changing the visual hierarchy so overlay becomes the new primary narrative
- introducing a separate void theme or a new page state for v13.0

---

## 4. `status.json` Contract Additions

The exporter shall preserve the existing top-level structure:

```text
meta
signal
evidence
```

v13 additions shall follow this shape:

```text
signal.protected_beta
signal.overlay_beta
signal.beta_overlay_multiplier
signal.deployment_overlay_multiplier
signal.overlay_mode
signal.overlay_state
signal.overlay_summary

evidence.execution_overlay.negative_score
evidence.execution_overlay.positive_score
evidence.execution_overlay.raw_inputs
evidence.execution_overlay.input_quality
evidence.execution_overlay.derived_features
evidence.execution_overlay.signal_contributions
evidence.execution_overlay.admission_decisions
evidence.execution_overlay.neutral_fallback_triggered
```

Semantics:

- `raw_target_beta` remains the inherited v12.1 pre-entropy surface
- `protected_beta` is post-entropy, pre-overlay
- `overlay_beta` is post-overlay continuous beta
- `target_beta` remains the actionable continuous target exported to the current hero card

---

## 5. `index.html` Adaptation Rules

### 5.1 Main Card

The hero section remains stable-regime first.

The target beta card remains the main number on the page.

v13 adds a compact audit strip below the existing beta bar:

- `Raw`
- `Protected`
- `Overlay`
- `Final`

This strip must use the existing card language. It must not become a second dashboard.

### 5.2 Deployment Card

The existing deployment card remains in place.

v13 may add one short line beneath the current readiness text:

- penalty active
- reward active
- neutral overlay

The wording must describe execution conditioning, not belief revision.

### 5.3 Insights Panel

The expanded insights panel may add three new sections:

1. `Execution Overlay`
2. `Overlay Inputs`
3. `Overlay Decision Trace`

These sections must reuse the existing evidence-card and feature-chip patterns.

If the overlay is neutral, the panel may collapse to a concise neutral message rather than dumping empty JSON.

### 5.4 Visual Priority

Visual priority order must remain:

1. stable regime
2. target beta
3. deployment rhythm
4. posterior and prior distributions
5. overlay diagnostics

Overlay is an execution audit layer, not the hero story.

---

## 6. `discord_notifier.py` Adaptation Rules

Discord remains compact.

Required behavior:

- keep the current embed-first format
- keep regime as the primary semantic color driver
- add overlay context only as execution audit information
- keep the message short enough for immediate human scan

Recommended field strategy:

- keep `Posterior Distribution`
- keep `Execution Audit`
- keep `Reference Allocation`
- add overlay lines inside `Execution Audit`, not a separate verbose JSON dump

Minimum overlay lines:

- `Protected Beta`
- `Overlay Beta`
- `Beta Multiplier`
- `Pace Multiplier`
- `Overlay State`

Discord must not dump raw overlay inputs, input quality maps, or long logic traces.

---

## 7. Copy Rules

Allowed narrative:

- Bayesian core determines direction
- overlay conditions execution
- penalty slows or reduces action
- reward only affects incremental deployment pace

Forbidden narrative:

- sentiment changed the regime
- tape changed posterior probability
- overlay discovered a new market law

---

## 8. Test Mapping

| Test ID | Purpose |
| :--- | :--- |
| `AC-17` | web export and `index.html` remain contract-aligned and style-preserving |
| `AC-18` | Discord payload includes compact overlay audit lines without posterior confusion |
| `tests/unit/test_web_exporter.py` | overlay fields appear in `status.json` with correct semantics |
| `tests/integration/test_web_alignment.py` | `index.html` references all required v13 paths |
| `tests/unit/test_discord_notifier.py` | embed wording and field structure remain compact and correct |
