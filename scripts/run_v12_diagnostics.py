"""Generate the v12 diagnostic protocol report from existing audit artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.engine.v11.probability_seeder import ProbabilitySeeder
from src.research.v12_diagnostics import (
    build_v12_diagnostic_report,
    write_v12_diagnostic_report,
)


def _load_audit_regimes(audit_contract_path: Path) -> list[str]:
    with audit_contract_path.open(encoding="utf-8") as handle:
        audit_data = json.load(handle)
    return list(audit_data.get("base_betas", {}).keys())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the v12 diagnostic protocol on backtest artifacts."
    )
    parser.add_argument("--audit-path", default="artifacts/v12_audit/full_audit.csv")
    parser.add_argument("--regime-path", default="data/v11_poc_phase1_results.csv")
    parser.add_argument("--dataset-path", default="data/macro_historical_dump.csv")
    parser.add_argument(
        "--audit-contract-path", default="src/engine/v11/resources/regime_audit.json"
    )
    parser.add_argument("--output-dir", default="artifacts/v12_diagnostics")
    args = parser.parse_args(argv)

    audit_frame = pd.read_csv(args.audit_path, parse_dates=["date"])
    label_frame = pd.read_csv(args.regime_path, parse_dates=["observation_date"])
    macro_frame = pd.read_csv(args.dataset_path, parse_dates=["observation_date"]).set_index(
        "observation_date"
    )

    seeder = ProbabilitySeeder()
    seeder.generate_features(macro_frame)
    feature_diag_frame = seeder.latest_diagnostics()

    report = build_v12_diagnostic_report(
        audit_frame,
        label_frame=label_frame,
        audit_regimes=_load_audit_regimes(Path(args.audit_contract_path)),
        feature_diag_frame=feature_diag_frame,
    )
    path = write_v12_diagnostic_report(report, args.output_dir)

    print(f"Wrote v12 diagnostic report to {path}")
    print(
        "Top-1 "
        f"{report['summary']['top1_accuracy']:.2%} | "
        f"Stable critical recall {report['critical_regime_performance']['stable_critical_recall']:.2%} | "
        f"Unsupported states {report['state_support']['unsupported_audit_regimes']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
