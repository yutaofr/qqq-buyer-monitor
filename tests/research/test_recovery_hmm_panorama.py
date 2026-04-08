from __future__ import annotations

from src.research.recovery_hmm.reporting import build_variant_matrix


def test_build_variant_matrix_ranks_promotable_variants_ahead_of_rejects():
    matrix = build_variant_matrix(
        [
            {
                "variant": "slower_variant",
                "decision": "DO_NOT_LIVE_INTEGRATE_YET",
                "shadow_total_return": 1.1,
                "shadow_sharpe": 0.7,
                "q1_2022_avg_weight": 0.72,
                "q1_2023_avg_weight": 0.55,
            },
            {
                "variant": "better_variant",
                "decision": "ELIGIBLE_FOR_GATED_LIVE_TRIAL",
                "shadow_total_return": 1.3,
                "shadow_sharpe": 0.9,
                "q1_2022_avg_weight": 0.60,
                "q1_2023_avg_weight": 0.82,
            },
        ]
    )

    assert list(matrix["variant"]) == ["better_variant", "slower_variant"]
