# QQQ Monitor

QQQ Monitor is a recommendation engine for `QQQ / QLD / Cash`.

The repository currently contains:

1. A legacy `v10` linear runtime kept for backward compatibility.
2. A converged `v11` probabilistic runtime with anti-noise data guards and behavior constraints.

For new work, `v11` is the reference architecture.

## Legacy Compatibility Notes

The repository still carries legacy documentation and tests around the older dual-controller vocabulary.

In that legacy runtime:

1. `Risk Controller` capped stock beta and leverage eligibility.
2. `Deployment Controller` governed how new cash was staged into `QQQ`.

Those concepts remain relevant for `v10` compatibility, but `v11` is now the primary production baseline.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Run the probabilistic runtime:

```bash
python -m src.main --engine v11
python -m src.main --engine v11 --json
```

Run the v11 audit:

```bash
python -m src.backtest --mode v11
```

Run v11 regression tests:

```bash
pytest tests/unit/engine/v11 -q
pytest tests/integration/engine/v11/test_v11_workflow.py -q
pytest tests/unit/test_main_v11.py -q
pytest tests/unit/test_backtest_v11.py -q
```

## v11 Runtime Contract

`v11` is posterior-first:

`raw data -> degradation audit -> adaptive percentile features -> PCA/KDE posterior -> entropy-aware sizing -> behavioral guard -> safety override -> CLI/DB`

The user-facing contract is:

1. `target_beta`
2. posterior regime probabilities
3. execution bucket (`QLD / QQQ / CASH`)
4. reference allocation path
5. quality audit

The system recommends; it does not trade.

## Verified Audit Snapshot

Reference run on 2026-03-30:

```text
--- v11 Probabilistic Audit ---
Probability: points=31 | top1_accuracy=58.06% | mean_actual_regime_probability=57.93% | mean_brier=0.7982
Execution:   left_escape=PASS | resurrection=PASS | lock_days=12
```

## Repository Structure

1. `src/engine/` decision logic
2. `src/collector/` data ingestion
3. `src/models/` shared domain models
4. `src/store/` persistence
5. `src/output/` CLI and report rendering
6. `tests/unit/` and `tests/integration/`
7. `conductor/tracks/v11/` normative v11 architecture docs
8. `docs/roadmap/` operational notes, acceptance report, and archived research

## Documentation

Normative v11 docs:

1. `conductor/tracks/v11/spec.md`
2. `conductor/tracks/v11/add.md`
3. `conductor/tracks/v11/design_decisions.md`
4. `docs/roadmap/v11_production_sop.md`
5. `docs/roadmap/v11_acceptance_report_2026-03-30.md`

Archived research docs under `docs/roadmap/v11_*` remain for historical context only and are not implementation sources of truth.
