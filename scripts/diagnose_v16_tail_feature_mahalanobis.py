#!/usr/bin/env python3
"""Forensic telemetry for V16 tail-recovery feature isolation in Q1 2020.

This script is intentionally diagnostic-only. It does not modify production
estimator code and runs the conductor with temporary state paths.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.spatial.distance import mahalanobis
from scipy.stats import chi2

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.engine.v11.conductor import V11Conductor, _v12_quality_field_specs  # noqa: E402
from src.engine.v11.core.data_quality import (  # noqa: E402
    assess_data_quality,
    feature_reliability_weights,
)

INCIDENT_FEATURES = ("pmi_momentum", "labor_slack", "liquidity_velocity")
DEFAULT_DATES = (
    "2020-02-20",
    "2020-02-28",
    "2020-03-09",
    "2020-03-16",
    "2020-03-23",
    "2020-03-31",
)


def _numeric_training_frame(conductor: V11Conductor) -> pd.DataFrame:
    macro_df = pd.read_csv(
        conductor.macro_data_path,
        index_col="observation_date",
        parse_dates=True,
    )
    regime_df = pd.read_csv(
        conductor.regime_data_path,
        parse_dates=["observation_date"],
    ).set_index("observation_date")

    if conductor.training_cutoff is not None:
        macro_df = macro_df[macro_df.index < conductor.training_cutoff]
        regime_df = regime_df[regime_df.index < conductor.training_cutoff]

    macro_df = conductor._augment_context_with_price_history(macro_df)
    features = conductor.seeder.generate_features(macro_df)
    frame = features.join(regime_df["regime"], how="inner").drop(columns=["regime"])
    return (
        frame.apply(pd.to_numeric, errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .dropna(axis=0, how="any")
    )


def _regularized_cov(frame: pd.DataFrame) -> np.ndarray:
    cov = frame.cov().values
    if cov.ndim == 0:
        cov = np.array([[float(cov)]], dtype=float)
    cov = np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0)
    return cov + np.eye(cov.shape[0]) * 1e-6


def _condition_payload(cov: np.ndarray) -> dict[str, float | str]:
    sign, logdet = np.linalg.slogdet(cov)
    determinant: float | str
    if sign <= 0:
        determinant = "non_positive"
    else:
        determinant = float(np.exp(logdet)) if logdet > -745 else f"exp({logdet:.6f})"
    return {
        "determinant": determinant,
        "log_determinant": float(logdet),
        "condition_number": float(np.linalg.cond(cov)),
    }


def _distance_payload(
    *,
    row: pd.Series,
    mean: np.ndarray,
    inv_cov: np.ndarray,
    feature_names: list[str],
    threshold: float,
    selected_features: tuple[str, ...],
    cov: np.ndarray,
    baseline_frame: pd.DataFrame,
) -> dict[str, Any]:
    x = row.loc[feature_names].to_numpy(dtype=float)
    delta = x - mean
    full_d = float(mahalanobis(x, mean, inv_cov))
    full_d2 = full_d * full_d
    md2_terms = delta * (inv_cov @ delta)

    selected_idx = [feature_names.index(name) for name in selected_features]
    selected_cov = cov[np.ix_(selected_idx, selected_idx)]
    selected_inv = np.linalg.pinv(selected_cov)
    selected_x = x[selected_idx]
    selected_mean = mean[selected_idx]
    selected_d = float(mahalanobis(selected_x, selected_mean, selected_inv))

    selected_payload = {}
    for name, idx in zip(selected_features, selected_idx, strict=True):
        baseline_std = float(baseline_frame[name].std())
        raw_value = float(row[name])
        selected_payload[name] = {
            "feature_z_value": raw_value,
            "baseline_mean": float(mean[idx]),
            "baseline_std": baseline_std,
            "univariate_baseline_sigma": float((raw_value - mean[idx]) / baseline_std)
            if baseline_std > 0
            else None,
            "full_md2_signed_contribution": float(md2_terms[idx]),
        }

    return {
        "full_mahalanobis_distance": full_d,
        "full_mahalanobis_distance_squared": full_d2,
        "threshold_distance": threshold,
        "threshold_distance_squared": threshold * threshold,
        "threshold_chi2_cdf_with_full_df": float(chi2.cdf(threshold * threshold, len(feature_names))),
        "threshold_chi2_survival_with_full_df": float(
            chi2.sf(threshold * threshold, len(feature_names))
        ),
        "is_ood": bool(full_d > threshold),
        "incident_subspace_mahalanobis_distance": selected_d,
        "incident_subspace_mahalanobis_distance_squared": selected_d * selected_d,
        "incident_subspace_threshold_chi2_95_distance": float(
            np.sqrt(chi2.ppf(0.95, len(selected_features)))
        ),
        "incident_features": selected_payload,
    }


def _nearest_index(index: pd.DatetimeIndex, date_str: str) -> pd.Timestamp:
    dt = pd.to_datetime(date_str).normalize()
    eligible = index[index <= dt]
    if eligible.empty:
        raise ValueError(f"No data available on or before {date_str}")
    return pd.Timestamp(eligible[-1]).normalize()


def run(args: argparse.Namespace) -> dict[str, Any]:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    with tempfile.TemporaryDirectory(prefix="v16_tail_diag_") as tmp:
        prior_copy = Path(tmp) / "prior_state.json"
        shutil.copyfile("src/engine/v11/resources/v13_6_ex_hydrated_prior.json", prior_copy)
        conductor = V11Conductor(
            training_cutoff=args.training_cutoff,
            prior_state_path=str(prior_copy),
            snapshot_dir=str(Path(tmp) / "snapshots"),
            allow_prior_bootstrap_drift=True,
        )

        raw = pd.read_csv(
            conductor.macro_data_path,
            index_col="observation_date",
            parse_dates=True,
        ).sort_index()
        raw = conductor._augment_context_with_price_history(raw)
        all_features = conductor.seeder.generate_features(raw)
        training_frame = _numeric_training_frame(conductor)
        cov = _regularized_cov(training_frame)
        with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
            inv_cov = np.linalg.pinv(cov)  # noqa: F841
        feature_names = list(training_frame.columns)
        threshold = float(conductor.v13_4_registry.get("mahalanobis_ood_threshold", 4.0))

        date_payloads: list[dict[str, Any]] = []
        previous_raw: pd.Series | None = None
        for date_str in args.dates:
            dt = _nearest_index(all_features.index, date_str)
            raw_dt = _nearest_index(raw.index, date_str)
            latest_raw = raw.loc[raw_dt]
            context_features = conductor.seeder.generate_features(raw.loc[:dt])
            latest_vector = context_features.iloc[[-1]]
            row = latest_vector.iloc[0]
            feature_dt = pd.Timestamp(latest_vector.index[-1]).normalize()

            quality_audit = assess_data_quality(
                latest_raw,
                previous_raw=previous_raw,
                registry=conductor.v13_4_registry,
                field_specs=_v12_quality_field_specs(),
            )
            feature_quality = feature_reliability_weights(
                latest_vector=latest_vector,
                latest_raw=latest_raw,
                field_quality={
                    str(name): float(payload.get("quality", 1.0))
                    for name, payload in dict(quality_audit.get("fields", {})).items()
                },
                seeder_config=conductor.seeder.config,
            )
            previous_raw = latest_raw

            captured_guard_vector: dict[str, np.ndarray] = {}
            original_is_outlier = conductor.mahalanobis_guard.is_outlier

            def _capturing_is_outlier(
                current_vector: np.ndarray,
                threshold: float = 4.0,
                return_distance: bool = False,
                *,
                stress_probability: float = 0.0,
            ) -> bool | tuple[bool, float]:
                captured_guard_vector["x"] = np.asarray(current_vector, dtype=float)  # noqa: B023
                return original_is_outlier(  # noqa: B023
                    current_vector,
                    threshold=threshold,
                    stress_probability=stress_probability,
                    return_distance=return_distance,
                )

            conductor.mahalanobis_guard.is_outlier = _capturing_is_outlier
            try:
                runtime = conductor.daily_run(raw.loc[:dt])
            finally:
                conductor.mahalanobis_guard.is_outlier = original_is_outlier
            diagnostics = runtime.get("v13_4_diagnostics", {})
            if "x" in captured_guard_vector:
                row = pd.Series(captured_guard_vector["x"], index=feature_names)

            raw_sources = {}
            for feature in INCIDENT_FEATURES:
                src = str(conductor.seeder.config[feature]["src"])
                raw_sources[feature] = {
                    "source_column": src,
                    "raw_value": None
                    if pd.isna(latest_raw.get(src))
                    else float(pd.to_numeric(pd.Series([latest_raw.get(src)]), errors="coerce").iloc[0]),
                    "feature_quality_weight": float(feature_quality.get(feature, 1.0)),
                    "runtime_dead_feature": feature in set(diagnostics.get("dead_features", [])),
                }

            date_payloads.append(
                {
                    "requested_date": date_str,
                    "effective_feature_date": feature_dt.date().isoformat(),
                    "effective_raw_date": raw_dt.date().isoformat(),
                    "raw_sources": raw_sources,
                    "runtime_dead_features": diagnostics.get("dead_features", []),
                    "runtime_mahalanobis_dist": diagnostics.get("mahalanobis_dist"),
                    "runtime_mahalanobis_geometry": diagnostics.get("mahalanobis_geometry", {}),
                    "quality_audit_reason": quality_audit.get("reason"),
                    "quality_fields": quality_audit.get("fields"),
                    "distance": _distance_payload(
                        row=row,
                        mean=conductor.mahalanobis_guard.mean,
                        inv_cov=conductor.mahalanobis_guard.inv_cov,
                        feature_names=feature_names,
                        threshold=threshold,
                        selected_features=INCIDENT_FEATURES,
                        cov=cov,
                        baseline_frame=training_frame,
                    ),
                }
            )

        result = {
            "training_cutoff": str(args.training_cutoff),
            "baseline_rows": int(len(training_frame)),
            "baseline_feature_count": int(len(feature_names)),
            "baseline_features": feature_names,
            "empirical_covariance_before_shrinkage": _condition_payload(cov),
            "robust_baseline": conductor.mahalanobis_guard.baseline_diagnostics(),
            "incident_subspace_covariance": _condition_payload(
                cov[
                    np.ix_(
                        [feature_names.index(f) for f in INCIDENT_FEATURES],
                        [feature_names.index(f) for f in INCIDENT_FEATURES],
                    )
                ]
            ),
            "dates": date_payloads,
        }

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-cutoff", default="2019-12-31")
    parser.add_argument("--output", default="")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("dates", nargs="*", default=list(DEFAULT_DATES))
    args = parser.parse_args()

    payload = run(args)
    text = json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
