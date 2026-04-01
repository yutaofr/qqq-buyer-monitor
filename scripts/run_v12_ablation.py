"""Run controlled v12 ablations and compare them against the baseline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.backtest import run_v11_audit
from src.engine.v11.probability_seeder import ProbabilitySeeder
from src.research.v12_diagnostics import build_v12_diagnostic_report, write_v12_diagnostic_report

EXPERIMENTS: dict[str, dict[str, Any]] = {
    "baseline": {},
    "var_smoothing_1e3": {"var_smoothing": 1e-3},
    "var_smoothing_1e4": {"var_smoothing": 1e-4},
    "var_smoothing_1e5": {"var_smoothing": 1e-5},
    "var_smoothing_1e6": {"var_smoothing": 1e-6},
    "clip_12": {"probability_seeder": {"clip_range": (-12.0, 12.0)}},
    "roc_63d": {
        "probability_seeder": {
            "config_overrides": {
                "copper_gold_roc_126d": {"diff": (63,), "min_periods": 63},
                "usdjpy_roc_126d": {"diff": (63,), "min_periods": 63},
            }
        }
    },
    "roc_21d": {
        "probability_seeder": {
            "config_overrides": {
                "copper_gold_roc_126d": {"diff": (21,), "min_periods": 21},
                "usdjpy_roc_126d": {"diff": (21,), "min_periods": 21},
            }
        }
    },
    "capex_ewma3": {
        "probability_seeder": {
            "config_overrides": {
                "core_capex_momentum": {"ewma_span": 3},
            }
        }
    },
    "move_orth_none": {
        "probability_seeder": {
            "orthogonalization_mode": "none",
        }
    },
    "move_orth_half": {
        "probability_seeder": {
            "orthogonalization_strength": 0.5,
        }
    },
    "var1e4_capex_ewma3": {
        "var_smoothing": 1e-4,
        "probability_seeder": {
            "config_overrides": {
                "core_capex_momentum": {"ewma_span": 3},
            }
        },
    },
    "var1e4_clip12": {
        "var_smoothing": 1e-4,
        "probability_seeder": {"clip_range": (-12.0, 12.0)},
    },
    "var1e4_move_half": {
        "var_smoothing": 1e-4,
        "probability_seeder": {"orthogonalization_strength": 0.5},
    },
    "states_4_baseline": {
        "audit_overrides": {
            "base_betas": {
                "BUST": 0.5,
                "RECOVERY": 1.1,
                "LATE_CYCLE": 0.8,
                "MID_CYCLE": 1.0,
            },
            "regime_sharpes": {
                "BUST": -0.8,
                "RECOVERY": 1.2,
                "LATE_CYCLE": 0.2,
                "MID_CYCLE": 1.0,
            },
        }
    },
    "states_4_var1e4": {
        "var_smoothing": 1e-4,
        "audit_overrides": {
            "base_betas": {
                "BUST": 0.5,
                "RECOVERY": 1.1,
                "LATE_CYCLE": 0.8,
                "MID_CYCLE": 1.0,
            },
            "regime_sharpes": {
                "BUST": -0.8,
                "RECOVERY": 1.2,
                "LATE_CYCLE": 0.2,
                "MID_CYCLE": 1.0,
            },
        }
    },
    "states_4_var1e4_capex": {
        "var_smoothing": 1e-4,
        "audit_overrides": {
            "base_betas": {
                "BUST": 0.5,
                "RECOVERY": 1.1,
                "LATE_CYCLE": 0.8,
                "MID_CYCLE": 1.0,
            },
            "regime_sharpes": {
                "BUST": -0.8,
                "RECOVERY": 1.2,
                "LATE_CYCLE": 0.2,
                "MID_CYCLE": 1.0,
            },
        },
        "probability_seeder": {
            "config_overrides": {
                "core_capex_momentum": {"ewma_span": 3},
            }
        },
    },
    "classifier_only_var1e4_capex": {
        "var_smoothing": 1e-4,
        "posterior_mode": "classifier_only",
        "probability_seeder": {
            "config_overrides": {
                "core_capex_momentum": {"ewma_span": 3},
            }
        },
    },
    "classifier_only_var1e5_capex": {
        "var_smoothing": 1e-5,
        "posterior_mode": "classifier_only",
        "probability_seeder": {
            "config_overrides": {
                "core_capex_momentum": {"ewma_span": 3},
            }
        },
    },
    "classifier_only_var1e6_capex": {
        "var_smoothing": 1e-6,
        "posterior_mode": "classifier_only",
        "probability_seeder": {
            "config_overrides": {
                "core_capex_momentum": {"ewma_span": 3},
            }
        },
    },
}


def _load_audit_regimes(audit_contract_path: Path) -> list[str]:
    with audit_contract_path.open(encoding="utf-8") as handle:
        audit_data = json.load(handle)
    return list(audit_data.get("base_betas", {}).keys())


def _flatten_report(name: str, report: dict[str, Any]) -> dict[str, Any]:
    summary = report["summary"]
    critical = report["critical_regime_performance"]
    covid = report["crisis_windows"]["2020_COVID"]
    q4_2018 = report["crisis_windows"]["2018Q4"]
    h1_2022 = report["crisis_windows"]["2022_H1"]
    beta = report["beta_comparison"]["overall"]
    return {
        "experiment": name,
        "top1_accuracy": summary["top1_accuracy"],
        "stable_accuracy": summary["stable_accuracy"],
        "mean_brier": summary["mean_brier"],
        "mean_entropy": summary["mean_entropy"],
        "lock_incidence": summary["lock_incidence"],
        "stable_critical_recall": critical["stable_critical_recall"],
        "raw_critical_recall": critical["raw_critical_recall"],
        "2018Q4_stable_recall": q4_2018["stable_critical_recall"],
        "2020_stable_recall": covid["stable_critical_recall"],
        "2022H1_stable_recall": h1_2022["stable_critical_recall"],
        "overall_final_return": beta["final_total_return"],
        "overall_final_drawdown": beta["final_max_drawdown"],
        "overall_raw_return": beta["raw_total_return"],
        "overall_raw_drawdown": beta["raw_max_drawdown"],
        "mean_beta_gap": beta["mean_beta_gap"],
        "audit_regime_count": len(report["state_support"]["audit_regimes"]),
        "unsupported_states": ",".join(report["state_support"]["unsupported_audit_regimes"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run controlled v12 ablation experiments.")
    parser.add_argument("--dataset-path", default="data/macro_historical_dump.csv")
    parser.add_argument("--regime-path", default="data/v11_poc_phase1_results.csv")
    parser.add_argument("--evaluation-start", default="2018-01-01")
    parser.add_argument("--audit-contract-path", default="src/engine/v11/resources/regime_audit.json")
    parser.add_argument("--output-dir", default="artifacts/v12_ablations")
    parser.add_argument(
        "--experiments",
        default=",".join(EXPERIMENTS.keys()),
        help="Comma-separated experiment names.",
    )
    args = parser.parse_args(argv)

    selected = [name.strip() for name in args.experiments.split(",") if name.strip()]
    unknown = [name for name in selected if name not in EXPERIMENTS]
    if unknown:
        raise ValueError(f"Unknown experiment names: {', '.join(unknown)}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_regimes = _load_audit_regimes(Path(args.audit_contract_path))
    label_frame = pd.read_csv(args.regime_path, parse_dates=["observation_date"])
    macro_frame = pd.read_csv(args.dataset_path, parse_dates=["observation_date"]).set_index("observation_date")

    comparison_rows: list[dict[str, Any]] = []
    reports: dict[str, dict[str, Any]] = {}
    for name in selected:
        experiment = EXPERIMENTS[name]
        experiment_dir = output_dir / name
        experiment_dir.mkdir(parents=True, exist_ok=True)
        experiment_audit_regimes = list(
            dict(experiment.get("audit_overrides", {}).get("base_betas", {})).keys()
        ) or audit_regimes

        run_v11_audit(
            dataset_path=args.dataset_path,
            regime_path=args.regime_path,
            evaluation_start=args.evaluation_start,
            artifact_dir=str(experiment_dir),
            experiment_config=experiment,
        )
        audit_frame = pd.read_csv(experiment_dir / "full_audit.csv", parse_dates=["date"])
        seeder = ProbabilitySeeder(**dict(experiment.get("probability_seeder", {})))
        seeder.generate_features(macro_frame)
        report = build_v12_diagnostic_report(
            audit_frame,
            label_frame=label_frame,
            audit_regimes=experiment_audit_regimes,
            feature_diag_frame=seeder.latest_diagnostics(),
        )
        write_v12_diagnostic_report(report, experiment_dir / "diagnostics")
        reports[name] = report
        comparison_rows.append(_flatten_report(name, report))

    comparison = pd.DataFrame(comparison_rows).sort_values(
        ["stable_critical_recall", "top1_accuracy", "mean_brier"],
        ascending=[False, False, True],
    )
    comparison.to_csv(output_dir / "comparison.csv", index=False)
    (output_dir / "comparison.json").write_text(
        json.dumps(reports, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    print(comparison.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
