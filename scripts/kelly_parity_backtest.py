import argparse
import json
from pathlib import Path

from src.backtest import run_v11_audit


def main(argv=None):
    parser = argparse.ArgumentParser(description="V15 Backtest Parity Diagnostics")
    parser.add_argument("--output-dir", default="artifacts/kelly_parity")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_b = run_v11_audit(
        artifact_dir=str(output_dir / "treatment_kelly"),
        experiment_config={
            "use_canonical_pipeline": True,
        }
    )

    metrics = {
        "top1_accuracy": summary_b.get("top1_accuracy"),
        "mean_brier": summary_b.get("mean_brier"),
        "mean_entropy": summary_b.get("mean_entropy"),
        "lock_incidence": summary_b.get("lock_incidence"),
        "compared_points": summary_b.get("compared_points"),
        "posterior_mode": summary_b.get("posterior_mode"),
        "var_smoothing": summary_b.get("gaussian_nb_var_smoothing", summary_b.get("var_smoothing")),
    }

    (output_dir / "parity_summary.json").write_text(json.dumps(metrics, indent=2) + "\n")

    def _fmt_pct(v):
        return f"{v * 100:.2f}%" if v is not None else "N/A"

    def _fmt_dec(v):
        return f"{v:.4f}" if v is not None else "N/A"

    report_lines = [
        "# V15 Backtest Parity Report",
        "",
        "## Core Inference Metrics (Architectural Diagnostics)",
        "",
        f"- **Top-1 Accuracy**: {_fmt_pct(metrics['top1_accuracy'])} (Expected: 50%-60%)",
        f"- **Mean Brier Score**: {_fmt_dec(metrics['mean_brier'])}",
        f"- **Mean Entropy**: {_fmt_dec(metrics['mean_entropy'])}",
        f"- **Lock Incidence**: {_fmt_pct(metrics['lock_incidence'])}",
        f"- **Compared Points**: {metrics['compared_points']}",
        "",
        "## Configuration Transmitted",
        f"- Posterior Mode: {metrics['posterior_mode']}",
        f"- Var Smoothing: {metrics['var_smoothing']}",
        "",
        "© 2026 QQQ Entropy AI Governance",
    ]

    (output_dir / "parity_report.md").write_text("\n".join(report_lines) + "\n")
    print(f"\n[kelly_parity] Report successfully written to {output_dir}")


if __name__ == "__main__":
    main()
