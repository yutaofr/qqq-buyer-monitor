from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def _coerce_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _clip01(value: float | None) -> float:
    return float(np.clip(float(value or 0.0), 0.0, 1.0))


def _stationary_excess_score(series: pd.Series, window: int = 252) -> float | None:
    """v14.0 stationary score with rolling normalization to prevent look-ahead scale inflation."""
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return None
    # Minimum history for stats (42 day trading cycle)
    min_p = 42
    if numeric.count() < min_p:
        baseline = numeric.expanding(min_periods=1).median()
    else:
        baseline = numeric.rolling(window=window, min_periods=min_p).median()

    excess = (numeric - baseline).clip(lower=0.0)
    last_excess = float(excess.iloc[-1])
    if not np.isfinite(last_excess) or last_excess <= 0.0:
        return 0.0

    if excess.count() < min_p:
        max_excess = float(excess.max())
    else:
        max_excess = float(excess.rolling(window=window, min_periods=min_p).max().iloc[-1])

    if not np.isfinite(max_excess) or max_excess <= 0.0:
        return 0.0
    return float(np.clip(last_excess / max_excess, 0.0, 1.0))


def is_weekly_release_visible(*, observation_ts: datetime, release_ts: datetime) -> bool:
    observed = (
        observation_ts
        if observation_ts.tzinfo is not None
        else observation_ts.replace(tzinfo=release_ts.tzinfo)
    )
    released = (
        release_ts if release_ts.tzinfo is not None else release_ts.replace(tzinfo=observed.tzinfo)
    )
    return observed >= released


def _normalize_mode(raw_mode: str | None, *, allowed_modes: set[str], default_mode: str) -> str:
    candidate = str(raw_mode or default_mode).upper()
    if candidate not in allowed_modes:
        raise ValueError(f"Unsupported overlay_mode: {candidate}")
    return candidate


class ExecutionOverlayEngine:
    """v13 execution overlay with monotone, bounded conditioning."""

    def __init__(
        self,
        *,
        audit_path: str | Path | None = None,
        suppress_collinear_qqew: bool = True,
    ):
        self.audit_path = Path(
            audit_path or Path(__file__).parent / "resources" / "execution_overlay_audit.json"
        )
        self.audit = json.loads(self.audit_path.read_text(encoding="utf-8"))
        self.suppress_collinear_qqew = bool(suppress_collinear_qqew)
        mode_policy = dict(self.audit.get("mode_policy", {}))
        self.allowed_modes = {
            str(mode).upper()
            for mode in mode_policy.get(
                "allowed_modes",
                ["DISABLED", "SHADOW", "NEGATIVE_ONLY", "FULL"],
            )
        }
        self.default_mode = _normalize_mode(
            str(mode_policy.get("default_mode", "FULL")),
            allowed_modes=self.allowed_modes,
            default_mode="FULL",
        )

    def evaluate(self, context_df: pd.DataFrame, *, mode: str | None = None) -> dict[str, Any]:
        frame = context_df.copy()
        overlay_mode = _normalize_mode(
            mode, allowed_modes=self.allowed_modes, default_mode=self.default_mode
        )
        if "observation_date" in frame.columns:
            frame["observation_date"] = pd.to_datetime(frame["observation_date"], errors="coerce")
            frame = frame.sort_values("observation_date")
        elif not isinstance(frame.index, pd.DatetimeIndex):
            frame.index = pd.to_datetime(frame.index, errors="coerce")

        admission_decisions: dict[str, dict[str, Any]] = {}
        raw_inputs: dict[str, Any] = {}
        input_quality: dict[str, float] = {}
        derived_features: dict[str, float | None] = {
            "breadth_stress": None,
            "concentration_stress": None,
            "non_confirmation": None,
            "volume_repair": None,
        }
        signal_contributions = {"negative": {}, "positive": {}}

        negative_components: list[tuple[str, float, float]] = []
        positive_components: list[tuple[str, float, float]] = []

        minimum_quality = float(self.audit["source_policy"]["minimum_quality"])
        minimum_history = int(self.audit["source_policy"]["minimum_history"])
        reject_prefixes = tuple(str(v) for v in self.audit["source_policy"]["reject_prefixes"])
        repurposed_fields = {str(v) for v in self.audit["source_policy"]["repurposed_proxy_fields"]}
        negative_weights = {
            str(key): float(value)
            for key, value in dict(self.audit["signal_weights"]["negative"]).items()
        }
        positive_weights = {
            str(key): float(value)
            for key, value in dict(self.audit["signal_weights"]["positive"]).items()
        }

        def source_ok(source: str | None) -> bool:
            return bool(source) and not str(source).startswith(reject_prefixes)

        def admission(
            source_name: str, *, admitted: bool, reason: str, quality: float = 0.0
        ) -> None:
            admission_decisions[source_name] = {
                "admitted": admitted,
                "reason": reason,
                "quality": round(float(quality), 6),
            }

        latest = frame.iloc[-1] if not frame.empty else pd.Series(dtype=object)
        breadth_source = str(latest.get("source_breadth_proxy", "") or "")
        breadth_quality = _clip01(latest.get("breadth_quality_score", 0.0))

        if "adv_dec_ratio" not in frame.columns and any(
            field in frame.columns for field in repurposed_fields
        ):
            admission(
                "breadth_proxy",
                admitted=False,
                reason="adv_dec_ratio missing; pct_above_50d is a repurposed proxy field and is rejected",
                quality=0.0,
            )
        else:
            raw_inputs["adv_dec_ratio"] = latest.get("adv_dec_ratio")
            input_quality["breadth_proxy"] = breadth_quality
            if (
                "adv_dec_ratio" in frame.columns
                and source_ok(breadth_source)
                and breadth_quality >= minimum_quality
            ):
                breadth_series = 1.0 - _coerce_series(frame, "adv_dec_ratio")
                breadth_stress = _stationary_excess_score(breadth_series)
                derived_features["breadth_stress"] = breadth_stress
                if breadth_stress is not None and breadth_stress > 0.0:
                    negative_components.append(
                        (
                            "breadth_stress",
                            breadth_stress,
                            negative_weights.get("breadth_stress", 0.0) * breadth_quality,
                        )
                    )
                    signal_contributions["negative"]["breadth_stress"] = breadth_stress
                admission(
                    "breadth_proxy", admitted=True, reason="admitted", quality=breadth_quality
                )
            else:
                admission(
                    "breadth_proxy",
                    admitted=False,
                    reason="missing_or_low_quality",
                    quality=breadth_quality,
                )

        concentration_source = str(latest.get("source_ndx_concentration", "") or "")
        concentration_quality = _clip01(latest.get("ndx_concentration_quality_score", 0.0))
        raw_inputs["ndx_concentration"] = latest.get("ndx_concentration")
        input_quality["ndx_concentration"] = concentration_quality
        breadth_is_qqew_derived = breadth_source.startswith("derived:qqq-qqew-breadth")
        if self.suppress_collinear_qqew and breadth_is_qqew_derived:
            admission(
                "ndx_concentration",
                admitted=False,
                reason="suppressed_collinear_with_derived_breadth",
                quality=concentration_quality,
            )
        elif (
            "ndx_concentration" in frame.columns
            and source_ok(concentration_source)
            and concentration_quality >= minimum_quality
        ):
            concentration_series = _coerce_series(frame, "ndx_concentration").clip(lower=0.0)
            concentration_stress = _stationary_excess_score(concentration_series)
            derived_features["concentration_stress"] = concentration_stress
            if concentration_stress is not None and concentration_stress > 0.0:
                negative_components.append(
                    (
                        "concentration_stress",
                        concentration_stress,
                        negative_weights.get("concentration_stress", 0.0) * concentration_quality,
                    )
                )
                signal_contributions["negative"]["concentration_stress"] = concentration_stress
            admission(
                "ndx_concentration", admitted=True, reason="admitted", quality=concentration_quality
            )
        else:
            admission(
                "ndx_concentration",
                admitted=False,
                reason="missing_or_low_quality",
                quality=concentration_quality,
            )

        close_source = str(latest.get("source_qqq_close", "") or "")
        volume_source = str(latest.get("source_qqq_volume", "") or "")
        close_quality = _clip01(latest.get("qqq_close_quality_score", 0.0))
        volume_quality = _clip01(latest.get("qqq_volume_quality_score", 0.0))
        raw_inputs["qqq_close"] = latest.get("qqq_close")
        raw_inputs["qqq_volume"] = latest.get("qqq_volume")
        input_quality["qqq_close"] = close_quality
        input_quality["qqq_volume"] = volume_quality

        close_series = _coerce_series(frame, "qqq_close")
        volume_series = _coerce_series(frame, "qqq_volume").clip(lower=1.0)
        have_tape = (
            {
                "qqq_close",
                "qqq_volume",
            }.issubset(frame.columns)
            and close_series.dropna().shape[0] >= minimum_history
            and volume_series.dropna().shape[0] >= minimum_history
        )
        tape_quality = min(close_quality, volume_quality)
        if (
            have_tape
            and source_ok(close_source)
            and source_ok(volume_source)
            and tape_quality >= minimum_quality
        ):
            price_strength_20d = close_series.pct_change(20).fillna(0.0)
            price_strength_5d = close_series.pct_change(5).fillna(0.0)
            log_volume = np.log(volume_series)
            exp_mean = log_volume.expanding(min_periods=minimum_history).mean()
            exp_std = (
                log_volume.expanding(min_periods=minimum_history).std(ddof=0).replace(0.0, np.nan)
            )
            volume_intensity = (
                ((log_volume - exp_mean) / exp_std).replace([np.inf, -np.inf], np.nan).fillna(0.0)
            )

            non_confirmation_raw = price_strength_20d.clip(lower=0.0) * (-volume_intensity).clip(
                lower=0.0
            )
            volume_repair_raw = (
                (-price_strength_20d).clip(lower=0.0)
                * price_strength_5d.clip(lower=0.0)
                * volume_intensity.clip(lower=0.0)
            )

            non_confirmation = _stationary_excess_score(non_confirmation_raw)
            volume_repair = _stationary_excess_score(volume_repair_raw)
            derived_features["non_confirmation"] = non_confirmation
            derived_features["volume_repair"] = volume_repair

            if non_confirmation is not None and non_confirmation > 0.0:
                negative_components.append(
                    (
                        "non_confirmation",
                        non_confirmation,
                        negative_weights.get("non_confirmation", 0.0) * tape_quality,
                    )
                )
                signal_contributions["negative"]["non_confirmation"] = non_confirmation
            if volume_repair is not None and volume_repair > 0.0:
                positive_components.append(
                    (
                        "volume_repair",
                        volume_repair,
                        positive_weights.get("volume_repair", 0.0) * tape_quality,
                    )
                )
                signal_contributions["positive"]["volume_repair"] = volume_repair

            admission("qqq_tape", admitted=True, reason="admitted", quality=tape_quality)
        else:
            admission(
                "qqq_tape", admitted=False, reason="missing_or_low_quality", quality=tape_quality
            )

        negative_score = self._weighted_average(negative_components)
        positive_score = self._weighted_average(positive_components)
        neutral = not negative_components and not positive_components

        beta_cfg = self.audit["beta_overlay"]
        pace_cfg = self.audit["deployment_overlay"]
        diagnostic_beta_overlay_multiplier = (
            1.0
            if neutral
            else float(
                np.clip(
                    1.0
                    - float(beta_cfg["lambda_beta"]) * negative_score
                    + float(beta_cfg.get("lambda_beta_pos", 0.0)) * positive_score,
                    float(beta_cfg["beta_floor"]),
                    float(beta_cfg.get("beta_ceiling", 1.0)),
                )
            )
        )
        diagnostic_deployment_overlay_multiplier = (
            1.0
            if neutral
            else float(
                np.clip(
                    1.0
                    - float(pace_cfg["lambda_pace_neg"]) * negative_score
                    + float(pace_cfg["lambda_pace_pos"]) * positive_score,
                    float(pace_cfg["pace_floor"]),
                    float(pace_cfg["pace_ceiling"]),
                )
            )
        )
        negative_only_deployment_multiplier = (
            1.0
            if neutral
            else float(
                np.clip(
                    1.0 - float(pace_cfg["lambda_pace_neg"]) * negative_score,
                    float(pace_cfg["pace_floor"]),
                    1.0,
                )
            )
        )
        negative_only_beta_multiplier = (
            1.0
            if neutral
            else float(
                np.clip(
                    1.0 - float(beta_cfg["lambda_beta"]) * negative_score,
                    float(beta_cfg["beta_floor"]),
                    1.0,
                )
            )
        )

        if neutral:
            overlay_state = "NEUTRAL"
        elif negative_score > positive_score and diagnostic_beta_overlay_multiplier < 1.0:
            overlay_state = "PENALTY"
        elif positive_score > negative_score and diagnostic_deployment_overlay_multiplier > 1.0:
            overlay_state = "REWARD"
        else:
            overlay_state = "MIXED"

        if overlay_mode in {"DISABLED", "SHADOW"}:
            beta_overlay_multiplier = 1.0
            deployment_overlay_multiplier = 1.0
        elif overlay_mode == "NEGATIVE_ONLY":
            beta_overlay_multiplier = negative_only_beta_multiplier
            deployment_overlay_multiplier = negative_only_deployment_multiplier
        else:
            beta_overlay_multiplier = diagnostic_beta_overlay_multiplier
            deployment_overlay_multiplier = diagnostic_deployment_overlay_multiplier

        return {
            "overlay_mode": overlay_mode,
            "beta_overlay_multiplier": round(beta_overlay_multiplier, 6),
            "deployment_overlay_multiplier": round(deployment_overlay_multiplier, 6),
            "diagnostic_beta_overlay_multiplier": round(diagnostic_beta_overlay_multiplier, 6),
            "diagnostic_deployment_overlay_multiplier": round(
                diagnostic_deployment_overlay_multiplier, 6
            ),
            "negative_score": round(float(negative_score), 6),
            "positive_score": round(float(positive_score), 6),
            "overlay_state": overlay_state,
            "overlay_summary": f"{overlay_mode} | {overlay_state}: neg={negative_score:.3f} pos={positive_score:.3f}",
            "neutral_fallback_triggered": neutral,
            "raw_inputs": raw_inputs,
            "input_quality": input_quality,
            "derived_features": derived_features,
            "signal_contributions": signal_contributions,
            "admission_decisions": admission_decisions,
        }

    @staticmethod
    def _weighted_average(components: list[tuple[str, float, float]]) -> float:
        weights = [max(0.0, float(weight)) for _, _, weight in components]
        total = float(sum(weights))
        if total <= 0.0:
            return 0.0
        value = (
            sum(float(component) * max(0.0, float(weight)) for _, component, weight in components)
            / total
        )
        return float(np.clip(value, 0.0, 1.0))
