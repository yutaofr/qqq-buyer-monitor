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
from src.output.backtest_plots import save_deployment_pacing_figure
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


def _window_summary(signals: pd.DataFrame, start: str, end: str, *, tolerance: float) -> dict[str, object]:
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
            "actual_mean_pacing": None,
            "expected_mean_pacing": None,
            "mae": None,
            "rmse": None,
            "error_variance": None,
            "within_tolerance_ratio": None,
            "actual_cash_total": None,
            "expected_cash_total": None,
        }

    error = pd.to_numeric(window["deployment_pacing_error"], errors="coerce")
    compared = window.loc[error.notna()].copy()
    if compared.empty:
        return {
            "rows": 0,
            "actual_mean_pacing": None,
            "expected_mean_pacing": None,
            "mae": None,
            "rmse": None,
            "error_variance": None,
            "within_tolerance_ratio": None,
            "actual_cash_total": None,
            "expected_cash_total": None,
        }

    error = pd.to_numeric(compared["deployment_pacing_error"], errors="coerce")
    return {
        "rows": int(len(compared)),
        "actual_mean_pacing": float(pd.to_numeric(compared["deployment_multiplier"], errors="coerce").mean()),
        "expected_mean_pacing": float(
            pd.to_numeric(compared["expected_deployment_multiplier"], errors="coerce").mean()
        ),
        "mae": float(error.abs().mean()),
        "rmse": float((error.pow(2).mean()) ** 0.5),
        "error_variance": float(error.var(ddof=0)),
        "within_tolerance_ratio": float((error.abs() <= tolerance).mean()),
        "actual_cash_total": float(
            pd.to_numeric(compared["actual_deployment_cash"], errors="coerce").sum()
        ),
        "expected_cash_total": float(
            pd.to_numeric(compared["expected_deployment_cash"], errors="coerce").sum()
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the v10 incremental-cash deployment pacing backtest report",
    )
    parser.add_argument("--cache-path", default="data/qqq_history_cache.csv")
    parser.add_argument("--macro-path", default="data/macro_historical_dump.csv")
    parser.add_argument("--registry-path", default="data/candidate_registry_v7.json")
    parser.add_argument("--tolerance", type=float, default=0.25)
    parser.add_argument("--save-dir", default="artifacts/v10_pacing_acceptance")
    parser.add_argument(
        "--docs-image-path",
        default="docs/images/v10.0_deployment_pacing_backtest.png",
        help="Optional mirrored docs image path for the pacing figure",
    )
    args = parser.parse_args(argv)

    qqq = _load_price_history(args.cache_path)
    macro = _load_research_macro_dataset(args.macro_path)
    if _macro_dataset_is_synthetic(macro):
        raise ValueError(
            "Deployment pacing report requires a non-synthetic macro dataset. "
            "Rebuild data/macro_historical_dump.csv from canonical research data first."
        )

    logging.getLogger("src.engine.tier0_macro").setLevel(logging.ERROR)
    seeder = HistoricalMacroSeeder(mock_df=macro)
    expectations = build_market_expectation_matrix(qqq, macro_seeder=seeder)
    coverage = summarize_signal_expectation_coverage(expectations)

    tester = Backtester()
    pacing_summary = tester.backtest_deployment_pacing_alignment(
        qqq,
        expected_matrix=expectations,
        macro_seeder=seeder,
        registry_path=args.registry_path,
        tolerance=args.tolerance,
    )
    deployment_summary = tester.backtest_deployment_alignment(
        qqq,
        expected_matrix=expectations,
        macro_seeder=seeder,
        registry_path=args.registry_path,
    )

    daily = pacing_summary.daily_timeseries.copy()
    windows = {
        name: _window_summary(daily, start, end, tolerance=args.tolerance)
        for name, start, end in WINDOWS
    }
    summary = {
        "pacing": {
            "compared_points": pacing_summary.compared_points,
            "mean_error": pacing_summary.mean_error,
            "mean_absolute_error": pacing_summary.mean_absolute_error,
            "rmse": pacing_summary.rmse,
            "error_variance": pacing_summary.error_variance,
            "error_std_dev": pacing_summary.error_std_dev,
            "correlation": pacing_summary.correlation,
            "explained_variance": pacing_summary.explained_variance,
            "within_tolerance_ratio": pacing_summary.within_tolerance_ratio,
            "actual_mean_pacing": pacing_summary.actual_mean_pacing,
            "expected_mean_pacing": pacing_summary.expected_mean_pacing,
            "cash_mean_absolute_error": pacing_summary.cash_mean_absolute_error,
            "cash_rmse": pacing_summary.cash_rmse,
            "categorical_exact_match_ratio": deployment_summary.exact_match_ratio,
            "categorical_within_one_step_ratio": deployment_summary.within_one_step_ratio,
        },
        "coverage": {
            "rows": coverage["rows"],
            "first_date": coverage["first_date"].isoformat() if coverage["first_date"] is not None else None,
            "last_date": coverage["last_date"].isoformat() if coverage["last_date"] is not None else None,
            "columns": coverage["coverage"],
        },
        "windows": windows,
    }

    print("\n--- Deployment Pacing Backtest Report ---")
    print(f"Rows: {coverage['rows']}")
    print(
        "Pacing alignment: "
        f"MAE={pacing_summary.mean_absolute_error:.4f}, "
        f"RMSE={pacing_summary.rmse:.4f}, "
        f"Var={pacing_summary.error_variance:.6f}, "
        f"within_tol={pacing_summary.within_tolerance_ratio:.2%}"
    )
    print(
        "Cash pacing: "
        f"cash_mae={pacing_summary.cash_mean_absolute_error:.2f}, "
        f"cash_rmse={pacing_summary.cash_rmse:.2f}"
    )
    print(
        "Categorical overlay: "
        f"exact={deployment_summary.exact_match_ratio:.2%}, "
        f"within_one_step={deployment_summary.within_one_step_ratio:.2%}"
    )
    for name, window_summary in windows.items():
        print(
            f"{name}: rows={window_summary['rows']}, "
            f"actual_mean_pacing={window_summary['actual_mean_pacing']}, "
            f"expected_mean_pacing={window_summary['expected_mean_pacing']}, "
            f"mae={window_summary['mae']}, "
            f"within_tol={window_summary['within_tolerance_ratio']}"
        )

    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    expectations.to_csv(save_dir / "market_expectations.csv", index=False)
    daily.reset_index().to_csv(save_dir / "deployment_pacing_daily.csv", index=False)
    pd.DataFrame.from_dict(windows, orient="index").reset_index(names="window").to_csv(
        save_dir / "deployment_pacing_windows.csv",
        index=False,
    )
    with (save_dir / "deployment_pacing_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    figure_paths = [save_dir / "deployment_pacing_backtest.png"]
    if args.docs_image_path:
        figure_paths.append(Path(args.docs_image_path))
    saved_paths = save_deployment_pacing_figure(
        daily,
        pacing_summary,
        figure_paths,
    )
    print("Saved deployment pacing artifacts to " + ", ".join(str(path) for path in saved_paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
