# GEMINI.md - QQQ Bayesian Orthogonal Factor Monitor (v13.0)

> **Repository Master Index: AI & Design Focus**

This repository is governed by a **v13.0 Orthogonal-Core** architecture. AI agents and architects should refer to the following atomic rule files:

## 1. Architecture & Design (The "Why")

- **[Principles](./docs/core/v12_principles.md)**: Orthogonal Matrix, Entropy-First, PIT Integrity, Gram-Schmidt Engine.
- **[Project Structure](./docs/core/v12_structure.md)**: Module roles and directory mapping.
- **[Expert Spec (Macro)](./docs/versions/v12/V12_ORTHOGONAL_FACTOR_SPEC.md)**: Technical factor specifications for the Mud Tractor.
- **[Expert Spec (Sidecar)](./docs/versions/v14/V14_SIDE_CAR_SPEC.md)**: Physical rules and thresholds for the QQQ Sidecar.
- **[Expert Spec (Resonance)](./docs/versions/v14/V14_5_RESONANCE_DETECTOR_SPEC.md)**: Physical rules and tactical thresholds for the QLD Resonance Detector.

## 2. Implementation & Quality (The "How")

- **[Coding Standards](./docs/core/v12_standards.md)**: Mandatory AC-0 to AC-15 criteria.
- **[Validation Protocols](./docs/core/v12_ops.md)**: Performance audits and unit testing.

## 🔴 CRITICAL SYSTEM REDLINES FOR ALL AI AGENTS 🔴

1. **Bayesian Integrity Lock**: In `src/engine/v11/core/bayesian_inference.py`, the posterior calculation **MUST ALWAYS** use true Bayesian multiplication ($Posterior \propto Prior \times Likelihood$). **NEVER** replace this with a linear weighted average (e.g., `m * Likelihood + (1-m) * Prior`). Linear mixtures destroy confidence accumulation and cause "High Entropy Deadlock."
2. **Temperature Scaling (Tau) Lock**: The `inference_tau` in `v13_4_weights_registry.json` is set to `10.0` to calibrate the overconfidence of Naive Bayes in high-dimensional orthogonal space. **NEVER** lower this to `< 1.0` (like the old `0.15` bug) to artificially "sharpen" probabilities. Values > 5.0 are preferred for industrial stability (Brier/Entropy calibration). v14.4 "Bayesian Overdrive" uses a dynamic `tau_factor` (0.5) to temporarily increase sensitivity ONLY during extreme OOD events, while maintaining a stable 10.0 baseline.
3. **Prior Gravity Lock**: The static baseline prior weight in `src/engine/v11/core/prior_knowledge.py` is permanently minimized to **5%**. **NEVER** increase this weight (like the old 40% bug), as it traps the system in an artificial mean-reversion gravity well.

## 3. Product & Philosophy

- **[PRD](./docs/core/PRD.md)**: Product definition and target goals.
- **[Philosophy](./docs/core/V13_USER_PHILOSOPHY.md)**: The user philosophy of orthogonal reality.

## 4. Code Quality & Auxiliary Agent Guidelines

To prevent system degradation ("Spaghetti Code") and enforce proper engineering constraints, all auxiliary developer agents MUST adhere to:

- **TDD-First**: All bug fixes and features must begin with a targeted failing test. Do not declare a task done without regression checks.
- **Confined Modifications**: Stick strictly to the assigned file scopes. Do not restructure the entire codebase or modify unassigned modules.
- **Anti-Spaghetti measures**: Avoid God-classes, keep functions concise (under 200 lines if possible), and isolate side effects (e.g., IO, state persistence) from core deterministic logic (`execution_pipeline`, `bayesian_inference`). Never "Fix Forward" a foundational bug by adding layered `if/else` hacks.
- **Environment & Credentials**: All FRED API keys required for backtesting and data retrieval MUST be sourced from the `.env` file. Do not hardcode keys or use external secrets during local development or backtests.

---
© 2026 QQQ Entropy AI Governance.
