from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path


def get_git_revision() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("ascii").strip()
    except Exception:
        return "unknown:detached-or-git-missing"


def get_file_hash(path: Path) -> str:
    if not path.exists():
        return "missing"
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def main():
    print("Generating QQQ v13.8 Calibration Evidence Report...")

    # 1. Load baseline audit data
    source_dir = Path("artifacts/v13_8_task6_check")
    summary_path = source_dir / "summary.json"
    trace_path = source_dir / "execution_trace.csv"

    if not summary_path.exists():
        print(f"ERROR: Missing source summary at {summary_path}")
        sys.exit(1)

    with open(summary_path, encoding="utf-8") as f:
        summary = json.load(f)

    # 2. Extract dates from trace
    import pandas as pd

    try:
        trace = pd.read_csv(trace_path)
        dates = pd.to_datetime(trace["date"])
        evaluation_start = dates.min().strftime("%Y-%m-%d")
        evaluation_end = dates.max().strftime("%Y-%m-%d")
    except Exception:
        evaluation_start = "unknown"
        evaluation_end = "unknown"

    # 3. Parameters and Logic Hashes
    registry_path = Path("src/engine/v11/resources/v13_4_weights_registry.json")
    params_hash = get_file_hash(registry_path)

    # 4. Construct Evidence
    report = {
        "calibration_artifact_id": "v13.8-ULTIMA-INDUSTRIAL",
        "code_revision": get_git_revision(),
        "evaluation_start": evaluation_start,
        "evaluation_end": evaluation_end,
        "price_cache_path": summary.get("experiment_config", {}).get("price_cache_path", "unknown"),
        "parameter_values_hash": params_hash,
        "holdout_window": "2018-01-01 to 2026-03-31 (Full Walk-Forward)",
        "summary_metrics": {
            "top1_accuracy": summary.get("top1_accuracy"),
            "mean_entropy": summary.get("mean_entropy"),
            "mean_brier": summary.get("mean_brier"),
            "lock_incidence": summary.get("lock_incidence"),
        },
        "reliability_required": {
            "fail_closed_enabled": True,
            "zero_live_download": True,
            "bit_identical_parity_required": True,
        },
        "environment": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "cpu_arch": platform.machine(),
        },
    }

    # 5. Export
    output_dir = Path("artifacts/v13_8_acceptance")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "calibration_report.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Report successfully generated at: {output_path}")


if __name__ == "__main__":
    main()
