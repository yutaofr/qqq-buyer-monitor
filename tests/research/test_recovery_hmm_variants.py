from __future__ import annotations

from src.research.recovery_hmm.variants import (
    LOCKED_CANDIDATE_VARIANT,
    WORLDVIEW_OPTIMIZATION_VARIANTS,
)


def test_worldview_variant_catalog_exposes_five_distinct_optimization_tracks():
    variants = WORLDVIEW_OPTIMIZATION_VARIANTS

    assert len(variants) == 5
    assert [variant.name for variant in variants] == [
        "stress_hardened",
        "recovery_accelerated",
        "orthogonal_consensus",
        "barbell_balance",
        "fdas_guardrail",
    ]


def test_locked_candidate_variant_remains_separate_from_future_optimization_tracks():
    assert LOCKED_CANDIDATE_VARIANT.name == "locked_candidate"
    assert LOCKED_CANDIDATE_VARIANT.name not in {variant.name for variant in WORLDVIEW_OPTIMIZATION_VARIANTS}
