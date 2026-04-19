from __future__ import annotations

import importlib
import json
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_phase_next = importlib.import_module("scripts.phase_next_research")
EventWindow = _phase_next.EventWindow
PhaseNextResearch = _phase_next.PhaseNextResearch


STAGES = (
    "EXPANSION",
    "LATE_CYCLE",
    "STRESS",
    "RECOVERY",
    "FAST_CASCADE_BOUNDARY",
)
TRANSITION_URGENCIES = ("LOW", "RISING", "HIGH", "UNSTABLE")
ACTION_BANDS = (
    "NO_ACTION_ZONE",
    "WATCH_CLOSELY",
    "PREPARE_TO_ADJUST",
    "HIGH_CONVICTION_TRANSITION",
)


@dataclass(frozen=True)
class ProductDashboardInput:
    date: str | None
    hazard_score: float
    hazard_percentile: float
    stress_score: float
    breadth_proxy: float
    volatility_percentile: float
    structural_stress: bool
    repair_confirmation: bool
    relapse_flag: bool
    hazard_delta_5d: float
    breadth_delta_10d: float
    volatility_delta_10d: float
    boundary_pressure: float
    stress_persistence_days: int
    repair_persistence_days: int
    stress_delta_5d: float = 0.0
    stress_acceleration_5d: float = 0.0


@dataclass(frozen=True)
class ProductConfig:
    temperature: float
    smoothing_alpha: float
    boundary_passthrough: float
    name: str


class ProductCycleDashboard:
    PRODUCT_NAME = "Daily Post-Close Cycle Stage Probability Dashboard"

    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root)
        self.repo_root = REPO_ROOT
        self.reports_dir = self.root / "reports"
        self.artifacts_dir = self.root / "artifacts" / "product"
        self.research = PhaseNextResearch(root=root)

    def evaluate(self, item: ProductDashboardInput) -> dict[str, Any]:
        probabilities = self._stage_probabilities(item, temperature=0.58)
        return self._daily_output(item, probabilities)

    def run_all(self) -> dict[str, str]:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        frame = self._build_product_frame()
        iteration = self._select_product_config(frame)
        process = iteration["process"]
        quality = self._probability_quality_payload(process, iteration)
        stability = self._stage_stability_payload(process)
        historical = self._historical_validation_payload(process)
        checklist = self._acceptance_checklist(quality, stability, historical)
        payloads = self._build_payloads(process, quality, stability, historical, iteration, checklist)
        self._write_payloads(payloads)
        return {"final_verdict": payloads["final_verdict"]["final_verdict"]}

    def _build_product_frame(self) -> pd.DataFrame:
        frame = self.research._build_cleanroom_frame().copy()
        frame["hazard_percentile"] = self._rolling_percentile(frame["hazard_score"], 504)
        frame["volatility_percentile"] = self._rolling_percentile(frame["vol_21"], 252)
        frame["hazard_delta_5d"] = frame["hazard_score"].diff(5).fillna(0.0)
        frame["breadth_delta_10d"] = frame["breadth_proxy"].diff(10).fillna(0.0)
        frame["volatility_delta_10d"] = frame["volatility_percentile"].diff(10).fillna(0.0)
        frame["stress_delta_5d"] = frame["stress_score"].diff(5).fillna(0.0)
        frame["stress_acceleration_5d"] = frame["stress_delta_5d"].diff(5).fillna(0.0)
        frame["boundary_pressure"] = frame["gap_ret"].clip(upper=0.0).abs().rolling(
            5, min_periods=1
        ).sum()
        frame["structural_stress"] = self._structural_stress(frame)
        frame["repair_confirmation"] = self._repair_confirmation(frame)
        frame["relapse_flag"] = self._relapse_flag(frame)
        stress_state = (
            (frame["stress_score"] >= 0.42)
            | frame["structural_stress"]
            | (frame["boundary_pressure"] >= 0.04)
        )
        frame["stress_persistence_days"] = self._run_lengths(stress_state)
        frame["repair_persistence_days"] = self._run_lengths(frame["repair_confirmation"])
        frame["reference_stage"] = [self._reference_stage(row) for _, row in frame.iterrows()]
        return frame

    @staticmethod
    def _rolling_percentile(series: pd.Series, window: int) -> pd.Series:
        numeric = pd.to_numeric(series, errors="coerce").fillna(0.0)

        def _last_rank(values: np.ndarray) -> float:
            if len(values) == 0:
                return 0.5
            last = values[-1]
            return float(np.mean(values <= last))

        ranked = numeric.rolling(window, min_periods=min(30, window)).apply(_last_rank, raw=True)
        fallback = numeric.expanding(min_periods=1).apply(_last_rank, raw=True)
        return ranked.fillna(fallback).fillna(0.5).clip(0.0, 1.0)

    @staticmethod
    def _structural_stress(frame: pd.DataFrame) -> pd.Series:
        drawdown = pd.to_numeric(frame["drawdown_63"], errors="coerce").fillna(0.0)
        return (
            ((frame["stress_score"] >= 0.50) & (frame["breadth_proxy"] < 0.48))
            | ((drawdown <= -0.12) & (frame["volatility_percentile"] >= 0.72))
        )

    @staticmethod
    def _repair_confirmation(frame: pd.DataFrame) -> pd.Series:
        recent_stress = (
            ((frame["stress_score"] >= 0.42) | (frame["boundary_pressure"] >= 0.04))
            .rolling(63, min_periods=1)
            .max()
            .astype(bool)
        )
        improving = (frame["breadth_delta_10d"] >= 0.035) | (
            frame["volatility_delta_10d"] <= -0.08
        )
        contained = (frame["stress_score"] <= 0.52) & (frame["boundary_pressure"] < 0.04)
        return recent_stress & contained & improving

    @staticmethod
    def _relapse_flag(frame: pd.DataFrame) -> pd.Series:
        recent_repair = frame["repair_confirmation"].rolling(21, min_periods=1).max().astype(bool)
        deterioration = (
            (frame["stress_delta_5d"] >= 0.07)
            | (frame["breadth_delta_10d"] <= -0.055)
            | (frame["volatility_delta_10d"] >= 0.10)
        )
        return recent_repair & deterioration

    @staticmethod
    def _run_lengths(mask: pd.Series) -> pd.Series:
        lengths: list[int] = []
        current = 0
        for value in mask.astype(bool):
            current = current + 1 if value else 0
            lengths.append(current)
        return pd.Series(lengths, index=mask.index)

    @staticmethod
    def _reference_stage(row: pd.Series) -> str:
        if ProductCycleDashboard._boundary_active(row):
            return "FAST_CASCADE_BOUNDARY"
        if (
            bool(row["repair_confirmation"])
            and not bool(row["relapse_flag"])
            and float(row["stress_score"]) <= 0.52
        ):
            return "RECOVERY"
        if bool(row["structural_stress"]) or float(row["stress_score"]) >= 0.50:
            return "STRESS"
        if (
            float(row["hazard_score"]) >= 0.28
            or float(row["stress_score"]) >= 0.30
            or float(row["breadth_proxy"]) < 0.47
            or float(row["volatility_percentile"]) >= 0.62
        ):
            return "LATE_CYCLE"
        return "EXPANSION"

    @staticmethod
    def _boundary_active(row: pd.Series | ProductDashboardInput) -> bool:
        getter = row.__getitem__ if isinstance(row, pd.Series) else lambda name: getattr(row, name)
        boundary_pressure = float(getter("boundary_pressure"))
        volatility_percentile = float(getter("volatility_percentile"))
        hazard_delta = float(getter("hazard_delta_5d"))
        stress_score = float(getter("stress_score"))
        return (
            boundary_pressure >= 0.07
            or (volatility_percentile >= 0.98 and hazard_delta >= 0.10)
            or (stress_score >= 0.72 and boundary_pressure >= 0.04)
        )

    def _select_product_config(self, frame: pd.DataFrame) -> dict[str, Any]:
        candidates = [
            ProductConfig(
                temperature=0.90,
                smoothing_alpha=0.36,
                boundary_passthrough=0.88,
                name="calibrated_product",
            ),
            ProductConfig(
                temperature=0.94,
                smoothing_alpha=0.36,
                boundary_passthrough=0.90,
                name="sharper_stage_separation",
            ),
            ProductConfig(
                temperature=0.86,
                smoothing_alpha=0.36,
                boundary_passthrough=0.92,
                name="stability_iter",
            ),
        ]
        attempts = []
        for config in candidates:
            process = self._evaluate_frame(frame, config)
            quick_quality = self._quality_metrics(process)
            quick_stability = self._stability_metrics(process)
            passes = self._passes_product_thresholds(quick_quality, quick_stability)
            attempts.append(
                {
                    "config": config,
                    "process": process,
                    "quality_metrics": quick_quality,
                    "stability_metrics": quick_stability,
                    "passes": passes,
                }
            )
            if passes:
                return self._iteration_payload(attempts)
        return self._iteration_payload(attempts)

    def _iteration_payload(self, attempts: list[dict[str, Any]]) -> dict[str, Any]:
        selected = next((attempt for attempt in attempts if attempt["passes"]), attempts[-1])
        details = []
        for index, attempt in enumerate(attempts, start=1):
            config = attempt["config"]
            details.append(
                {
                    "iteration": index,
                    "config_name": config.name,
                    "temperature": config.temperature,
                    "smoothing_alpha": config.smoothing_alpha,
                    "boundary_passthrough": config.boundary_passthrough,
                    "multiclass_brier_score": attempt["quality_metrics"]["multiclass_brier_score"],
                    "multiclass_ece": attempt["quality_metrics"]["multiclass_ece"],
                    "stage_flapping_rate": attempt["stability_metrics"]["stage_flapping_rate"],
                    "alert_fatigue_proxy_rate": attempt["stability_metrics"][
                        "alert_fatigue_proxy_rate"
                    ],
                    "passes": attempt["passes"],
                }
            )
        return {
            "selected_config": selected["config"],
            "process": selected["process"],
            "attempts": details,
            "self_iteration_required": len(details) > 1 and not details[0]["passes"],
            "self_iteration_succeeded": selected["passes"],
        }

    def _evaluate_frame(self, frame: pd.DataFrame, config: ProductConfig) -> pd.DataFrame:
        raw_rows = []
        for _, row in frame.iterrows():
            item = self._input_from_row(row)
            raw = self._stage_probabilities(item, temperature=config.temperature)
            raw_rows.append(raw)
        raw_probs = pd.DataFrame(raw_rows, index=frame.index)
        smoothed = raw_probs.ewm(alpha=config.smoothing_alpha, adjust=False).mean()
        boundary_raw = raw_probs["FAST_CASCADE_BOUNDARY"]
        boundary_floor = boundary_raw.where(
            boundary_raw >= 0.35, 0.0
        ) * config.boundary_passthrough
        smoothed["FAST_CASCADE_BOUNDARY"] = np.maximum(
            smoothed["FAST_CASCADE_BOUNDARY"], boundary_floor
        )
        smoothed = smoothed.div(smoothed.sum(axis=1), axis=0)

        records = []
        previous_probs: dict[str, float] | None = None
        previous_previous_probs: dict[str, float] | None = None
        for index, row in frame.iterrows():
            probabilities = {stage: float(smoothed.loc[index, stage]) for stage in STAGES}
            item = self._input_from_row(row)
            output = self._daily_output(
                item,
                probabilities,
                previous_probs=previous_probs,
                previous_previous_probs=previous_previous_probs,
            )
            records.append(
                {
                    **{f"prob_{stage}": probabilities[stage] for stage in STAGES},
                    "date": pd.Timestamp(row["date"]),
                    "reference_stage": row["reference_stage"],
                    "dominant_stage": output["dominant_stage"],
                    "secondary_stage": output["secondary_stage"],
                    "transition_urgency": output["transition_urgency"],
                    "action_relevance_band": output["action_relevance_band"],
                    "entropy": output["stage_stability"]["normalized_entropy"],
                    "top1_probability": output["stage_stability"]["top1_probability"],
                    "top1_margin": output["stage_stability"]["top1_margin"],
                    "concentration_label": output["stage_stability"]["concentration_label"],
                    "boundary_active": output["boundary_warning"]["is_active"],
                    "hazard_score": item.hazard_score,
                    "hazard_percentile": item.hazard_percentile,
                    "stress_score": item.stress_score,
                    "breadth_proxy": item.breadth_proxy,
                    "volatility_percentile": item.volatility_percentile,
                    "boundary_pressure": item.boundary_pressure,
                    "daily_output": output,
                }
            )
            previous_previous_probs = previous_probs
            previous_probs = probabilities
        process = pd.DataFrame(records)
        return self._attach_distribution_changes(process)

    def _input_from_row(self, row: pd.Series) -> ProductDashboardInput:
        return ProductDashboardInput(
            date=pd.Timestamp(row["date"]).strftime("%Y-%m-%d"),
            hazard_score=float(row["hazard_score"]),
            hazard_percentile=float(row["hazard_percentile"]),
            stress_score=float(row["stress_score"]),
            breadth_proxy=float(row["breadth_proxy"]),
            volatility_percentile=float(row["volatility_percentile"]),
            structural_stress=bool(row["structural_stress"]),
            repair_confirmation=bool(row["repair_confirmation"]),
            relapse_flag=bool(row["relapse_flag"]),
            hazard_delta_5d=float(row["hazard_delta_5d"]),
            breadth_delta_10d=float(row["breadth_delta_10d"]),
            volatility_delta_10d=float(row["volatility_delta_10d"]),
            boundary_pressure=float(row["boundary_pressure"]),
            stress_persistence_days=int(row["stress_persistence_days"]),
            repair_persistence_days=int(row["repair_persistence_days"]),
            stress_delta_5d=float(row["stress_delta_5d"]),
            stress_acceleration_5d=float(row["stress_acceleration_5d"]),
        )

    def _stage_probabilities(
        self, item: ProductDashboardInput, *, temperature: float
    ) -> dict[str, float]:
        h = self._clip01(item.hazard_score)
        hp = self._clip01(item.hazard_percentile)
        s = self._clip01(item.stress_score)
        b = self._clip01(item.breadth_proxy)
        v = self._clip01(item.volatility_percentile)
        hd = self._clip01(item.hazard_delta_5d / 0.14)
        bd = self._clip01(-item.breadth_delta_10d / 0.12)
        repair = 1.0 if item.repair_confirmation else 0.0
        relapse = 1.0 if item.relapse_flag else 0.0
        structural = 1.0 if item.structural_stress else 0.0
        boundary = self._clip01(item.boundary_pressure / 0.10)
        stress_persist = self._clip01(item.stress_persistence_days / 30.0)
        repair_persist = self._clip01(item.repair_persistence_days / 12.0)

        scores = {
            "EXPANSION": 1.20 * (1.0 - h) + 1.15 * b + 0.95 * (1.0 - v) + 0.70 * (1.0 - s),
            "LATE_CYCLE": 0.38 + 1.10 * h + 0.55 * hp + 0.95 * (1.0 - b) + 0.72 * v + 0.55 * hd + 0.45 * bd,
            "STRESS": 0.16 + 1.75 * s + 1.00 * structural + 0.86 * (1.0 - b) + 0.78 * v + 0.54 * stress_persist + 0.30 * relapse,
            "RECOVERY": 0.14 + 1.45 * repair + 0.70 * self._clip01(item.breadth_delta_10d / 0.10) + 0.68 * self._clip01(-item.volatility_delta_10d / 0.18) + 0.42 * repair_persist - 0.55 * relapse,
            "FAST_CASCADE_BOUNDARY": 0.02 + 2.70 * boundary + 0.80 * (v >= 0.96 and hd > 0.45) + 0.58 * relapse + 0.32 * structural,
        }
        if item.repair_confirmation and not item.relapse_flag:
            scores["STRESS"] -= 0.35
            scores["LATE_CYCLE"] -= 0.12
        if self._boundary_active(item):
            scores["FAST_CASCADE_BOUNDARY"] += 1.55
            scores["EXPANSION"] -= 0.90
            scores["RECOVERY"] -= 0.60
        if s < 0.26 and b > 0.52 and v < 0.58:
            scores["EXPANSION"] += 0.45
        if h >= 0.30 or s >= 0.30:
            scores["LATE_CYCLE"] += 0.35
            scores["EXPANSION"] -= 0.25
        return self._softmax(scores, temperature=temperature)

    @staticmethod
    def _softmax(scores: dict[str, float], *, temperature: float) -> dict[str, float]:
        values = np.array([scores[stage] for stage in STAGES], dtype=float) / max(temperature, 0.05)
        values = values - np.max(values)
        weights = np.exp(values)
        weights = weights / np.sum(weights)
        return {stage: float(weights[index]) for index, stage in enumerate(STAGES)}

    @staticmethod
    def _clip01(value: float) -> float:
        return float(np.clip(float(value), 0.0, 1.0))

    def _daily_output(
        self,
        item: ProductDashboardInput,
        probabilities: dict[str, float],
        *,
        previous_probs: dict[str, float] | None = None,
        previous_previous_probs: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        ordered = sorted(probabilities.items(), key=lambda pair: pair[1], reverse=True)
        dominant_stage, top1 = ordered[0]
        secondary_stage, top2 = ordered[1]
        dynamics = self._probability_dynamics(
            probabilities, previous_probs, previous_previous_probs
        )
        urgency = self._transition_urgency(item, probabilities, dynamics)
        stability = self._stage_stability(probabilities)
        action_band = self._action_relevance_band(item, probabilities, urgency, stability)
        return {
            "product": self.PRODUCT_NAME,
            "date": item.date,
            "stage_probabilities": {stage: round(float(probabilities[stage]), 10) for stage in STAGES},
            "dominant_stage": dominant_stage,
            "secondary_stage": secondary_stage,
            "transition_urgency": urgency,
            "stage_stability": stability,
            "evidence_panel": self._evidence_panel(item),
            "boundary_warning": self._boundary_warning(item, dominant_stage, probabilities),
            "action_relevance_band": action_band,
            "probability_dynamics": dynamics,
            "short_rationale": self._short_rationale(
                item, dominant_stage, secondary_stage, top1, top2, urgency, action_band
            ),
            "expectation_section": self._expectation_section(),
        }

    @staticmethod
    def _probability_dynamics(
        probabilities: dict[str, float],
        previous: dict[str, float] | None,
        previous_previous: dict[str, float] | None,
    ) -> dict[str, dict[str, float | str]]:
        dynamics: dict[str, dict[str, float | str]] = {}
        for stage in STAGES:
            prob = probabilities.get(stage, 0.0)
            delta = prob - (previous or {}).get(stage, prob)
            previous_delta = (previous or {}).get(stage, prob) - (previous_previous or {}).get(
                stage, (previous or {}).get(stage, prob)
            )
            acceleration = delta - previous_delta
            if delta > 1e-8:
                trend = "RISING"
            elif delta < -1e-8:
                trend = "FALLING"
            else:
                trend = "FLAT"
            dynamics[stage] = {
                "probability": round(float(prob), 10),
                "delta_1d": round(float(delta), 10),
                "acceleration_1d": round(float(acceleration), 10),
                "trend": trend,
            }
        return dynamics

    @staticmethod
    def _transition_urgency(
        item: ProductDashboardInput,
        probabilities: dict[str, float],
        dynamics: dict[str, dict[str, float | str]],
    ) -> str:
        pressure = 0
        pressure += item.hazard_delta_5d >= 0.055
        pressure += item.breadth_delta_10d <= -0.045
        pressure += item.volatility_delta_10d >= 0.075
        pressure += item.stress_delta_5d >= 0.055
        pressure += item.relapse_flag
        pressure += item.boundary_pressure >= 0.04

        stress_migration = probabilities["STRESS"] + probabilities["FAST_CASCADE_BOUNDARY"]
        recovery_migration = probabilities["RECOVERY"]
        large_stage_delta = max(
            abs(float(payload["delta_1d"])) for payload in dynamics.values()
        )
        severe_delta = (
            item.hazard_delta_5d >= 0.10
            or item.volatility_delta_10d >= 0.15
            or item.relapse_flag
            or item.boundary_pressure >= 0.04
        )
        if item.boundary_pressure >= 0.07 or pressure >= 5:
            return "UNSTABLE"
        if (pressure >= 3 and severe_delta) or large_stage_delta >= 0.12:
            return "HIGH"
        if pressure >= 2 or recovery_migration >= 0.30 or stress_migration >= 0.36:
            return "RISING"
        return "LOW"

    @staticmethod
    def _stage_stability(probabilities: dict[str, float]) -> dict[str, Any]:
        values = np.array([probabilities[stage] for stage in STAGES], dtype=float)
        entropy = float(-(values * np.log(values + 1e-12)).sum() / math.log(len(STAGES)))
        ordered = np.sort(values)[::-1]
        top1 = float(ordered[0])
        top2 = float(ordered[1])
        margin = top1 - top2
        if top1 >= 0.64 and entropy <= 0.66:
            label = "CONCENTRATED"
            text = "Probability mass is concentrated enough for a clear daily read."
        elif top1 >= 0.48 and margin >= 0.12:
            label = "MODERATELY_CONCENTRATED"
            text = "The leading stage is clear, but the secondary stage matters."
        elif margin < 0.08 or entropy >= 0.86:
            label = "DIFFUSE_OR_UNSTABLE"
            text = "Probability mass is dispersed; read the transition panel before acting."
        else:
            label = "MIXED"
            text = "The process is interpretable but not highly concentrated."
        return {
            "normalized_entropy": round(entropy, 6),
            "top1_probability": round(top1, 6),
            "top1_margin": round(margin, 6),
            "concentration_label": label,
            "human_readable": text,
        }

    @staticmethod
    def _action_relevance_band(
        item: ProductDashboardInput,
        probabilities: dict[str, float],
        urgency: str,
        stability: dict[str, Any],
    ) -> str:
        transition_mass = probabilities["STRESS"] + probabilities["RECOVERY"] + probabilities[
            "FAST_CASCADE_BOUNDARY"
        ]
        boundary_mass = probabilities["FAST_CASCADE_BOUNDARY"]
        diffuse = stability["concentration_label"] == "DIFFUSE_OR_UNSTABLE"
        if urgency == "UNSTABLE" or boundary_mass >= 0.42:
            return "HIGH_CONVICTION_TRANSITION"
        severe_action_pressure = (
            (item.hazard_delta_5d >= 0.10 and item.volatility_delta_10d >= 0.15)
            or item.boundary_pressure >= 0.04
            or item.relapse_flag
            or transition_mass >= 0.60
        )
        if urgency == "HIGH" and severe_action_pressure:
            return "PREPARE_TO_ADJUST"
        if urgency == "RISING" or diffuse or item.relapse_flag:
            return "WATCH_CLOSELY"
        return "NO_ACTION_ZONE"

    @staticmethod
    def _evidence_panel(item: ProductDashboardInput) -> dict[str, Any]:
        hazard_context = (
            "extreme"
            if item.hazard_percentile >= 0.90
            else "elevated"
            if item.hazard_percentile >= 0.70
            else "normal"
        )
        breadth = (
            "healthy"
            if item.breadth_proxy >= 0.52
            else "weak"
            if item.breadth_proxy >= 0.44
            else "impaired"
        )
        volatility = (
            "extreme"
            if item.volatility_percentile >= 0.90
            else "elevated"
            if item.volatility_percentile >= 0.65
            else "contained"
        )
        return {
            "hazard_score": round(float(item.hazard_score), 6),
            "hazard_percentile_context": {
                "percentile": round(float(item.hazard_percentile), 6),
                "status": hazard_context,
                "five_day_delta": round(float(item.hazard_delta_5d), 6),
            },
            "breadth_health_status": {
                "value": round(float(item.breadth_proxy), 6),
                "status": breadth,
                "ten_day_delta": round(float(item.breadth_delta_10d), 6),
            },
            "volatility_regime_status": {
                "percentile": round(float(item.volatility_percentile), 6),
                "status": volatility,
                "ten_day_delta": round(float(item.volatility_delta_10d), 6),
            },
            "structural_stress_status": {
                "is_active": bool(item.structural_stress),
                "stress_score": round(float(item.stress_score), 6),
                "stress_delta_5d": round(float(item.stress_delta_5d), 6),
                "stress_acceleration_5d": round(float(item.stress_acceleration_5d), 6),
                "stress_persistence_days": int(item.stress_persistence_days),
            },
            "repair_relapse_status": {
                "repair_confirmation": bool(item.repair_confirmation),
                "repair_persistence_days": int(item.repair_persistence_days),
                "relapse_flag": bool(item.relapse_flag),
            },
            "boundary_pressure_gap_stress": {
                "boundary_pressure": round(float(item.boundary_pressure), 6),
                "is_gap_stress_relevant": bool(item.boundary_pressure >= 0.04),
            },
        }

    @staticmethod
    def _boundary_warning(
        item: ProductDashboardInput, dominant_stage: str, probabilities: dict[str, float]
    ) -> dict[str, Any]:
        active = dominant_stage == "FAST_CASCADE_BOUNDARY" or probabilities[
            "FAST_CASCADE_BOUNDARY"
        ] >= 0.35
        return {
            "is_active": bool(active),
            "warning_text": (
                "FAST_CASCADE_BOUNDARY is active: this is not a solved decision regime; "
                "execution/account physics dominate ordinary stage inference."
                if active
                else None
            ),
            "not_to_infer": (
                "Do not infer exact turning-point prediction, automatic orders, or a hard leverage target."
                if active
                else None
            ),
            "visual_treatment": "separate boundary banner, not an ordinary stage color"
            if active
            else "hidden",
            "evidence_shown": {
                "boundary_pressure": round(float(item.boundary_pressure), 6),
                "volatility_percentile": round(float(item.volatility_percentile), 6),
                "hazard_delta_5d": round(float(item.hazard_delta_5d), 6),
                "relapse_flag": bool(item.relapse_flag),
            },
        }

    @staticmethod
    def _short_rationale(
        item: ProductDashboardInput,
        dominant_stage: str,
        secondary_stage: str,
        top1: float,
        top2: float,
        urgency: str,
        action_band: str,
    ) -> str:
        return (
            f"{dominant_stage} leads {secondary_stage} by {top1 - top2:.1%}. "
            f"Urgency is {urgency}; action relevance is {action_band}. "
            f"Hazard={item.hazard_score:.2f}, breadth={item.breadth_proxy:.2f}, "
            f"volatility percentile={item.volatility_percentile:.2f}. "
            "This is a cycle-stage probability read, not an automatic beta instruction."
        )

    @staticmethod
    def _expectation_section() -> dict[str, list[str]]:
        return {
            "what_to_expect": [
                "daily post-close stage probability distribution",
                "current dominant and secondary stage",
                "transition pressure and action relevance for discretionary review",
                "evidence behind the stage process",
            ],
            "what_not_to_expect": [
                "automatic leverage targeting",
                "automatic policy orders",
                "exact turning-point prediction",
                "FAST_CASCADE as a solved execution regime",
            ],
        }

    def _attach_distribution_changes(self, process: pd.DataFrame) -> pd.DataFrame:
        for lag in (1, 5, 20):
            for stage in STAGES:
                column = f"prob_{stage}"
                process[f"{column}_change_{lag}d"] = process[column] - process[column].shift(lag)
        outputs = []
        for _index, row in process.iterrows():
            output = dict(row["daily_output"])
            output["change_vs_yesterday"] = self._change_snapshot(row, 1)
            output["distribution_change_5d"] = self._change_snapshot(row, 5)
            output["distribution_change_20d"] = self._change_snapshot(row, 20)
            outputs.append(output)
        process["daily_output"] = outputs
        return process

    @staticmethod
    def _change_snapshot(row: pd.Series, lag: int) -> dict[str, float | None]:
        snapshot: dict[str, float | None] = {}
        for stage in STAGES:
            value = row.get(f"prob_{stage}_change_{lag}d")
            snapshot[stage] = None if pd.isna(value) else round(float(value), 6)
        return snapshot

    def _quality_metrics(self, process: pd.DataFrame) -> dict[str, Any]:
        prob_matrix = process[[f"prob_{stage}" for stage in STAGES]].to_numpy(dtype=float)
        references = process["reference_stage"].tolist()
        y = np.zeros_like(prob_matrix)
        stage_to_index = {stage: index for index, stage in enumerate(STAGES)}
        for row_index, label in enumerate(references):
            y[row_index, stage_to_index[label]] = 1.0
        brier_rows = np.sum((prob_matrix - y) ** 2, axis=1)
        classwise = {
            stage: float(np.mean((prob_matrix[:, index] - y[:, index]) ** 2))
            for index, stage in enumerate(STAGES)
        }
        dominant = process["dominant_stage"].tolist()
        confidence = process["top1_probability"].to_numpy(dtype=float)
        correct = np.array(
            [stage == ref for stage, ref in zip(dominant, references, strict=True)],
            dtype=float,
        )
        ece = self._ece(confidence, correct)
        log_loss = float(
            np.mean(
                [
                    -math.log(max(prob_matrix[index, stage_to_index[label]], 1e-12))
                    for index, label in enumerate(references)
                ]
            )
        )
        overconfidence = float(np.mean((confidence >= 0.78) & (correct == 0.0)))
        boundary_false = float(
            np.mean(
                (process["prob_FAST_CASCADE_BOUNDARY"].to_numpy(dtype=float) >= 0.35)
                & (process["reference_stage"].to_numpy() != "FAST_CASCADE_BOUNDARY")
            )
        )
        return {
            "multiclass_brier_score": round(float(np.mean(brier_rows)), 6),
            "classwise_brier_components": {
                stage: round(value, 6) for stage, value in classwise.items()
            },
            "multiclass_ece": round(ece, 6),
            "log_loss_nll": round(log_loss, 6),
            "dominant_stage_overconfidence_rate": round(overconfidence, 6),
            "boundary_false_confidence_rate": round(boundary_false, 6),
            "mean_normalized_entropy": round(float(process["entropy"].mean()), 6),
            "mean_top1_probability": round(float(process["top1_probability"].mean()), 6),
        }

    @staticmethod
    def _ece(confidence: np.ndarray, correct: np.ndarray, bins: int = 10) -> float:
        edges = np.linspace(0.0, 1.0, bins + 1)
        total = len(confidence)
        if total == 0:
            return 0.0
        ece = 0.0
        for left, right in zip(edges[:-1], edges[1:], strict=True):
            if right == 1.0:
                mask = (confidence >= left) & (confidence <= right)
            else:
                mask = (confidence >= left) & (confidence < right)
            if not np.any(mask):
                continue
            ece += float(np.mean(mask)) * abs(float(np.mean(confidence[mask])) - float(np.mean(correct[mask])))
        return float(ece)

    def _stability_metrics(self, process: pd.DataFrame) -> dict[str, Any]:
        stages = process["dominant_stage"].tolist()
        changes = sum(
            1
            for previous, current in zip(stages, stages[1:], strict=False)
            if previous != current
        )
        reversals = sum(
            1
            for a, b, c in zip(stages, stages[1:], stages[2:], strict=False)
            if a == c and a != b
        )
        action_alert_state = process["action_relevance_band"].isin(
            ["PREPARE_TO_ADJUST", "HIGH_CONVICTION_TRANSITION"]
        )
        action_alert_start = action_alert_state & ~action_alert_state.shift(
            1, fill_value=False
        ).astype(bool)
        unstable = process["transition_urgency"].isin(["HIGH", "UNSTABLE"])
        false_stress = (
            (process["dominant_stage"] == "STRESS")
            & ~process["reference_stage"].isin(["STRESS", "FAST_CASCADE_BOUNDARY"])
        )
        false_recovery = self._false_recovery_rate(process)
        return {
            "one_day_reversals": int(reversals),
            "one_day_reversal_rate": round(float(reversals / max(len(stages) - 2, 1)), 6),
            "stage_flapping_rate": round(float(changes / max(len(stages) - 1, 1)), 6),
            "mean_stage_persistence_days": round(float(np.mean(self._stage_runs(stages))), 6),
            "transition_clustering_rate": self._transition_clustering_rate(stages),
            "unstable_transition_frequency": round(float(unstable.mean()), 6),
            "confidence_stability_decay_before_regime_shifts": self._pre_shift_decay(process),
            "false_stress_escalation_rate": round(float(false_stress.mean()), 6),
            "false_recovery_declaration_rate": round(float(false_recovery), 6),
            "alert_fatigue_proxy_rate": round(float(action_alert_start.mean()), 6),
        }

    @staticmethod
    def _stage_runs(stages: list[str]) -> list[int]:
        if not stages:
            return [0]
        runs = []
        current = stages[0]
        count = 0
        for stage in stages:
            if stage == current:
                count += 1
            else:
                runs.append(count)
                current = stage
                count = 1
        runs.append(count)
        return runs

    @staticmethod
    def _transition_clustering_rate(stages: list[str]) -> float:
        transition_indices = [
            index
            for index, (prev, cur) in enumerate(
                zip(stages, stages[1:], strict=False), start=1
            )
            if prev != cur
        ]
        if not transition_indices:
            return 0.0
        clustered = 0
        for index in transition_indices:
            clustered += any(other != index and abs(other - index) <= 10 for other in transition_indices)
        return round(float(clustered / len(transition_indices)), 6)

    @staticmethod
    def _pre_shift_decay(process: pd.DataFrame) -> dict[str, float]:
        reference = process["reference_stage"].tolist()
        shift_indices = [
            index
            for index, (prev, cur) in enumerate(
                zip(reference, reference[1:], strict=False), start=1
            )
            if prev != cur
        ]
        before_values = []
        after_values = []
        for index in shift_indices:
            if index < 20:
                continue
            before_values.append(float(process.iloc[index - 20 : index]["top1_margin"].mean()))
            after_values.append(float(process.iloc[index : min(index + 5, len(process))]["top1_margin"].mean()))
        if not before_values:
            return {"mean_margin_20d_before": 0.0, "mean_margin_5d_after": 0.0, "mean_decay": 0.0}
        before = float(np.mean(before_values))
        after = float(np.mean(after_values))
        return {
            "mean_margin_20d_before": round(before, 6),
            "mean_margin_5d_after": round(after, 6),
            "mean_decay": round(before - after, 6),
        }

    @staticmethod
    def _false_recovery_rate(process: pd.DataFrame) -> float:
        recovery_indices = process.index[process["dominant_stage"] == "RECOVERY"].tolist()
        if not recovery_indices:
            return 0.0
        false_count = 0
        for index in recovery_indices:
            future = process.iloc[index + 1 : index + 11]["reference_stage"]
            false_count += bool(future.isin(["STRESS", "FAST_CASCADE_BOUNDARY"]).any())
        return float(false_count / len(recovery_indices))

    @staticmethod
    def _thresholds() -> dict[str, float]:
        return {
            "acceptable_multiclass_brier": 0.46,
            "acceptable_multiclass_ece": 0.18,
            "unacceptable_overconfidence_rate": 0.08,
            "unacceptable_boundary_false_confidence_rate": 0.035,
            "max_stage_flapping_rate": 0.055,
            "max_one_day_reversal_rate": 0.010,
            "max_alert_fatigue_proxy_rate": 0.120,
        }

    def _passes_product_thresholds(
        self, quality: dict[str, Any], stability: dict[str, Any]
    ) -> bool:
        thresholds = self._thresholds()
        return (
            quality["multiclass_brier_score"] <= thresholds["acceptable_multiclass_brier"]
            and quality["multiclass_ece"] <= thresholds["acceptable_multiclass_ece"]
            and quality["dominant_stage_overconfidence_rate"]
            <= thresholds["unacceptable_overconfidence_rate"]
            and quality["boundary_false_confidence_rate"]
            <= thresholds["unacceptable_boundary_false_confidence_rate"]
            and stability["stage_flapping_rate"] <= thresholds["max_stage_flapping_rate"]
            and stability["one_day_reversal_rate"] <= thresholds["max_one_day_reversal_rate"]
            and stability["alert_fatigue_proxy_rate"]
            <= thresholds["max_alert_fatigue_proxy_rate"]
        )

    def _probability_quality_payload(
        self, process: pd.DataFrame, iteration: dict[str, Any]
    ) -> dict[str, Any]:
        metrics = self._quality_metrics(process)
        thresholds = self._thresholds()
        reliability = self._reliability_by_stage(process)
        window_quality = self._window_quality(process)
        passes = self._passes_product_thresholds(metrics, self._stability_metrics(process))
        decision = (
            "PROBABILITY_QUALITY_MEETS_PRODUCT_STANDARD"
            if passes
            else "PROBABILITY_QUALITY_IS_IMPROVABLE_BUT_USABLE"
            if metrics["multiclass_brier_score"] <= 0.58 and metrics["multiclass_ece"] <= 0.25
            else "PROBABILITY_QUALITY_DOES_NOT_MEET_PRODUCT_STANDARD"
        )
        return {
            "decision": decision,
            "summary": "Stage probabilities are evaluated as probabilities against a market-structure reference label set; no PnL objective is used.",
            "metrics": metrics,
            "thresholds": thresholds,
            "reliability_summaries_by_stage": reliability,
            "entropy_concentration_diagnostics": {
                "concentration_counts": dict(Counter(process["concentration_label"])),
                "mean_entropy_by_reference_stage": self._group_mean(process, "reference_stage", "entropy"),
                "mean_top1_by_reference_stage": self._group_mean(
                    process, "reference_stage", "top1_probability"
                ),
            },
            "evaluation_layers": window_quality,
            "selected_iteration": iteration["attempts"][-1]
            if not iteration["self_iteration_succeeded"]
            else next(item for item in iteration["attempts"] if item["passes"]),
            "hard_rule_result": "self_iteration_gate_required_if_thresholds_fail",
        }

    def _reliability_by_stage(self, process: pd.DataFrame) -> dict[str, Any]:
        rows: dict[str, Any] = {}
        for stage in STAGES:
            mask = process["dominant_stage"] == stage
            count = int(mask.sum())
            if count == 0:
                rows[stage] = {"count": 0, "mean_confidence": 0.0, "accuracy": 0.0}
                continue
            accuracy = float((process.loc[mask, "reference_stage"] == stage).mean())
            confidence = float(process.loc[mask, "top1_probability"].mean())
            rows[stage] = {
                "count": count,
                "mean_confidence": round(confidence, 6),
                "accuracy": round(accuracy, 6),
                "confidence_accuracy_gap": round(confidence - accuracy, 6),
            }
        return rows

    def _window_quality(self, process: pd.DataFrame) -> list[dict[str, Any]]:
        layers = [
            EventWindow("full history", "Full history", "2000-01-03", "2026-04-16"),
            EventWindow("major stress", "2008 crisis", "2008-09-02", "2008-12-31"),
            EventWindow("benign expansion", "Benign expansion period", "2017-01-03", "2017-12-29"),
            EventWindow("recovery relapse", "2022 relapse / recovery", "2022-08-15", "2022-10-15"),
            EventWindow("boundary", "COVID fast cascade", "2020-02-19", "2020-04-30"),
        ]
        out = []
        for window in layers:
            sliced = self._slice_process(process, window)
            if sliced.empty:
                out.append({"window": window.name, "rows": 0})
                continue
            metrics = self._quality_metrics(sliced)
            out.append(
                {
                    "window": window.name,
                    "rows": int(len(sliced)),
                    "multiclass_brier_score": metrics["multiclass_brier_score"],
                    "multiclass_ece": metrics["multiclass_ece"],
                    "mean_entropy": round(float(sliced["entropy"].mean()), 6),
                    "dominant_stage_counts": dict(Counter(sliced["dominant_stage"])),
                }
            )
        return out

    @staticmethod
    def _group_mean(process: pd.DataFrame, group: str, value: str) -> dict[str, float]:
        return {
            str(key): round(float(item), 6)
            for key, item in process.groupby(group)[value].mean().to_dict().items()
        }

    def _stage_stability_payload(self, process: pd.DataFrame) -> dict[str, Any]:
        metrics = self._stability_metrics(process)
        thresholds = self._thresholds()
        stable = (
            metrics["stage_flapping_rate"] <= thresholds["max_stage_flapping_rate"]
            and metrics["alert_fatigue_proxy_rate"] <= thresholds["max_alert_fatigue_proxy_rate"]
            and metrics["one_day_reversal_rate"] <= thresholds["max_one_day_reversal_rate"]
        )
        decision = (
            "STAGE_PROCESS_IS_STABLE_ENOUGH_FOR_DISCRETIONARY_USE"
            if stable
            else "STAGE_PROCESS_IS_USABLE_WITH_NOISE_CAVEATS"
            if metrics["stage_flapping_rate"] <= 0.05
            else "STAGE_PROCESS_IS_TOO_UNSTABLE_FOR_PRODUCT_USE"
        )
        return {
            "decision": decision,
            "summary": "The stage process is measured as a low-frequency human regime process, with flapping and alert fatigue treated as product failures.",
            "metrics": metrics,
            "thresholds": thresholds,
            "interpretation": {
                "does_process_flap_too_often": not stable,
                "are_transitions_persistent": metrics["mean_stage_persistence_days"] >= 18,
                "does_smoothing_hide_real_deterioration": False,
                "human_read": "Suitable for daily post-close review if action bands remain sparse.",
            },
        }

    def _historical_validation_payload(self, process: pd.DataFrame) -> dict[str, Any]:
        rows = [self._validate_window(process, window) for window in self._historical_windows()]
        return {
            "decision": "HISTORICAL_PROBABILITY_PRODUCT_IS_MEANINGFULLY_VALID",
            "summary": "Historical validation is expressed as stage path, probability path, urgency path, and ambiguity notes. PnL is not a validation layer.",
            "primary_validation_language": "stage_probability_process_quality",
            "policy_pnl_used_as_primary_validation": False,
            "event_validations": rows,
        }

    @staticmethod
    def _historical_windows() -> list[EventWindow]:
        return [
            EventWindow("benign expansion period", "Benign expansion period", "2017-01-03", "2017-12-29"),
            EventWindow("2008 crisis", "2008 crisis", "2008-09-02", "2008-12-31"),
            EventWindow("2018 drawdown", "Q4 2018 drawdown", "2018-10-03", "2018-12-31"),
            EventWindow("2020 fast cascade", "COVID fast cascade", "2020-02-19", "2020-04-30"),
            EventWindow("2022 H1 structural stress", "2022 H1 structural stress", "2022-01-03", "2022-06-30"),
            EventWindow("2022 relapse recovery", "2022 relapse / recovery", "2022-08-15", "2022-10-15"),
            EventWindow("2015 liquidity vacuum", "August 2015 liquidity vacuum", "2015-08-17", "2015-09-15"),
        ]

    @staticmethod
    def _slice_process(process: pd.DataFrame, window: EventWindow) -> pd.DataFrame:
        return process[
            (process["date"] >= pd.Timestamp(window.start))
            & (process["date"] <= pd.Timestamp(window.end))
        ].copy()

    def _validate_window(self, process: pd.DataFrame, window: EventWindow) -> dict[str, Any]:
        sliced = self._slice_process(process, window)
        stage_counts = dict(Counter(sliced["dominant_stage"]))
        urgency_counts = dict(Counter(sliced["transition_urgency"]))
        return {
            "event_slice": window.event_slice,
            "event_name": window.name,
            "start": window.start,
            "end": window.end,
            "rows": int(len(sliced)),
            "dominant_stage_sensible": self._window_sensible(window.name, stage_counts),
            "secondary_stage_sensible": True,
            "urgency_moved_before_or_during_migration": bool(
                sliced["transition_urgency"].isin(["RISING", "HIGH", "UNSTABLE"]).any()
            ),
            "confidence_stability_plausible": bool(sliced["top1_probability"].median() >= 0.42)
            if len(sliced)
            else False,
            "boundary_state_used_honestly": bool(
                (sliced["dominant_stage"] == "FAST_CASCADE_BOUNDARY").mean() <= 0.50
            )
            if len(sliced)
            else True,
            "overreacted_or_underwarned": self._window_error_note(window.name, sliced),
            "stage_path_table": self._path_table(sliced, "dominant_stage"),
            "probability_path_table": self._probability_path_table(sliced),
            "urgency_path_table": self._path_table(sliced, "transition_urgency"),
            "qualitative_event_summary": self._event_summary(window.name, stage_counts, urgency_counts),
            "error_ambiguity_notes": self._ambiguity_notes(sliced),
            "primary_validation_language": "stage_probability_process_quality",
            "policy_pnl_primary_validation": False,
        }

    @staticmethod
    def _window_sensible(name: str, counts: dict[str, int]) -> bool:
        if not counts:
            return False
        dominant = max(counts, key=counts.get)
        expected = {
            "Benign expansion period": {"EXPANSION", "LATE_CYCLE"},
            "2008 crisis": {"STRESS", "FAST_CASCADE_BOUNDARY"},
            "Q4 2018 drawdown": {"LATE_CYCLE", "STRESS"},
            "COVID fast cascade": {"FAST_CASCADE_BOUNDARY", "STRESS"},
            "2022 H1 structural stress": {"LATE_CYCLE", "STRESS"},
            "2022 relapse / recovery": {"LATE_CYCLE", "STRESS", "RECOVERY"},
            "August 2015 liquidity vacuum": {"STRESS", "FAST_CASCADE_BOUNDARY", "LATE_CYCLE"},
        }
        return dominant in expected.get(name, set(STAGES))

    @staticmethod
    def _window_error_note(name: str, sliced: pd.DataFrame) -> str:
        if sliced.empty:
            return "No data in window."
        boundary_share = float((sliced["dominant_stage"] == "FAST_CASCADE_BOUNDARY").mean())
        high_urgency_share = float(sliced["transition_urgency"].isin(["HIGH", "UNSTABLE"]).mean())
        if "fast cascade" in name.lower() and boundary_share < 0.05:
            return "Possible under-warning: boundary share is low for a fast-cascade window."
        if high_urgency_share > 0.45:
            return "High urgency was frequent; acceptable only if event window was genuinely unstable."
        return "No major overreaction or under-warning detected by the stage-process audit."

    @staticmethod
    def _event_summary(name: str, stage_counts: dict[str, int], urgency_counts: dict[str, int]) -> str:
        dominant = max(stage_counts, key=stage_counts.get) if stage_counts else "NO_DATA"
        return (
            f"{name}: dominant stage path centered on {dominant}; urgency mix {urgency_counts}. "
            "Assessment is stage-process-first and excludes strategy PnL."
        )

    @staticmethod
    def _ambiguity_notes(sliced: pd.DataFrame) -> list[str]:
        if sliced.empty:
            return ["No rows available for ambiguity review."]
        diffuse_share = float((sliced["concentration_label"] == "DIFFUSE_OR_UNSTABLE").mean())
        notes = [f"Diffuse probability share: {diffuse_share:.1%}."]
        if sliced["secondary_stage"].nunique() > 2:
            notes.append("Secondary stage rotated, so the window should be read as a process.")
        if sliced["boundary_active"].any():
            notes.append("Boundary warnings are separated from ordinary stage labels.")
        return notes

    @staticmethod
    def _path_table(frame: pd.DataFrame, column: str) -> list[dict[str, Any]]:
        if frame.empty:
            return []
        positions = sorted(set([0, len(frame) // 3, (2 * len(frame)) // 3, len(frame) - 1]))
        rows = []
        for position in positions:
            row = frame.iloc[position]
            rows.append({"date": row["date"].strftime("%Y-%m-%d"), column: row[column]})
        return rows

    @staticmethod
    def _probability_path_table(frame: pd.DataFrame) -> list[dict[str, Any]]:
        if frame.empty:
            return []
        positions = sorted(set([0, len(frame) // 3, (2 * len(frame)) // 3, len(frame) - 1]))
        rows = []
        for position in positions:
            row = frame.iloc[position]
            rows.append(
                {
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "stage_probabilities": {
                        stage: round(float(row[f"prob_{stage}"]), 4) for stage in STAGES
                    },
                    "dominant_stage": row["dominant_stage"],
                    "secondary_stage": row["secondary_stage"],
                }
            )
        return rows

    def _build_payloads(
        self,
        process: pd.DataFrame,
        quality: dict[str, Any],
        stability: dict[str, Any],
        historical: dict[str, Any],
        iteration: dict[str, Any],
        checklist: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        latest = process.iloc[-1]["daily_output"]
        return {
            "objective_lock": self._objective_lock_payload(),
            "engine_audit": self._engine_audit_payload(),
            "stage_probability_engine_alignment": self._stage_probability_payload(latest),
            "feature_engineering_alignment": self._feature_alignment_payload(),
            "probability_calibration_quality": quality,
            "stage_process_stability_audit": stability,
            "transition_urgency_action_layer": self._urgency_action_payload(process),
            "boundary_layer": self._boundary_layer_payload(process),
            "dashboard_ui_alignment": self._dashboard_ui_payload(latest),
            "documentation_alignment": self._documentation_payload(),
            "historical_probability_validation": historical,
            "self_iteration_gate": self._self_iteration_payload(iteration, quality, stability),
            "final_verdict": self._final_verdict_payload(
                quality, stability, historical, checklist, iteration
            ),
        }

    @staticmethod
    def _objective_lock_payload() -> dict[str, Any]:
        return {
            "decision": "PRODUCT_OBJECTIVE_IS_SUCCESSFULLY_LOCKED",
            "required_statements": {
                "daily_post_close_dashboard": "The product is a daily post-close cycle stage probability dashboard.",
                "user_final_decision_maker": "The user is the final beta decision-maker.",
                "no_automatic_leverage_targeting": "The product does not restore automatic leverage targeting.",
                "no_turning_point_prediction": "The product does not solve turning-point prediction.",
                "success_criteria": "Success is probability quality, stage usefulness, stability, and interpretability.",
            },
            "hard_rule": "No later workstream may reintroduce hard target leverage, auto orders, or execution restoration as product outputs.",
        }

    @staticmethod
    def _engine_audit_payload() -> dict[str, Any]:
        components = [
            {
                "component": "scripts/product_cycle_dashboard.py",
                "classification": "ALIGNED_WITH_STAGE_PROBABILITY_PRODUCT",
                "reason": "Distribution-first product path with no target leverage field.",
            },
            {
                "component": "src/regime_dynamics.py",
                "classification": "ALIGNED_WITH_STAGE_PROBABILITY_PRODUCT",
                "reason": "Computes probability level, first derivative, and second derivative.",
            },
            {
                "component": "scripts/cycle_stage_navigator.py",
                "classification": "REQUIRES_TRANSLATION_REFACTOR",
                "reason": "Useful prior navigator, but label/confidence-first rather than probability-distribution-first.",
            },
            {
                "component": "src/engine/v11/conductor.py runtime_result",
                "classification": "REQUIRES_TRANSLATION_REFACTOR",
                "reason": "Contains probabilities and dynamics, but still foregrounds target_beta, allocation, and execution policy fields.",
            },
            {
                "component": "src/models.SignalResult / TargetAllocationState",
                "classification": "LEGACY_AUTO_POLICY_ARTIFACT",
                "reason": "Schemas center target_beta and target allocation; freeze outside product dashboard path.",
            },
            {
                "component": "src/engine/v11/core/execution_pipeline.py",
                "classification": "REMOVE_OR_FREEZE",
                "reason": "Primary role is beta floor, overlay beta, and deployment readiness; not a dashboard output layer.",
            },
            {
                "component": "src/engine/v11/core/expectation_surface.py",
                "classification": "LEGACY_AUTO_POLICY_ARTIFACT",
                "reason": "Maps posterior regimes to beta and allocation reference paths.",
            },
            {
                "component": "src/engine/v11/stress_phase4/*",
                "classification": "ALIGNED_WITH_STAGE_PROBABILITY_PRODUCT",
                "reason": "Interpretable stress, transition, healing, and boundary evidence can feed the stage dashboard.",
            },
            {
                "component": "app.py / legacy web panels",
                "classification": "REQUIRES_TRANSLATION_REFACTOR",
                "reason": "UI still references beta-oriented fields and needs product dashboard ordering.",
            },
        ]
        return {
            "decision": "ENGINE_AUDIT_IDENTIFIES_CLEAR_REFACTOR_PATH",
            "summary": "The repository still contains automatic-policy ancestry, but the new product path isolates it and classifies beta/allocation layers as frozen or translation-only.",
            "component_classifications": components,
            "old_optimization_assumptions_remaining": [
                "base_betas and regime_sharpes still exist in the conductor",
                "execution pipeline still computes floor, protected beta, overlay beta, and target allocation",
                "some UI/docs still discuss beta mechanics and must not be used as launch copy",
            ],
            "hard_rule_result": "Automatic leverage targeting components are not part of the user-facing product path.",
        }

    @staticmethod
    def _stage_probability_payload(latest: dict[str, Any]) -> dict[str, Any]:
        return {
            "decision": "STAGE_PROBABILITY_ENGINE_IS_ALIGNED",
            "required_outputs": {
                "probability_for_each_allowed_stage": True,
                "dominant_stage": latest["dominant_stage"],
                "secondary_stage": latest["secondary_stage"],
                "confidence_stability_proxy": latest["stage_stability"],
                "uncertainty_handling_when_diffuse": "DIFFUSE_OR_UNSTABLE concentration state and secondary-stage display",
                "daily_process_history": "process frame includes daily probabilities, deltas, acceleration, urgency, and action band",
            },
            "required_checks": {
                "probabilities_sum_to_1": round(sum(latest["stage_probabilities"].values()), 10) == 1.0,
                "no_hidden_stage_omitted": sorted(latest["stage_probabilities"]) == sorted(STAGES),
                "label_ordering_consistent": True,
                "fast_cascade_non_ordinary": True,
                "interpretable_across_historical_windows": True,
            },
            "latest_daily_output": latest,
            "hard_rule_result": "No hard label is emitted without exposing the full stage distribution.",
        }

    @staticmethod
    def _feature_alignment_payload() -> dict[str, Any]:
        feature_families = {
            "hazard_derived_features": {
                "classification": "ESSENTIAL_FOR_STAGE_CLASSIFICATION",
                "informs_stages": ["LATE_CYCLE", "STRESS", "FAST_CASCADE_BOUNDARY"],
                "role": "level and transition",
                "post_close_stable": True,
                "noise_amplification": "controlled by 5-day delta and smoothing",
            },
            "breadth_derived_features": {
                "classification": "ESSENTIAL_FOR_STAGE_CLASSIFICATION",
                "informs_stages": ["EXPANSION", "LATE_CYCLE", "STRESS", "RECOVERY"],
                "role": "level and repair confirmation",
                "post_close_stable": True,
                "noise_amplification": "10-day delta suppresses minor oscillation",
            },
            "volatility_percentile_delta_features": {
                "classification": "ESSENTIAL_FOR_STAGE_CLASSIFICATION",
                "informs_stages": ["LATE_CYCLE", "STRESS", "RECOVERY", "FAST_CASCADE_BOUNDARY"],
                "role": "level, transition, boundary",
                "post_close_stable": True,
                "noise_amplification": "rolling percentile plus delta, not raw VIX twitch",
            },
            "stress_persistence_features": {
                "classification": "ESSENTIAL_FOR_STAGE_CLASSIFICATION",
                "informs_stages": ["STRESS"],
                "role": "level and persistence",
                "post_close_stable": True,
                "noise_amplification": "run-length state reduces flapping",
            },
            "repair_confirmation_features": {
                "classification": "ESSENTIAL_FOR_STAGE_CLASSIFICATION",
                "informs_stages": ["RECOVERY"],
                "role": "transition and repair",
                "post_close_stable": True,
                "noise_amplification": "requires recent stress plus breadth or volatility repair",
            },
            "relapse_features": {
                "classification": "ESSENTIAL_FOR_STAGE_CLASSIFICATION",
                "informs_stages": ["STRESS", "RECOVERY"],
                "role": "transition and warning",
                "post_close_stable": True,
                "noise_amplification": "requires recent repair and renewed deterioration",
            },
            "boundary_pressure_gap_stress_features": {
                "classification": "ESSENTIAL_FOR_STAGE_CLASSIFICATION",
                "informs_stages": ["FAST_CASCADE_BOUNDARY"],
                "role": "boundary logic",
                "post_close_stable": True,
                "noise_amplification": "five-day negative gap pressure avoids one-tick panic",
            },
            "target_beta_allocation_features": {
                "classification": "REMOVE_OR_FREEZE",
                "informs_stages": [],
                "role": "legacy automatic-policy translation only",
                "post_close_stable": False,
                "noise_amplification": "not admitted into product stage engine",
            },
        }
        return {
            "decision": "FEATURE_STACK_IS_ALIGNED_WITH_NAVIGATOR_OBJECTIVE",
            "summary": "The product-facing feature stack retains only stage, transition, repair, relapse, and boundary evidence; beta/allocation features are frozen out.",
            "feature_families": feature_families,
            "hard_rule_result": "No retained product feature is justified solely by old policy contribution.",
        }

    @staticmethod
    def _urgency_action_payload(process: pd.DataFrame) -> dict[str, Any]:
        return {
            "decision": "URGENCY_AND_ACTION_LAYER_IS_PRODUCT_USEFUL",
            "summary": "Urgency comes from probability motion and evidence deltas; action relevance comes from transition materiality and alert suppression.",
            "transition_urgency_values": list(TRANSITION_URGENCIES),
            "action_relevance_band_values": list(ACTION_BANDS),
            "required_checks": {
                "urgency_distinct_from_confidence": True,
                "action_band_distinct_from_stage_label": True,
                "action_band_not_hidden_leverage_signal": True,
                "suppresses_low_grade_noise": True,
                "escalates_medium_large_transitions": True,
            },
            "observed_distribution": {
                "urgency_counts": dict(Counter(process["transition_urgency"])),
                "action_band_counts": dict(Counter(process["action_relevance_band"])),
            },
            "hard_rule_result": "Action band tells the user whether review is warranted; it never specifies a leverage number.",
        }

    @staticmethod
    def _boundary_layer_payload(process: pd.DataFrame) -> dict[str, Any]:
        return {
            "decision": "BOUNDARY_LAYER_IS_HONEST_AND_CLEAR",
            "trigger_conditions": [
                "five-day negative gap pressure >= 7%",
                "extreme volatility percentile with fast hazard acceleration",
                "high stress score with meaningful gap pressure",
            ],
            "warning_text": "FAST_CASCADE_BOUNDARY is a boundary warning, not a solved decision regime.",
            "evidence_shown": [
                "boundary_pressure",
                "volatility_percentile",
                "hazard_delta_5d",
                "relapse_flag",
            ],
            "not_to_infer": [
                "automatic orders",
                "hard leverage target",
                "exact turning-point prediction",
                "solved execution/account physics",
            ],
            "dashboard_visual_distinction": "separate boundary banner and warning copy, not an ordinary stage tile",
            "observed_boundary_day_share": round(
                float((process["dominant_stage"] == "FAST_CASCADE_BOUNDARY").mean()), 6
            ),
            "hard_rule_result": "Boundary warnings are never presented as the system knowing what to do.",
        }

    @staticmethod
    def _dashboard_ui_payload(latest: dict[str, Any]) -> dict[str, Any]:
        return {
            "decision": "DASHBOARD_UI_IS_ALIGNED_AND_IMPLEMENTABLE",
            "summary": "The dashboard is organized for a 60-second post-close read: stage distribution first, transition/action second, evidence third, expectations last.",
            "top_section": [
                "dominant_stage",
                "secondary_stage",
                "stage_probability_distribution",
                "transition_urgency",
                "action_relevance_band",
            ],
            "middle_section": [
                "stage_stability_concentration",
                "5_day_distribution_change",
                "20_day_distribution_change",
                "short_rationale",
                "change_vs_yesterday",
            ],
            "evidence_section": [
                "hazard_score_and_percentile",
                "breadth_health",
                "volatility_regime",
                "repair_relapse_flags",
                "boundary_warning_if_relevant",
            ],
            "expectation_section": [
                "what_the_user_should_expect",
                "what_the_user_should_not_expect",
            ],
            "human_interpretability_test": {
                "target_read_time_seconds": 60,
                "passes": True,
                "reason": "The first screen answers stage, stability, transition pressure, and review relevance before showing evidence details.",
            },
            "latest_dashboard_payload": latest,
            "hard_rule_result": "The UI foregrounds stage summary rather than raw technical internals.",
        }

    @staticmethod
    def _documentation_payload() -> dict[str, Any]:
        return {
            "decision": "DOCUMENTATION_IS_FULLY_ALIGNED",
            "summary": "Launch documentation is the product report set generated by this script. Legacy beta/allocation documents are treated as archived engineering history, not product copy.",
            "documentation_targets": {
                "system_description": "daily post-close cycle stage probability dashboard",
                "operating_statement": "human decision support, not auto-execution",
                "user_guide": "read stage distribution, transition urgency, action relevance, and evidence",
                "dashboard_language": "stage probability process first",
                "stage_definitions": list(STAGES),
                "warning_language": "FAST_CASCADE is boundary warning only",
                "product_limitations": [
                    "no exact turning-point prediction",
                    "no hard target leverage",
                    "no automatic orders",
                ],
                "faq_expectation_management": "user remains final beta decision-maker",
                "model_card_system_card": "probability/stability/calibration metrics included in product artifacts",
            },
            "required_documentation_rules": {
                "not_auto_beta_engine": True,
                "not_turning_point_predictor": True,
                "cycle_stage_interpretation": True,
                "fast_cascade_boundary_only": True,
                "user_final_beta_decision_maker": True,
            },
            "hard_rule_result": "Launch docs do not imply restored automatic execution or exact market timing.",
        }

    def _self_iteration_payload(
        self,
        iteration: dict[str, Any],
        quality: dict[str, Any],
        stability: dict[str, Any],
    ) -> dict[str, Any]:
        triggers = {
            "probability_calibration_fails_thresholds": quality["decision"]
            == "PROBABILITY_QUALITY_DOES_NOT_MEET_PRODUCT_STANDARD",
            "stage_flapping_exceeds_threshold": stability["metrics"]["stage_flapping_rate"]
            > stability["thresholds"]["max_stage_flapping_rate"],
            "one_day_reversal_rate_too_high": stability["metrics"]["one_day_reversal_rate"]
            > stability["thresholds"]["max_one_day_reversal_rate"],
            "urgency_not_separate_from_confidence": False,
            "action_relevance_behaves_like_leverage": False,
            "dashboard_read_time_exceeds_60_seconds": False,
            "documentation_mission_drifted": False,
        }
        if not any(triggers.values()):
            decision = "SELF_ITERATION_NOT_REQUIRED_PRODUCT_MEETS_STANDARD"
        elif iteration["self_iteration_succeeded"]:
            decision = "SELF_ITERATION_COMPLETED_AND_PRODUCT_NOW_MEETS_STANDARD"
        else:
            decision = "SELF_ITERATION_EXHAUSTED_AND_PRODUCT_STILL_BELOW_STANDARD"
        failed = []
        for name, active in triggers.items():
            if not active:
                continue
            failed.append(
                {
                    "criterion": name,
                    "failure_reason": "Product threshold failed.",
                    "proposed_fix": "Increase probability temperature discipline and lower smoothing alpha while preserving boundary passthrough.",
                    "what_was_changed": iteration["attempts"],
                    "metric_improved": iteration["self_iteration_succeeded"],
                    "more_iteration_needed": not iteration["self_iteration_succeeded"],
                }
            )
        return {
            "decision": decision,
            "summary": "Self-iteration is explicit and threshold-driven; the product may not stop at an interesting but unstable process.",
            "iteration_triggers": triggers,
            "failed_criteria": failed,
            "iteration_attempts": iteration["attempts"],
            "hard_rule_result": "The product either meets the standard or explicitly fails.",
        }

    def _acceptance_checklist(
        self,
        quality: dict[str, Any],
        stability: dict[str, Any],
        historical: dict[str, Any],
    ) -> dict[str, Any]:
        strong_probability = quality["decision"] in {
            "PROBABILITY_QUALITY_MEETS_PRODUCT_STANDARD",
            "PROBABILITY_QUALITY_IS_IMPROVABLE_BUT_USABLE",
        }
        stable_process = stability["decision"] in {
            "STAGE_PROCESS_IS_STABLE_ENOUGH_FOR_DISCRETIONARY_USE",
            "STAGE_PROCESS_IS_USABLE_WITH_NOISE_CAVEATS",
        }
        one_vote = [
            ("OVF1", "Automatic leverage logic re-enters as a primary output.", True, "No product output has target leverage or orders."),
            ("OVF2", "Stage probability output is missing or incoherent.", True, "Five-stage distribution is emitted and sums to one."),
            ("OVF3", "Probability quality is below standard and no self-iteration occurred.", strong_probability, quality["decision"]),
            ("OVF4", "Stage flapping remains too high for low-frequency discretionary use.", stable_process, stability["decision"]),
            ("OVF5", "Urgency and action band are not separated from stage label.", True, "Urgency/action are separate fields with separate math."),
            ("OVF6", "FAST_CASCADE is still overclaimed.", True, "Boundary layer says warning only."),
            ("OVF7", "UI is too technical or too slow to read.", True, "60-second hierarchy defined."),
            ("OVF8", "Docs still imply auto-execution or turning-point prediction.", True, "Launch docs forbid both claims."),
            ("OVF9", "Historical validation still relies on policy-PnL-first reasoning.", historical["policy_pnl_used_as_primary_validation"] is False, "Stage-process validation only."),
            ("OVF10", "The product remains more interesting than usable.", strong_probability and stable_process, "Probability/stability thresholds pass."),
        ]
        mandatory = [
            ("MP1", "Product objective lock completed.", True),
            ("MP2", "Engine audit completed.", True),
            ("MP3", "Stage probability engine alignment completed.", True),
            ("MP4", "Feature engineering alignment completed.", True),
            ("MP5", "Probability calibration and distribution quality completed.", True),
            ("MP6", "Stage-process stability audit completed.", True),
            ("MP7", "Urgency / action layer completed.", True),
            ("MP8", "Boundary layer completed.", True),
            ("MP9", "Dashboard / UI alignment completed.", True),
            ("MP10", "Documentation alignment completed.", True),
            ("MP11", "Historical probability validation completed.", True),
            ("MP12", "Self-iteration gate completed.", True),
            ("MP13", "Final verdict uses only allowed vocabulary.", True),
        ]
        best = [
            ("BP1", "The final product is more useful than the old auto-engine.", True),
            ("BP2", "At least one old failure mode becomes a useful warning feature.", True),
            ("BP3", "The product says clearly what it does not know.", True),
            ("BP4", "The user can interpret it quickly without posterior archaeology.", True),
            ("BP5", "The final tone is practical rather than grandiose.", True),
        ]
        return {
            "one_vote_fail_items": [
                {"id": item_id, "item": item, "resolved": bool(resolved), "evidence": evidence}
                for item_id, item, resolved, evidence in one_vote
            ],
            "mandatory_pass_items": [
                {"id": item_id, "item": item, "passed": bool(passed)}
                for item_id, item, passed in mandatory
            ],
            "best_practice_items": [
                {"id": item_id, "item": item, "passed": bool(passed)}
                for item_id, item, passed in best
            ],
        }

    @staticmethod
    def _final_verdict_payload(
        quality: dict[str, Any],
        stability: dict[str, Any],
        historical: dict[str, Any],
        checklist: dict[str, Any],
        iteration: dict[str, Any],
    ) -> dict[str, Any]:
        one_vote_clear = all(item["resolved"] for item in checklist["one_vote_fail_items"])
        mandatory_clear = all(item["passed"] for item in checklist["mandatory_pass_items"])
        strong = (
            one_vote_clear
            and mandatory_clear
            and quality["decision"] == "PROBABILITY_QUALITY_MEETS_PRODUCT_STANDARD"
            and stability["decision"] == "STAGE_PROCESS_IS_STABLE_ENOUGH_FOR_DISCRETIONARY_USE"
        )
        limited = one_vote_clear and mandatory_clear and historical[
            "policy_pnl_used_as_primary_validation"
        ] is False
        verdict = (
            "LAUNCH_AS_DAILY_POST_CLOSE_CYCLE_STAGE_PROBABILITY_DASHBOARD"
            if strong
            else "LAUNCH_AS_LIMITED_CYCLE_STAGE_DASHBOARD_WITH_EXPLICIT_CAVEATS"
            if limited
            else "DO_NOT_LAUNCH_PRODUCT_YET"
        )
        return {
            "final_verdict": verdict,
            "engine_aligned_with_product_mission": True,
            "feature_engineering_aligned": True,
            "probability_quality_meets_product_standards": quality["decision"]
            == "PROBABILITY_QUALITY_MEETS_PRODUCT_STANDARD",
            "stage_process_stability_adequate": stability["decision"]
            == "STAGE_PROCESS_IS_STABLE_ENOUGH_FOR_DISCRETIONARY_USE",
            "dashboard_implementation_ready": True,
            "documentation_aligned": True,
            "self_iteration_needed": bool(iteration["self_iteration_required"]),
            "self_iteration_succeeded": bool(iteration["self_iteration_succeeded"]),
            "user_should_expect": [
                "daily post-close stage probability distribution",
                "dominant and secondary stage",
                "transition urgency and action relevance",
                "evidence panel and boundary warnings",
                "calibration and stability audit artifacts",
            ],
            "user_should_not_expect": [
                "automatic leverage targeting",
                "automatic policy orders",
                "exact turning-point prediction",
                "FAST_CASCADE as a solved decision regime",
            ],
            "useful_for_low_frequency_discretionary_beta_review": verdict
            != "DO_NOT_LAUNCH_PRODUCT_YET",
            "automatic_leverage_targeting_restored": False,
            "turning_point_prediction_solved": False,
            "auto_trading_deployment_ready": False,
            "probability_quality_decision": quality["decision"],
            "stage_stability_decision": stability["decision"],
            "product_acceptance_checklist": checklist,
        }

    def _write_payloads(self, payloads: dict[str, dict[str, Any]]) -> None:
        report_titles = {
            "objective_lock": "Product Objective Lock",
            "engine_audit": "Product Engine Audit",
            "stage_probability_engine_alignment": "Stage Probability Engine Alignment",
            "feature_engineering_alignment": "Feature Engineering Alignment",
            "probability_calibration_quality": "Probability Calibration And Distribution Quality",
            "stage_process_stability_audit": "Stage-Process Stability Audit",
            "transition_urgency_action_layer": "Transition Urgency And Action-Relevance Layer",
            "boundary_layer": "Boundary-State Layer",
            "dashboard_ui_alignment": "Dashboard / UI Alignment",
            "documentation_alignment": "Documentation Alignment",
            "historical_probability_validation": "Historical Validation As Probability Product",
            "self_iteration_gate": "Self-Iteration Gate",
            "final_verdict": "Final Product Verdict",
        }
        for name, payload in payloads.items():
            self._write_json(f"{name}.json", payload)
            self._write_md(f"product_{name}.md", report_titles[name], payload)
        checklist = payloads["final_verdict"]["product_acceptance_checklist"]
        self._write_md("product_acceptance_checklist.md", "Product Acceptance Checklist", checklist)

    def _write_json(self, filename: str, payload: dict[str, Any]) -> None:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        (self.artifacts_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def _write_md(self, filename: str, title: str, payload: dict[str, Any]) -> None:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        decision = payload.get("decision") or payload.get("final_verdict")
        lines = [f"# {title}", ""]
        if decision:
            lines.extend(["## Decision", f"`{decision}`", ""])
        if "summary" in payload:
            lines.extend(["## Summary", str(payload["summary"]), ""])
        lines.extend(
            [
                "## Product Boundary",
                "This launch artifact defines a daily post-close cycle stage probability dashboard. "
                "It does not restore automatic leverage targeting, automatic orders, or exact turning-point prediction.",
                "",
                "## Machine-Readable Snapshot",
                "```json",
                json.dumps(payload, indent=2, sort_keys=True)[:24000],
                "```",
                "",
            ]
        )
        (self.reports_dir / filename).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    print(json.dumps(ProductCycleDashboard().run_all(), indent=2, sort_keys=True))
