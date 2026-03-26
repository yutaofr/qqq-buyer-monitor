from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from src.backtest import (
    Backtester,
    _load_price_history,
    _load_research_macro_dataset,
    _macro_dataset_is_synthetic,
)
from src.collector.historical_macro_seeder import HistoricalMacroSeeder
from src.research.data_contracts import summarize_signal_expectation_coverage
from src.research.signal_expectations import build_market_expectation_matrix

WINDOWS = (
    ("dot-com", "2000-03-10", "2002-10-09"),
    ("gfc", "2007-10-09", "2009-03-09"),
    ("covid", "2020-02-19", "2020-03-23"),
    ("qt-2022", "2022-01-03", "2022-10-14"),
    ("bull-2003-2007", "2003-04-01", "2007-10-31"),
    ("bull-2009-2020", "2009-03-09", "2020-02-19"),
    ("bull-2023-now", "2023-01-03", "2026-03-20"),
)


def _window_summary(signals: pd.DataFrame, start: str, end: str) -> dict[str, object]:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    index_tz = getattr(signals.index, "tz", None)
    if index_tz is not None:
        start_ts = start_ts.tz_localize(index_tz)
        end_ts = end_ts.tz_localize(index_tz)
    window = signals.loc[(signals.index >= start_ts) & (signals.index <= end_ts)].copy()
    if window.empty:
        return {
            "rows": 0,
            "mean_actual_beta": None,
            "mean_expected_beta": None,
            "beta_match_ratio": None,
            "deployment_match_ratio": None,
        }
    beta_match = (window["signal_target_beta"] == window["expected_target_beta"]).mean()
    deploy_match = (window["deployment_state"] == window["expected_deployment_state"]).mean()
    return {
        "rows": int(len(window)),
        "mean_actual_beta": float(window["signal_target_beta"].mean()),
        "mean_expected_beta": float(window["expected_target_beta"].mean()),
        "beta_match_ratio": float(beta_match),
        "deployment_match_ratio": float(deploy_match),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run realistic dual-signal acceptance backtests")
    parser.add_argument("--cache-path", default="data/qqq_history_cache.csv")
    parser.add_argument("--macro-path", default="data/macro_historical_dump.csv")
    parser.add_argument("--registry-path", default="data/candidate_registry_v7.json")
    parser.add_argument("--beta-tolerance", type=float, default=0.10)
    parser.add_argument(
        "--save-dir",
        help="Optional directory for expectation matrix, joined daily alignment, and summary JSON",
    )
    args = parser.parse_args(argv)

    qqq = _load_price_history(args.cache_path)
    macro = _load_research_macro_dataset(args.macro_path)
    if _macro_dataset_is_synthetic(macro):
        raise ValueError(
            "Acceptance report requires a non-synthetic macro dataset. "
            "Rebuild data/macro_historical_dump.csv from canonical research data first."
        )

    logging.getLogger("src.engine.tier0_macro").setLevel(logging.ERROR)
    seeder = HistoricalMacroSeeder(mock_df=macro)
    expectations = build_market_expectation_matrix(qqq, macro_seeder=seeder)
    coverage = summarize_signal_expectation_coverage(expectations)

    tester = Backtester()
    beta_summary = tester.backtest_target_beta_alignment(
        qqq,
        expected_matrix=expectations,
        macro_seeder=seeder,
        registry_path=args.registry_path,
        tolerance=args.beta_tolerance,
    )
    deployment_summary = tester.backtest_deployment_alignment(
        qqq,
        expected_matrix=expectations,
        macro_seeder=seeder,
        registry_path=args.registry_path,
    )

    daily = beta_summary.daily_timeseries.copy()
    for column in (
        "expected_deployment_state",
        "deployment_state",
        "deployment_exact_match",
        "deployment_rank_abs_error",
        "deployment_within_one_step",
        "used_beta_floor_fallback",
        "blood_chip_override_active",
        "deployment_reason_rule",
        "deployment_reason_path",
    ):
        if column in deployment_summary.daily_timeseries.columns:
            daily[column] = deployment_summary.daily_timeseries[column]

    used_floor_fallback = daily.get("used_beta_floor_fallback", pd.Series(False, index=daily.index)).fillna(False)
    blood_chip_override_flags = daily.get(
        "blood_chip_override_active",
        pd.Series(False, index=daily.index),
    ).fillna(False).astype(bool)
    crisis_override_path_counts = (
        daily.loc[
            (daily["tier0_regime"] == "CRISIS")
            & blood_chip_override_flags
            & (daily["deployment_state"] != "DEPLOY_PAUSE"),
            "deployment_reason_path",
        ]
        .dropna()
        .astype(str)
        .value_counts()
        .sort_index()
    )
    summary = {
        "acceptance": {
            "beta_mae": float(beta_summary.mean_absolute_error),
            "beta_rmse": float(beta_summary.rmse),
            "beta_within_tolerance_ratio": float(beta_summary.within_tolerance_ratio),
            "deployment_exact_match_ratio": float(deployment_summary.exact_match_ratio),
            "deployment_mean_rank_abs_error": float(deployment_summary.mean_rank_abs_error),
            "deployment_within_one_step_ratio": float(deployment_summary.within_one_step_ratio),
            "beta_floor_respected": bool((daily["signal_target_beta"] >= 0.5 - 1e-9).all()),
            "beta_cap_respected": bool((daily["signal_target_beta"] <= 1.2 + 1e-9).all()),
            "used_beta_floor_fallback_days": int(used_floor_fallback.sum()),
            "crisis_blood_chip_overrides": int(
                (
                    (daily["tier0_regime"] == "CRISIS")
                    & blood_chip_override_flags
                    & (daily["deployment_state"] != "DEPLOY_PAUSE")
                ).sum()
            ),
            "crisis_unauthorized_breaches": int(
                (
                    (daily["tier0_regime"] == "CRISIS")
                    & ~blood_chip_override_flags
                    & (daily["deployment_state"] != "DEPLOY_PAUSE")
                ).sum()
            ),
            "crisis_blood_chip_override_paths": {
                str(path): int(count)
                for path, count in crisis_override_path_counts.items()
            },
        },
        "coverage": {
            "rows": coverage["rows"],
            "first_date": coverage["first_date"].isoformat() if coverage["first_date"] is not None else None,
            "last_date": coverage["last_date"].isoformat() if coverage["last_date"] is not None else None,
            "columns": coverage["coverage"],
        },
        "distributions": {
            "actual_beta": {str(k): int(v) for k, v in daily["signal_target_beta"].value_counts().sort_index().items()},
            "expected_beta": {str(k): int(v) for k, v in daily["expected_target_beta"].value_counts().sort_index().items()},
            "actual_deployment": {str(k): int(v) for k, v in daily["deployment_state"].value_counts().items()},
            "expected_deployment": {str(k): int(v) for k, v in daily["expected_deployment_state"].value_counts().items()},
            "risk_state": {str(k): int(v) for k, v in daily["risk_state"].value_counts().items()},
        },
        "windows": {
            name: _window_summary(daily, start, end)
            for name, start, end in WINDOWS
        },
    }

    print("\n--- Signal Acceptance Report ---")
    print(f"Rows: {coverage['rows']}")
    print(
        "Target beta alignment: "
        f"MAE={beta_summary.mean_absolute_error:.4f}, "
        f"RMSE={beta_summary.rmse:.4f}, "
        f"within_tol={beta_summary.within_tolerance_ratio:.2%}"
    )
    print(
        "Deployment alignment: "
        f"exact={deployment_summary.exact_match_ratio:.2%}, "
        f"mean_rank_abs_error={deployment_summary.mean_rank_abs_error:.4f}, "
        f"within_one_step={deployment_summary.within_one_step_ratio:.2%}"
    )
    print(
        "Beta envelope: "
        f"floor_respected={summary['acceptance']['beta_floor_respected']}, "
        f"cap_respected={summary['acceptance']['beta_cap_respected']}, "
        f"floor_fallback_days={summary['acceptance']['used_beta_floor_fallback_days']}"
    )
    print(
        "CRISIS audit: "
        f"blood_chip_overrides={summary['acceptance']['crisis_blood_chip_overrides']}, "
        f"unauthorized_breaches={summary['acceptance']['crisis_unauthorized_breaches']}"
    )
    if not crisis_override_path_counts.empty:
        path_summary = ", ".join(
            f"{path}={count}" for path, count in crisis_override_path_counts.items()
        )
        print(f"CRISIS override paths: {path_summary}")
    for name, window_summary in summary["windows"].items():
        print(
            f"{name}: rows={window_summary['rows']}, "
            f"actual_beta={window_summary['mean_actual_beta']}, "
            f"expected_beta={window_summary['mean_expected_beta']}, "
            f"beta_match={window_summary['beta_match_ratio']}, "
            f"deployment_match={window_summary['deployment_match_ratio']}"
        )

    if args.save_dir:
        save_dir = Path(args.save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        expectations.to_csv(save_dir / "market_expectations.csv", index=False)
        daily.reset_index().to_csv(save_dir / "daily_signal_alignment.csv", index=False)
        with (save_dir / "signal_acceptance_summary.json").open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)
        print(f"Saved acceptance artifacts to {save_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
