from __future__ import annotations

import pandas as pd

from src.research.recovery_hmm.comparison import compare_shadow_vs_production


def test_comparison_report_flags_recovery_release_vs_production_baseline(tmp_path):
    production = pd.DataFrame(
        {
            "date": ["2023-01-03", "2023-01-04"],
            "stable_regime": ["BUST", "BUST"],
            "target_beta": [0.5, 0.5],
        }
    )
    shadow = pd.DataFrame(
        {
            "date": ["2023-01-03", "2023-01-04"],
            "shadow_state": ["RECOVERY", "RECOVERY"],
            "w_final": [0.9, 0.95],
        }
    )
    production_path = tmp_path / "production.csv"
    shadow_path = tmp_path / "shadow.csv"
    production.to_csv(production_path, index=False)
    shadow.to_csv(shadow_path, index=False)

    report = compare_shadow_vs_production(
        production_trace_path=production_path,
        shadow_trace_path=shadow_path,
    )

    assert "recovery_release_gap" in report
