"""Run a deterministic v13 cold-start and warm-start validation from frozen market cache."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.engine.v11.conductor import V11Conductor
from src.main import _build_v11_signal_result
from src.output.discord_notifier import build_discord_payload
from src.output.web_exporter import export_web_snapshot


def _load_validation_row(macro_path: str, price_cache_path: str) -> pd.DataFrame:
    macro_df = pd.read_csv(macro_path, parse_dates=["observation_date"]).set_index(
        "observation_date"
    )
    price_df = pd.read_csv(price_cache_path)
    price_df["Date"] = (
        pd.to_datetime(price_df["Date"], utc=True).dt.tz_localize(None).dt.normalize()
    )
    price_df = price_df.set_index("Date")

    common_dates = macro_df.index.intersection(price_df.index)
    if common_dates.empty:
        raise ValueError("No common frozen date between macro history and QQQ cache.")

    as_of = common_dates.max()
    row = macro_df.loc[[as_of]].copy()
    row["qqq_close"] = float(price_df.loc[as_of, "Close"])
    row["source_qqq_close"] = "direct:yfinance:cached"
    row["qqq_close_quality_score"] = 1.0
    row["qqq_volume"] = float(price_df.loc[as_of, "Volume"])
    row["source_qqq_volume"] = "direct:yfinance:cached"
    row["qqq_volume_quality_score"] = 1.0
    row["adv_dec_ratio"] = np.nan
    row["source_breadth_proxy"] = "unavailable:breadth"
    row["breadth_quality_score"] = 0.0
    row["ndx_concentration"] = np.nan
    row["source_ndx_concentration"] = "unavailable:ndx_concentration"
    row["ndx_concentration_quality_score"] = 0.0
    row["reference_capital"] = float(
        row.get("reference_capital", pd.Series([100_000.0])).iloc[0] or 100_000.0
    )
    row["current_nav"] = float(row.get("current_nav", pd.Series([100_000.0])).iloc[0] or 100_000.0)
    return row


def _run_once(
    *,
    row: pd.DataFrame,
    macro_path: str,
    regime_path: str,
    prior_state_path: Path,
    snapshot_dir: Path,
    web_status_path: Path,
    discord_payload_path: Path,
) -> dict[str, Any]:
    conductor = V11Conductor(
        macro_data_path=macro_path,
        regime_data_path=regime_path,
        prior_state_path=str(prior_state_path),
        snapshot_dir=str(snapshot_dir),
    )
    runtime = conductor.daily_run(row)
    signal = _build_v11_signal_result(runtime, price=float(row["qqq_close"].iloc[0]))
    export_web_snapshot(signal, output_path=web_status_path)
    discord_payload_path.write_text(
        json.dumps(build_discord_payload(signal), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {
        "date": str(runtime["date"]),
        "stable_regime": str(runtime["stable_regime"]),
        "raw_regime": str(runtime["raw_regime"]),
        "target_beta": float(runtime["target_beta"]),
        "raw_target_beta": float(runtime["raw_target_beta"]),
        "protected_beta": float(runtime["protected_beta"]),
        "overlay_beta": float(runtime["overlay_beta"]),
        "overlay_mode": str(runtime["overlay"]["overlay_mode"]),
        "overlay_state": str(runtime["overlay"]["overlay_state"]),
        "overlay_summary": str(runtime["overlay"]["overlay_summary"]),
        "deployment_state": str(runtime["deployment"]["deployment_state"]),
        "entropy": float(runtime["entropy"]),
        "snapshot_dir": str(snapshot_dir),
        "web_status_path": str(web_status_path),
        "discord_payload_path": str(discord_payload_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic v13 cold/warm validation.")
    parser.add_argument("--macro-path", default="data/macro_historical_dump.csv")
    parser.add_argument("--regime-path", default="data/v11_poc_phase1_results.csv")
    parser.add_argument("--price-cache-path", default="data/qqq_history_cache.csv")
    parser.add_argument("--output-dir", default="artifacts/v13_runtime_validation")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    row = _load_validation_row(args.macro_path, args.price_cache_path)
    prior_state_path = output_dir / "prior_state.json"

    cold = _run_once(
        row=row,
        macro_path=args.macro_path,
        regime_path=args.regime_path,
        prior_state_path=prior_state_path,
        snapshot_dir=output_dir / "cold_snapshots",
        web_status_path=output_dir / "cold_status.json",
        discord_payload_path=output_dir / "cold_discord_payload.json",
    )
    warm = _run_once(
        row=row,
        macro_path=args.macro_path,
        regime_path=args.regime_path,
        prior_state_path=prior_state_path,
        snapshot_dir=output_dir / "warm_snapshots",
        web_status_path=output_dir / "warm_status.json",
        discord_payload_path=output_dir / "warm_discord_payload.json",
    )

    summary = {
        "observation_date": str(row.index[-1].date()),
        "cold": cold,
        "warm": warm,
        "delta": {
            "target_beta": float(warm["target_beta"] - cold["target_beta"]),
            "raw_target_beta": float(warm["raw_target_beta"] - cold["raw_target_beta"]),
            "entropy": float(warm["entropy"] - cold["entropy"]),
        },
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
