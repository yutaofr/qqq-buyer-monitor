from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd  # noqa: E402

from src.research.regime_process_audit import compute_regime_process_alignment  # noqa: E402
from src.research.worldview_benchmark import build_worldview_benchmark  # noqa: E402

REGIMES = ("MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY")
WINDOWS: dict[str, tuple[str, str]] = {
    "2018_Q4": ("2018-09-01", "2019-01-31"),
    "2020_COVID": ("2020-02-15", "2020-05-15"),
    "2022_TIGHTENING": ("2021-12-15", "2022-07-15"),
    "2023_RECOVERY": ("2022-11-01", "2023-04-15"),
    "2024_PULLBACK": ("2024-07-01", "2024-11-15"),
}


def _load_price_benchmark(price_cache_path: Path) -> pd.DataFrame:
    prices = pd.read_csv(price_cache_path, parse_dates=["Date"])[["Date", "Close", "Volume"]]
    prices["Date"] = pd.to_datetime(prices["Date"], utc=True).dt.tz_convert(None).dt.normalize()
    prices = prices.rename(columns={"Date": "date"}).drop_duplicates("date").sort_values("date")
    benchmark = build_worldview_benchmark(prices.set_index("date"))
    return benchmark.reset_index().rename(columns={"index": "date"})


def _load_trace(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if "date" not in frame.columns:
        first = frame.columns[0]
        if first.startswith("Unnamed"):
            frame = frame.rename(columns={first: "date"})
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    return frame.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


def _window_summary(merged: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for window_name, (start, end) in WINDOWS.items():
        frame = merged[
            (merged["date"] >= pd.Timestamp(start)) & (merged["date"] <= pd.Timestamp(end))
        ].copy()
        if frame.empty:
            continue
        prob_hits = []
        delta_hits = []
        accel_hits = []
        for regime in REGIMES:
            prob_hits.append(
                frame[f"prob_{regime}"].between(
                    frame[f"benchmark_prob_lower_{regime}"],
                    frame[f"benchmark_prob_upper_{regime}"],
                )
            )
            delta_hits.append(
                frame[f"prob_delta_{regime}"].between(
                    frame[f"benchmark_prob_delta_lower_{regime}"],
                    frame[f"benchmark_prob_delta_upper_{regime}"],
                )
            )
            accel_hits.append(
                frame[f"prob_acceleration_{regime}"].between(
                    frame[f"benchmark_prob_acceleration_lower_{regime}"],
                    frame[f"benchmark_prob_acceleration_upper_{regime}"],
                )
            )
        rows.append(
            {
                "window": window_name,
                "rows": int(len(frame)),
                "stable_vs_benchmark_regime": float(
                    (frame["stable_regime"] == frame["benchmark_regime"]).mean()
                ),
                "probability_within_band_share": float(pd.concat(prob_hits, axis=1).stack().mean()),
                "delta_within_band_share": float(pd.concat(delta_hits, axis=1).stack().mean()),
                "acceleration_within_band_share": float(
                    pd.concat(accel_hits, axis=1).stack().mean()
                ),
                "transition_intensity_mean": float(
                    pd.to_numeric(frame["benchmark_transition_intensity"], errors="coerce").mean()
                ),
            }
        )
    return pd.DataFrame(rows)


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows_"
    lines = [
        "| " + " | ".join(map(str, df.columns)) + " |",
        "| " + " | ".join([":---"] * len(df.columns)) + " |",
    ]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in df.columns) + " |")
    return "\n".join(lines)


def _write_report(
    path: Path,
    *,
    summaries: dict[str, dict[str, Any]],
    window_tables: dict[str, pd.DataFrame],
) -> None:
    lines = ["# Regime Process Panorama", ""]
    for name, summary in summaries.items():
        overall = summary["overall"]
        lines.extend(
            [
                f"## {name}",
                "",
                f"- Rows: `{overall['rows']}`",
                f"- Stable vs benchmark regime: `{overall['stable_vs_benchmark_regime']:.2%}`",
                f"- Probability within 1-delta share: `{overall['probability_within_band_share']:.2%}`",
                f"- Delta within 1-delta share: `{overall['delta_within_band_share']:.2%}`",
                f"- Acceleration within 1-delta share: `{overall['acceleration_within_band_share']:.2%}`",
                f"- Transition rows: `{overall['transition_rows']}`",
                f"- Transition probability within 1-delta share: `{overall['transition_probability_within_band_share']:.2%}`",
                "",
                _markdown_table(window_tables[name].round(4)),
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run regime-process panorama audit for mainline and shadow traces."
    )
    parser.add_argument("--price-cache-path", default="data/qqq_history_cache.csv")
    parser.add_argument(
        "--mainline-trace-path", default="artifacts/v14_panorama/mainline/full_audit.csv"
    )
    parser.add_argument(
        "--shadow-trace-path",
        default="artifacts/recovery_hmm_shadow/variant_panorama_8yr/recovery_accelerated/shadow_trace.csv",
    )
    parser.add_argument("--artifact-dir", default="artifacts/regime_process_panorama")
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)

    benchmark = _load_price_benchmark(Path(args.price_cache_path))
    benchmark.to_csv(artifact_dir / "benchmark_trace.csv", index=False)

    traces = {
        "mainline": _load_trace(Path(args.mainline_trace_path)),
        "shadow": _load_trace(Path(args.shadow_trace_path)),
    }
    summaries: dict[str, dict[str, Any]] = {}
    window_tables: dict[str, pd.DataFrame] = {}

    for name, trace in traces.items():
        merged, summary = compute_regime_process_alignment(trace, benchmark)
        summaries[name] = summary
        merged.to_csv(artifact_dir / f"{name}_merged.csv", index=False)
        by_regime = pd.DataFrame(summary["by_regime"])
        by_regime.to_csv(artifact_dir / f"{name}_by_regime.csv", index=False)
        windows = _window_summary(merged)
        windows.to_csv(artifact_dir / f"{name}_windows.csv", index=False)
        window_tables[name] = windows

    (artifact_dir / "summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    _write_report(artifact_dir / "report.md", summaries=summaries, window_tables=window_tables)
    print(
        {
            "artifact_dir": str(artifact_dir),
            "summary_path": str(artifact_dir / "summary.json"),
            "report_path": str(artifact_dir / "report.md"),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
