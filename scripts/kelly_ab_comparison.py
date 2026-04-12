"""
A/B Comparison: True Kelly (6 variants) vs Pseudo Kelly Baseline.

Usage (in container):
    python scripts/kelly_ab_comparison.py \
        --trace-path artifacts/v12_audit/execution_trace.csv \
        --regime-audit src/engine/v11/resources/regime_audit.json \
        --output-dir artifacts/kelly_ab

Output:
    artifacts/kelly_ab/ab_summary.json   -- 机器可读 JSON
    artifacts/kelly_ab/ab_report.md      -- 人类可读 Markdown 对比报告
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from src.engine.v11.core.kelly_criterion import (
    compute_kelly_fraction,
    kelly_fraction_to_deployment_state,
)

# 实验矩阵
VARIANTS = [
    {"id": "half_erp_low",     "kelly_scale": 0.5,  "erp_weight": 0.2},
    {"id": "half_erp_mid",     "kelly_scale": 0.5,  "erp_weight": 0.4},
    {"id": "half_erp_high",    "kelly_scale": 0.5,  "erp_weight": 0.8},
    {"id": "quarter_erp_low",  "kelly_scale": 0.25, "erp_weight": 0.2},
    {"id": "quarter_erp_mid",  "kelly_scale": 0.25, "erp_weight": 0.4},
    {"id": "quarter_erp_high", "kelly_scale": 0.25, "erp_weight": 0.8},
]

REGIME_ORDER = ["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"]


def _load_trace(trace_path: str) -> pd.DataFrame:
    """
    加载 execution_trace.csv，提取每行的 posterior 概率、entropy、erp 和 actual_regime。
    """
    df = pd.read_csv(trace_path)
    required = ["actual_regime", "entropy", "prob_MID_CYCLE", "prob_LATE_CYCLE", "prob_BUST", "prob_RECOVERY"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required col: {col}")
    if "erp_percentile" not in df.columns:
        if "target_beta" in df.columns:
            beta_min = 0.5
            beta_max = 1.2
            beta_norm = (df["target_beta"].clip(beta_min, beta_max) - beta_min) / (beta_max - beta_min)
            df["erp_percentile"] = (1.0 - beta_norm).clip(0.0, 1.0)
        else:
            df["erp_percentile"] = 0.5
    return df


def _compute_all_variant_decisions(
    trace: pd.DataFrame,
    regime_sharpes: dict[str, float],
) -> pd.DataFrame:
    """
    对 trace 的每一行，计算所有 6 个 True Kelly 变体的 kelly_fraction 和 deployment_state。
    返回 DataFrame，列名格式: {variant_id}_fraction, {variant_id}_state
    """
    df = trace.copy()

    for variant in VARIANTS:
        vid = variant["id"]
        ks = variant["kelly_scale"]
        ew = variant["erp_weight"]

        fractions = []
        states = []

        for _idx, row in df.iterrows():
            posteriors = {
                "MID_CYCLE": float(row["prob_MID_CYCLE"]),
                "LATE_CYCLE": float(row["prob_LATE_CYCLE"]),
                "BUST": float(row["prob_BUST"]),
                "RECOVERY": float(row["prob_RECOVERY"])
            }
            f = compute_kelly_fraction(
                posteriors=posteriors,
                regime_sharpes=regime_sharpes,
                entropy=float(row["entropy"]),
                erp_percentile=float(row["erp_percentile"]),
                kelly_scale=ks,
                erp_weight=ew
            )
            s = kelly_fraction_to_deployment_state(f)
            fractions.append(f)
            states.append(s)

        df[f"{vid}_fraction"] = fractions
        df[f"{vid}_state"] = states

    return df


def _compute_metrics(
    trace: pd.DataFrame,
    pseudo_kelly_col: str = "deployment_state",
) -> dict:
    """
    计算每个变体的对比指标
    """
    metrics = {}

    variant_cols = [v["id"] for v in VARIANTS]
    if pseudo_kelly_col in trace.columns:
        variant_ids = variant_cols + ["pseudo_kelly"]
    else:
        variant_ids = variant_cols

    for vid in variant_ids:
        if vid == "pseudo_kelly":
            state_col = pseudo_kelly_col
            frac_col = None
        else:
            state_col = f"{vid}_state"
            frac_col = f"{vid}_fraction"

        dist = trace[state_col].value_counts(normalize=True).to_dict()

        switches = (trace[state_col] != trace[state_col].shift()).sum() - 1
        if switches < 0:
            switches = 0
        switch_rate = float(switches / len(trace)) if len(trace) > 1 else 0.0

        recovery_fast = 0.0
        bust_pause = 0.0
        mid_base = 0.0

        recov_df = trace[trace["actual_regime"] == "RECOVERY"]
        if len(recov_df) > 0:
            recovery_fast = float((recov_df[state_col] == "DEPLOY_FAST").mean())

        bust_df = trace[trace["actual_regime"] == "BUST"]
        if len(bust_df) > 0:
            bust_pause = float((bust_df[state_col] == "DEPLOY_PAUSE").mean())

        mid_df = trace[trace["actual_regime"] == "MID_CYCLE"]
        if len(mid_df) > 0:
            mid_base = float((mid_df[state_col] == "DEPLOY_BASE").mean())

        fraction_stats = {}
        if frac_col is not None:
            desc = trace[frac_col].describe()
            fraction_stats = {
                "mean": float(desc["mean"]),
                "std": float(desc["std"]),
                "min": float(desc["min"]),
                "max": float(desc["max"]),
                "p25": float(desc["25%"]),
                "p75": float(desc["75%"])
            }

        metrics[vid] = {
            "state_distribution": dist,
            "switch_rate": switch_rate,
            "regime_alignment": {
                "recovery_fast_rate": recovery_fast,
                "bust_pause_rate": bust_pause,
                "mid_base_rate": mid_base,
                "composite_score": (recovery_fast + bust_pause + mid_base) / 3.0
            },
            "fraction_stats": fraction_stats
        }
    return metrics


def _render_markdown_report(metrics: dict, output_path: Path) -> None:
    """生成 Markdown 对比报告"""
    lines = ["# Kelly A/B Comparison Report\n"]

    lines.append("| Variant | Switch Rate | Composite Alignment | Recovery=FAST | Bust=PAUSE | Mid=BASE |")
    lines.append("|---------|-------------|---------------------|---------------|------------|----------|")

    best_vid = None
    best_score = -1.0

    for vid, m in metrics.items():
        sr = m["switch_rate"]
        align = m["regime_alignment"]
        comp = align["composite_score"]
        rec_fast = align["recovery_fast_rate"]
        bus_pau = align["bust_pause_rate"]
        mid_bas = align["mid_base_rate"]

        if vid != "pseudo_kelly" and comp > best_score:
            best_score = comp
            best_vid = vid

        lines.append(f"| {vid} | {sr:.1%} | {comp:.1%} | {rec_fast:.1%} | {bus_pau:.1%} | {mid_bas:.1%} |")

    lines.append(f"\n**Recommendation**: Variant `{best_vid}` has the highest composite regime alignment score ({best_score:.1%}).\n")

    lines.append("## Distribution Details\n")
    for vid, m in metrics.items():
        lines.append(f"### {vid}")
        dist_str = ", ".join([f"{k}: {v:.1%}" for k, v in m["state_distribution"].items()])
        lines.append(f"- State Dist: {dist_str}")
        if m["fraction_stats"]:
            fs = m["fraction_stats"]
            lines.append(f"- Kelly Frac: mean {fs['mean']:.3f}, std {fs['std']:.3f}, range [{fs['min']:.3f}, {fs['max']:.3f}]")
        lines.append("")

    output_path.write_text("\n".join(lines))


def main(argv=None):
    parser = argparse.ArgumentParser(description="True Kelly vs Pseudo Kelly A/B comparison")
    parser.add_argument("--trace-path", required=True)
    parser.add_argument("--regime-audit", default="src/engine/v11/resources/regime_audit.json")
    parser.add_argument("--output-dir", default="artifacts/kelly_ab")
    args = parser.parse_args(argv)

    with open(args.regime_audit) as f:
        audit = json.load(f)
    regime_sharpes = dict(audit["regime_sharpes"])

    trace = _load_trace(args.trace_path)
    trace = _compute_all_variant_decisions(trace, regime_sharpes)
    metrics = _compute_metrics(trace)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "ab_summary.json").write_text(json.dumps(metrics, indent=2))
    _render_markdown_report(metrics, output_dir / "ab_report.md")
    print(f"[kelly_ab] Report saved to {output_dir}")


if __name__ == "__main__":
    main()
