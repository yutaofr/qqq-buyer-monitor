"""Research diagnostics for the v12 orthogonal-factor audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.research.data_contracts import summarize_regime_state_support

DEFAULT_CRISIS_WINDOWS: dict[str, tuple[str, str]] = {
    "2018Q4": ("2018-10-01", "2018-12-31"),
    "2020_COVID": ("2020-02-15", "2020-04-30"),
    "2022_H1": ("2022-01-01", "2022-06-30"),
}
_CRITICAL_REGIMES = frozenset({"BUST", "LATE_CYCLE"})
_FLOAT_COLUMNS = (
    "target_beta",
    "raw_target_beta",
    "entropy",
    "brier",
    "close",
    "prob_BUST",
    "prob_CAPITULATION",
    "prob_RECOVERY",
    "prob_LATE_CYCLE",
    "prob_MID_CYCLE",
)


def build_v12_diagnostic_report(
    audit_frame: pd.DataFrame,
    *,
    label_frame: pd.DataFrame | pd.Series | None = None,
    audit_regimes: list[str] | tuple[str, ...] | None = None,
    crisis_windows: dict[str, tuple[str, str]] | None = None,
    feature_diag_frame: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Build the diagnostic report required by the v12 performance protocol."""
    audit = _normalize_audit_frame(audit_frame)
    windows = crisis_windows or DEFAULT_CRISIS_WINDOWS

    report: dict[str, Any] = {
        "summary": _build_summary(audit),
        "critical_regime_performance": _build_critical_regime_performance(audit),
        "confusion_matrix": _build_confusion_matrix(audit),
        "posterior_alignment": _build_posterior_alignment(audit),
        "crisis_windows": _build_crisis_window_report(audit, windows),
        "beta_comparison": _build_beta_comparison(audit, windows),
        "entropy": _build_entropy_report(audit, windows),
        "feature_diagnostics": _build_feature_diagnostics(feature_diag_frame, windows),
    }

    if label_frame is not None and audit_regimes is not None:
        report["state_support"] = summarize_regime_state_support(
            label_frame,
            audit_regimes=audit_regimes,
        )
    else:
        report["state_support"] = {
            "audit_regimes": sorted({str(regime) for regime in (audit_regimes or ())}),
            "label_regimes": [],
            "supported_regimes": [],
            "unsupported_audit_regimes": [],
            "extra_label_regimes": [],
        }

    return report


def write_v12_diagnostic_report(report: dict[str, Any], output_dir: str | Path) -> Path:
    """Persist the JSON diagnostic report and a compact crisis-slice table."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "diagnostic_report.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")

    crisis_rows = []
    for window_name, metrics in report.get("crisis_windows", {}).items():
        crisis_rows.append({"window": window_name, **metrics})
    if crisis_rows:
        pd.DataFrame(crisis_rows).to_csv(out_dir / "crisis_windows.csv", index=False)

    posterior_rows = []
    for regime_name, metrics in report.get("posterior_alignment", {}).get("by_regime", {}).items():
        posterior_rows.append({"actual_regime": regime_name, **metrics})
    if posterior_rows:
        pd.DataFrame(posterior_rows).to_csv(out_dir / "posterior_alignment.csv", index=False)

    beta_rows = []
    for scope_name, metrics in report.get("beta_comparison", {}).get("windows", {}).items():
        beta_rows.append({"window": scope_name, **metrics})
    if beta_rows:
        pd.DataFrame(beta_rows).to_csv(out_dir / "beta_windows.csv", index=False)

    return json_path


def _normalize_audit_frame(audit_frame: pd.DataFrame) -> pd.DataFrame:
    if audit_frame is None or audit_frame.empty:
        raise ValueError("audit_frame is required")

    frame = audit_frame.copy()
    if "date" not in frame.columns:
        if isinstance(frame.index, pd.DatetimeIndex):
            frame = frame.reset_index().rename(columns={"index": "date"})
        else:
            raise ValueError("audit_frame must include a `date` column or DatetimeIndex")

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    if frame["date"].isna().any():
        bad_rows = frame.index[frame["date"].isna()].tolist()
        raise ValueError(f"Invalid audit dates: rows {bad_rows}")

    for column in _FLOAT_COLUMNS:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    return frame.sort_values("date").reset_index(drop=True)


def _build_summary(audit: pd.DataFrame) -> dict[str, float | int]:
    predicted = audit.get("predicted_regime", audit.get("stable_regime"))
    top1_accuracy = (
        float((predicted == audit["actual_regime"]).mean()) if predicted is not None else 0.0
    )
    return {
        "compared_points": int(len(audit)),
        "top1_accuracy": top1_accuracy,
        "raw_accuracy": float((audit["raw_regime"] == audit["actual_regime"]).mean()),
        "stable_accuracy": float((audit["stable_regime"] == audit["actual_regime"]).mean()),
        "mean_brier": float(audit["brier"].mean()) if "brier" in audit.columns else 0.0,
        "mean_entropy": float(audit["entropy"].mean()) if "entropy" in audit.columns else 0.0,
        "lock_incidence": float(audit["lock_active"].astype(bool).mean())
        if "lock_active" in audit.columns
        else 0.0,
    }


def _build_critical_regime_performance(audit: pd.DataFrame) -> dict[str, float]:
    critical_days = audit["actual_regime"].isin(_CRITICAL_REGIMES)
    if not critical_days.any():
        return {
            "critical_days": 0,
            "raw_critical_recall": 0.0,
            "stable_critical_recall": 0.0,
        }
    return {
        "critical_days": int(critical_days.sum()),
        "raw_critical_recall": float(
            audit.loc[critical_days, "raw_regime"].isin(_CRITICAL_REGIMES).mean()
        ),
        "stable_critical_recall": float(
            audit.loc[critical_days, "stable_regime"].isin(_CRITICAL_REGIMES).mean()
        ),
    }


def _build_confusion_matrix(audit: pd.DataFrame) -> dict[str, dict[str, int]]:
    confusion = pd.crosstab(audit["actual_regime"], audit["stable_regime"])
    return {
        str(actual): {str(predicted): int(count) for predicted, count in row.items()}
        for actual, row in confusion.iterrows()
    }


def _build_posterior_alignment(audit: pd.DataFrame) -> dict[str, Any]:
    prob_cols = [column for column in audit.columns if column.startswith("prob_")]
    if not prob_cols:
        return {"overall": {}, "by_regime": {}}

    regimes = [column.replace("prob_", "") for column in prob_cols]
    aligned = audit[["actual_regime", "entropy", *prob_cols]].copy()
    aligned = aligned.dropna(subset=["actual_regime"])

    if aligned.empty:
        return {"overall": {}, "by_regime": {}}

    overall_true_prob = []
    overall_true_rank = []
    overall_l1_error = []
    for _, row in aligned.iterrows():
        actual = str(row["actual_regime"])
        if f"prob_{actual}" not in prob_cols:
            continue
        posterior = pd.Series({regime: float(row[f"prob_{regime}"]) for regime in regimes})
        posterior = posterior.sort_values(ascending=False)
        overall_true_prob.append(float(row[f"prob_{actual}"]))
        overall_true_rank.append(float(posterior.index.get_loc(actual) + 1))
        expected = pd.Series({regime: (1.0 if regime == actual else 0.0) for regime in regimes})
        overall_l1_error.append(float((posterior.sort_index() - expected.sort_index()).abs().sum()))

    by_regime: dict[str, Any] = {}
    for actual_regime, frame in aligned.groupby("actual_regime"):
        actual = str(actual_regime)
        mean_posterior = {
            regime: float(pd.to_numeric(frame[f"prob_{regime}"], errors="coerce").mean())
            for regime in regimes
        }
        posterior_frame = frame[prob_cols].copy()
        ranks = posterior_frame.rank(axis=1, ascending=False, method="min")
        true_regime_col = f"prob_{actual}"
        true_prob = pd.to_numeric(frame[true_regime_col], errors="coerce")
        expected = pd.DataFrame(0.0, index=posterior_frame.index, columns=prob_cols)
        expected[true_regime_col] = 1.0
        l1_error = (posterior_frame - expected).abs().sum(axis=1)
        by_regime[actual] = {
            "rows": int(len(frame)),
            "mean_true_regime_probability": float(true_prob.mean()),
            "mean_true_regime_rank": float(ranks[true_regime_col].mean()),
            "mean_entropy": float(pd.to_numeric(frame["entropy"], errors="coerce").mean()),
            "mean_expected_l1_error": float(l1_error.mean()),
            **{f"mean_prob_{regime}": probability for regime, probability in mean_posterior.items()},
        }

    return {
        "overall": {
            "rows": int(len(aligned)),
            "mean_true_regime_probability": float(np.mean(overall_true_prob)) if overall_true_prob else 0.0,
            "mean_true_regime_rank": float(np.mean(overall_true_rank)) if overall_true_rank else 0.0,
            "mean_expected_l1_error": float(np.mean(overall_l1_error)) if overall_l1_error else 0.0,
        },
        "by_regime": by_regime,
    }


def _build_crisis_window_report(
    audit: pd.DataFrame,
    windows: dict[str, tuple[str, str]],
) -> dict[str, dict[str, Any]]:
    report: dict[str, dict[str, Any]] = {}
    dated = audit.set_index("date")
    for window_name, (start, end) in windows.items():
        frame = dated.loc[pd.Timestamp(start) : pd.Timestamp(end)].copy()
        report[window_name] = _summarize_crisis_window(frame)
    return report


def _summarize_crisis_window(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "rows": 0,
            "critical_days": 0,
            "raw_critical_recall": 0.0,
            "stable_critical_recall": 0.0,
            "raw_stable_divergence": 0.0,
            "mean_entropy": 0.0,
            "mean_beta_gap": 0.0,
            "first_raw_bust_date": None,
            "first_stable_bust_date": None,
        }

    critical_days = frame["actual_regime"].isin(_CRITICAL_REGIMES)
    raw_bust_dates = frame.index[frame["raw_regime"] == "BUST"]
    stable_bust_dates = frame.index[frame["stable_regime"] == "BUST"]
    return {
        "rows": int(len(frame)),
        "critical_days": int(critical_days.sum()),
        "raw_critical_recall": float(
            frame.loc[critical_days, "raw_regime"].isin(_CRITICAL_REGIMES).mean()
        )
        if critical_days.any()
        else 0.0,
        "stable_critical_recall": float(
            frame.loc[critical_days, "stable_regime"].isin(_CRITICAL_REGIMES).mean()
        )
        if critical_days.any()
        else 0.0,
        "raw_stable_divergence": float((frame["raw_regime"] != frame["stable_regime"]).mean()),
        "mean_entropy": float(frame["entropy"].mean()) if "entropy" in frame.columns else 0.0,
        "mean_beta_gap": float((frame["raw_target_beta"] - frame["target_beta"]).mean())
        if {"raw_target_beta", "target_beta"}.issubset(frame.columns)
        else 0.0,
        "first_raw_bust_date": raw_bust_dates.min().date().isoformat()
        if len(raw_bust_dates)
        else None,
        "first_stable_bust_date": stable_bust_dates.min().date().isoformat()
        if len(stable_bust_dates)
        else None,
    }


def _build_beta_comparison(
    audit: pd.DataFrame,
    windows: dict[str, tuple[str, str]],
) -> dict[str, Any]:
    dated = audit.set_index("date")
    report = {
        "overall": _summarize_beta_window(dated),
        "windows": {},
    }
    for window_name, (start, end) in windows.items():
        report["windows"][window_name] = _summarize_beta_window(
            dated.loc[pd.Timestamp(start) : pd.Timestamp(end)]
        )
    return report


def _summarize_beta_window(frame: pd.DataFrame) -> dict[str, float]:
    if frame.empty or "close" not in frame.columns:
        return {
            "rows": int(len(frame)),
            "raw_total_return": 0.0,
            "raw_max_drawdown": 0.0,
            "final_total_return": 0.0,
            "final_max_drawdown": 0.0,
            "benchmark_total_return": 0.0,
            "benchmark_max_drawdown": 0.0,
            "mean_beta_gap": 0.0,
        }

    returns = frame["close"].pct_change().fillna(0.0)
    raw = returns * frame["raw_target_beta"].shift(1).fillna(frame["raw_target_beta"].iloc[0])
    final = returns * frame["target_beta"].shift(1).fillna(frame["target_beta"].iloc[0])
    benchmark = returns

    raw_total, raw_drawdown = _total_return_and_drawdown(raw)
    final_total, final_drawdown = _total_return_and_drawdown(final)
    bench_total, bench_drawdown = _total_return_and_drawdown(benchmark)
    return {
        "rows": int(len(frame)),
        "raw_total_return": raw_total,
        "raw_max_drawdown": raw_drawdown,
        "final_total_return": final_total,
        "final_max_drawdown": final_drawdown,
        "benchmark_total_return": bench_total,
        "benchmark_max_drawdown": bench_drawdown,
        "mean_beta_gap": float((frame["raw_target_beta"] - frame["target_beta"]).mean()),
    }


def _total_return_and_drawdown(returns: pd.Series) -> tuple[float, float]:
    equity = (1.0 + returns.fillna(0.0)).cumprod()
    if equity.empty:
        return 0.0, 0.0
    peak = equity.cummax()
    drawdown = (equity / peak - 1.0).min()
    return float(equity.iloc[-1] - 1.0), float(drawdown)


def _build_entropy_report(
    audit: pd.DataFrame,
    windows: dict[str, tuple[str, str]],
) -> dict[str, Any]:
    dated = audit.set_index("date")
    report = {"overall": _summarize_entropy_window(dated), "windows": {}}
    for window_name, (start, end) in windows.items():
        report["windows"][window_name] = _summarize_entropy_window(
            dated.loc[pd.Timestamp(start) : pd.Timestamp(end)]
        )
    return report


def _summarize_entropy_window(frame: pd.DataFrame) -> dict[str, float]:
    if frame.empty or "entropy" not in frame.columns:
        return {
            "rows": int(len(frame)),
            "mean_entropy": 0.0,
            "max_entropy": 0.0,
            "p90_entropy": 0.0,
        }
    entropy = pd.to_numeric(frame["entropy"], errors="coerce").dropna()
    if entropy.empty:
        return {
            "rows": int(len(frame)),
            "mean_entropy": 0.0,
            "max_entropy": 0.0,
            "p90_entropy": 0.0,
        }
    return {
        "rows": int(len(frame)),
        "mean_entropy": float(entropy.mean()),
        "max_entropy": float(entropy.max()),
        "p90_entropy": float(entropy.quantile(0.9)),
    }


def _build_feature_diagnostics(
    feature_diag_frame: pd.DataFrame | None,
    windows: dict[str, tuple[str, str]],
) -> dict[str, Any]:
    if feature_diag_frame is None or feature_diag_frame.empty:
        empty = {
            "rows": 0,
            "mean_move_21d_raw_abs": 0.0,
            "mean_move_21d_orth_abs": 0.0,
            "mean_move_spread_beta": 0.0,
            "mean_move_spread_corr_21d": 0.0,
        }
        return {"overall": empty, "windows": {name: empty for name in windows}}

    diag = feature_diag_frame.copy()
    if not isinstance(diag.index, pd.DatetimeIndex):
        raise ValueError("feature_diag_frame must use a DatetimeIndex")
    diag.index = pd.to_datetime(diag.index, errors="coerce").normalize()
    diag = diag.replace([np.inf, -np.inf], np.nan)

    report = {"overall": _summarize_feature_window(diag), "windows": {}}
    for window_name, (start, end) in windows.items():
        report["windows"][window_name] = _summarize_feature_window(
            diag.loc[pd.Timestamp(start) : pd.Timestamp(end)]
        )
    return report


def _summarize_feature_window(frame: pd.DataFrame) -> dict[str, float]:
    if frame.empty:
        return {
            "rows": 0,
            "mean_move_21d_raw_abs": 0.0,
            "mean_move_21d_orth_abs": 0.0,
            "mean_move_spread_beta": 0.0,
            "mean_move_spread_corr_21d": 0.0,
        }
    return {
        "rows": int(len(frame)),
        "mean_move_21d_raw_abs": float(
            pd.to_numeric(frame.get("move_21d_raw_z"), errors="coerce").abs().mean()
        ),
        "mean_move_21d_orth_abs": float(
            pd.to_numeric(frame.get("move_21d_orth_z"), errors="coerce").abs().mean()
        ),
        "mean_move_spread_beta": float(
            pd.to_numeric(frame.get("move_spread_beta"), errors="coerce").mean()
        ),
        "mean_move_spread_corr_21d": float(
            pd.to_numeric(frame.get("move_spread_corr_21d"), errors="coerce").mean()
        ),
    }
