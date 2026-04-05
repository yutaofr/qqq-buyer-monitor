import pandas as pd

from src.research.v11_feature_subset_research import (
    QQQ_CYCLE_CORE_FEATURES,
    QQQ_CYCLE_OPTIONAL_FEATURES,
    build_qqq_cycle_candidate_sets,
    build_research_frame,
    flatten_window_report,
    rank_candidate_frame,
)


def test_build_qqq_cycle_candidate_sets_is_unique_and_ordered():
    feature_order = list(QQQ_CYCLE_CORE_FEATURES) + list(QQQ_CYCLE_OPTIONAL_FEATURES)

    candidates = build_qqq_cycle_candidate_sets(feature_order)

    names = [candidate["name"] for candidate in candidates]
    subsets = [tuple(candidate["features"]) for candidate in candidates]

    assert "baseline_12" in names
    assert "drop_real_yield_structural_z" in names
    assert "drop_pmi_momentum__labor_slack" in names
    assert "qqq_core_6" in names
    assert len(names) == len(set(names))
    assert len(subsets) == len(set(subsets))

    for candidate in candidates:
        assert candidate["features"] == [f for f in feature_order if f in candidate["features"]]


def test_flatten_window_report_captures_alignment_metrics():
    report = {
        "summary": {
            "top1_accuracy": 0.62,
            "mean_brier": 0.44,
            "mean_entropy": 0.31,
        },
        "critical_regime_performance": {
            "stable_critical_recall": 0.77,
            "raw_critical_recall": 0.74,
        },
        "posterior_alignment": {
            "overall": {
                "mean_true_regime_probability": 0.58,
                "mean_true_regime_rank": 1.31,
                "mean_expected_l1_error": 0.88,
            },
            "by_regime": {
                "BUST": {"mean_true_regime_probability": 0.41, "mean_true_regime_rank": 1.4},
                "RECOVERY": {"mean_true_regime_probability": 0.33, "mean_true_regime_rank": 1.8},
            },
        },
    }

    flat = flatten_window_report("selection", report)

    assert flat["selection_top1_accuracy"] == 0.62
    assert flat["selection_mean_true_regime_probability"] == 0.58
    assert flat["selection_min_regime_true_probability"] == 0.33
    assert flat["selection_max_regime_true_rank"] == 1.8


def test_rank_candidate_frame_prefers_higher_accuracy_and_better_alignment():
    frame = pd.DataFrame(
        [
            {
                "name": "candidate_a",
                "selection_top1_accuracy": 0.67,
                "selection_mean_brier": 0.46,
                "selection_mean_entropy": 0.55,
                "selection_stable_critical_recall": 0.82,
                "selection_mean_true_regime_probability": 0.54,
                "selection_mean_true_regime_rank": 1.42,
                "selection_mean_expected_l1_error": 0.91,
                "selection_min_regime_true_probability": 0.31,
                "selection_max_regime_true_rank": 1.9,
            },
            {
                "name": "candidate_b",
                "selection_top1_accuracy": 0.61,
                "selection_mean_brier": 0.52,
                "selection_mean_entropy": 0.61,
                "selection_stable_critical_recall": 0.78,
                "selection_mean_true_regime_probability": 0.48,
                "selection_mean_true_regime_rank": 1.57,
                "selection_mean_expected_l1_error": 0.99,
                "selection_min_regime_true_probability": 0.24,
                "selection_max_regime_true_rank": 2.2,
            },
        ]
    )

    ranked = rank_candidate_frame(frame)

    assert ranked.iloc[0]["name"] == "candidate_a"
    assert ranked.iloc[0]["selection_composite_rank"] < ranked.iloc[1]["selection_composite_rank"]


def test_build_research_frame_emits_date_column(tmp_path):
    dates = pd.bdate_range("2024-01-01", periods=80)
    macro = pd.DataFrame(
        {
            "observation_date": dates,
            "effective_date": dates,
            "credit_spread_bps": range(80),
            "real_yield_10y_pct": [0.01] * 80,
            "net_liquidity_usd_bn": [5000.0] * 80,
            "treasury_vol_21d": [0.02] * 80,
            "copper_gold_ratio": [0.2] * 80,
            "breakeven_10y": [0.02] * 80,
            "core_capex_mm": [10.0] * 80,
            "usdjpy": [120.0] * 80,
            "erp_ttm_pct": [0.03] * 80,
            "pmi_proxy_manemp": [50.0] * 80,
            "job_openings": [8.0] * 80,
            "source_credit_spread": ["fred:series"] * 80,
            "source_real_yield": ["fred:series"] * 80,
            "source_net_liquidity": ["derived:series"] * 80,
            "source_treasury_vol": ["direct:series"] * 80,
            "source_copper_gold": ["direct:series"] * 80,
            "source_breakeven": ["direct:series"] * 80,
            "source_core_capex": ["direct:series"] * 80,
            "source_usdjpy": ["direct:series"] * 80,
            "source_erp_ttm": ["direct:series"] * 80,
            "source_pmi_proxy": ["fred:series"] * 80,
            "source_job_openings": ["fred:series"] * 80,
            "build_version": ["synthetic"] * 80,
        }
    )
    regimes = pd.DataFrame(
        {
            "observation_date": dates,
            "regime": ["MID_CYCLE"] * 40 + ["LATE_CYCLE"] * 40,
        }
    )
    macro_path = tmp_path / "macro.csv"
    regime_path = tmp_path / "regimes.csv"
    macro.to_csv(macro_path, index=False)
    regimes.to_csv(regime_path, index=False)

    frame, ordered_regimes, metadata = build_research_frame(
        dataset_path=macro_path,
        regime_path=regime_path,
        feature_names=["spread_absolute", "erp_absolute"],
    )

    assert "date" in frame.columns
    assert frame["date"].min() == pd.Timestamp("2024-01-01")
    assert ordered_regimes == ["MID_CYCLE", "LATE_CYCLE"]
    assert metadata["feature_names"] == ["spread_absolute", "erp_absolute"]
