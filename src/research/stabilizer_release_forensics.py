"""Forensic analysis for delayed RECOVERY stable-state release."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def flatten_forensic_row(row: dict[str, Any]) -> dict[str, Any]:
    out = {
        "date": row.get("date"),
        "test_type": row.get("test_type"),
        "actual_regime": row.get("actual_regime"),
        "predicted_regime": row.get("predicted_regime"),
        "raw_regime": row.get("raw_regime"),
        "stable_regime": row.get("stable_regime"),
    }
    for key, value in dict(row.get("price_topology", {})).items():
        if key == "probabilities":
            for regime, prob in dict(value).items():
                out[f"price_topology_prob_{regime}"] = prob
        else:
            out[f"price_topology_{key}"] = value
    for key, value in dict(row.get("regime_stabilizer", {})).items():
        out[f"stabilizer_{key}"] = value
    return out


def load_forensic_trace(path: str | Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            rows.append(flatten_forensic_row(json.loads(raw)))
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame = frame.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return frame


def build_release_failure_frame(
    merged_trace: pd.DataFrame,
    forensic_trace: pd.DataFrame,
) -> pd.DataFrame:
    merged = merged_trace.copy()
    merged["date"] = pd.to_datetime(merged["date"], errors="coerce")
    forensic = forensic_trace.copy()
    forensic["date"] = pd.to_datetime(forensic["date"], errors="coerce")
    frame = merged.merge(forensic, on="date", how="left", suffixes=("", "_forensic"))
    frame = frame[
        (frame["benchmark_regime"] == "RECOVERY") & (frame["stable_regime"] != "RECOVERY")
    ].copy()
    if frame.empty:
        return frame
    frame["release_failure_cause"] = frame.apply(classify_release_failure, axis=1)
    return frame


def classify_release_failure(row: pd.Series) -> str:
    if row.get("benchmark_regime") != "RECOVERY" or row.get("stable_regime") == "RECOVERY":
        return "not_a_release_failure"

    if row.get("price_topology_regime") != "RECOVERY":
        return "topology_not_confirmed"

    prob_bust = float(row.get("prob_BUST", 0.0) or 0.0)
    prob_recovery = float(row.get("prob_RECOVERY", 0.0) or 0.0)
    bearish_divergence = float(row.get("price_topology_bearish_divergence", 0.0) or 0.0)
    recovery_acceleration = float(row.get("price_topology_recovery_prob_acceleration", 0.0) or 0.0)
    topology_confidence = float(row.get("price_topology_confidence", 0.0) or 0.0)
    barrier = float(row.get("stabilizer_barrier", 0.0) or 0.0)
    evidence = float(row.get("stabilizer_evidence", 0.0) or 0.0)

    if row.get("raw_regime") != "RECOVERY" and prob_bust >= prob_recovery:
        return "posterior_trapped_in_bust"
    if bearish_divergence >= 0.25:
        return "bearish_divergence_drag"
    if recovery_acceleration < 0.0:
        return "recovery_acceleration_fade"
    if row.get("raw_regime") == "RECOVERY" and barrier > 0.0 and evidence < barrier:
        return "stabilizer_barrier_hold"
    if topology_confidence < 0.10:
        return "low_topology_confidence"
    return "unclassified_release_failure"


def summarize_release_failures(frame: pd.DataFrame) -> dict[str, Any]:
    if frame is None or frame.empty:
        return {
            "failure_rows": 0,
            "by_cause": {},
            "raw_recovery_share": 0.0,
            "mean_barrier_gap": 0.0,
        }

    working = frame.copy()
    if "release_failure_cause" not in working.columns:
        working["release_failure_cause"] = working.apply(classify_release_failure, axis=1)

    cause_counts = (
        working["release_failure_cause"].value_counts(dropna=False).sort_index().to_dict()
    )
    barrier = pd.to_numeric(working.get("stabilizer_barrier"), errors="coerce").fillna(0.0)
    evidence = pd.to_numeric(working.get("stabilizer_evidence"), errors="coerce").fillna(0.0)
    raw_recovery_share = float((working["raw_regime"] == "RECOVERY").mean())
    return {
        "failure_rows": int(len(working)),
        "by_cause": {str(key): int(value) for key, value in cause_counts.items()},
        "raw_recovery_share": raw_recovery_share,
        "mean_barrier_gap": float((barrier - evidence).mean()),
    }


def render_release_failure_report(summary: dict[str, Any], frame: pd.DataFrame) -> str:
    lines = [
        "# Stabilizer Release Forensics",
        "",
        f"- failure rows: `{summary['failure_rows']}`",
        f"- raw recovery share: `{summary['raw_recovery_share']:.2%}`",
        f"- mean barrier gap: `{summary['mean_barrier_gap']:.4f}`",
        "",
        "## Root Causes",
        "",
    ]
    for cause, count in sorted(dict(summary.get("by_cause", {})).items()):
        lines.append(f"- `{cause}`: `{count}`")

    if frame is not None and not frame.empty:
        lines.extend(["", "## Representative Dates", ""])
        display = frame.copy()
        if "release_failure_cause" not in display.columns:
            display["release_failure_cause"] = display.apply(classify_release_failure, axis=1)
        barrier = pd.to_numeric(display.get("stabilizer_barrier"), errors="coerce").fillna(0.0)
        evidence = pd.to_numeric(display.get("stabilizer_evidence"), errors="coerce").fillna(0.0)
        display["barrier_gap"] = barrier - evidence
        cols = [
            "date",
            "release_failure_cause",
            "raw_regime",
            "stable_regime",
            "prob_BUST",
            "prob_RECOVERY",
            "price_topology_confidence",
            "price_topology_bearish_divergence",
            "price_topology_recovery_prob_acceleration",
            "barrier_gap",
        ]
        for _, row in display.sort_values("barrier_gap", ascending=False).head(10)[cols].iterrows():
            lines.append(
                "- `{date}` {cause} | raw={raw} stable={stable} | bust={bust:.3f} recovery={recovery:.3f} | conf={conf:.3f} | bear={bear:.3f} | accel={accel:.4f} | gap={gap:.4f}".format(
                    date=pd.Timestamp(row["date"]).date().isoformat(),
                    cause=row["release_failure_cause"],
                    raw=row["raw_regime"],
                    stable=row["stable_regime"],
                    bust=float(row["prob_BUST"]),
                    recovery=float(row["prob_RECOVERY"]),
                    conf=float(row["price_topology_confidence"]),
                    bear=float(row["price_topology_bearish_divergence"]),
                    accel=float(row["price_topology_recovery_prob_acceleration"]),
                    gap=float(row["barrier_gap"]),
                )
            )

    return "\n".join(lines) + "\n"
