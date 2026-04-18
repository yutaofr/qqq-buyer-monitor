from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class DeploymentPolicySpec:
    """Governed operating policy for converting pi_stress posterior into triggers."""

    mode: str
    primary_threshold: float
    warning_threshold: float | None = None
    conservative_threshold: float | None = None
    escalation_threshold: float | None = None
    hysteresis: dict[str, float] = field(default_factory=dict)
    fallback_mode: str = "legacy_fixed_0_50"
    monitoring_hooks: tuple[str, ...] = (
        "posterior_drift",
        "threshold_trigger_drift",
        "calibration_drift",
        "data_drift",
        "downstream_beta_pathology",
    )

    @staticmethod
    def supported_modes() -> tuple[str, ...]:
        return (
            "legacy_fixed_0_50",
            "calibrated_fixed_threshold",
            "threshold_policy_with_hysteresis",
        )

    @classmethod
    def legacy_fixed_0_50(cls) -> "DeploymentPolicySpec":
        return cls(
            mode="legacy_fixed_0_50",
            primary_threshold=0.50,
            warning_threshold=0.45,
            conservative_threshold=0.50,
            escalation_threshold=0.65,
            hysteresis={},
            fallback_mode="legacy_fixed_0_50",
        )

    @classmethod
    def calibrated_fixed_threshold(
        cls,
        *,
        threshold: float = 0.35,
    ) -> "DeploymentPolicySpec":
        return cls(
            mode="calibrated_fixed_threshold",
            primary_threshold=float(threshold),
            warning_threshold=max(0.0, float(threshold) - 0.05),
            conservative_threshold=float(threshold),
            escalation_threshold=min(1.0, float(threshold) + 0.25),
            hysteresis={},
            fallback_mode="legacy_fixed_0_50",
        )

    @classmethod
    def threshold_policy_with_hysteresis(cls) -> "DeploymentPolicySpec":
        return cls(
            mode="threshold_policy_with_hysteresis",
            primary_threshold=0.25,
            warning_threshold=0.20,
            conservative_threshold=0.35,
            escalation_threshold=0.50,
            hysteresis={
                "enter_after_days": 2,
                "exit_below_threshold": 0.20,
                "exit_after_days": 3,
                "minimum_episode_days": 2,
            },
            fallback_mode="legacy_fixed_0_50",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "primary_threshold": float(self.primary_threshold),
            "warning_threshold": None
            if self.warning_threshold is None
            else float(self.warning_threshold),
            "conservative_threshold": None
            if self.conservative_threshold is None
            else float(self.conservative_threshold),
            "escalation_threshold": None
            if self.escalation_threshold is None
            else float(self.escalation_threshold),
            "hysteresis": dict(self.hysteresis),
            "fallback_mode": self.fallback_mode,
            "monitoring_hooks": list(self.monitoring_hooks),
        }


class ThresholdPolicyEvaluator:
    """Evaluate operating thresholds separately from posterior estimation."""

    def __init__(self, thresholds: list[float] | tuple[float, ...] | None = None):
        self.thresholds = list(thresholds) if thresholds is not None else [
            0.20,
            0.25,
            0.30,
            0.35,
            0.40,
            0.45,
            0.50,
            0.55,
            0.60,
            0.65,
            0.70,
        ]

    def evaluate(self, *, scores, labels, episode_ids=None) -> dict[str, object]:
        score_arr = np.clip(np.asarray(scores, dtype=float).reshape(-1), 0.0, 1.0)
        label_arr = np.asarray(labels, dtype=int).reshape(-1)
        if len(score_arr) != len(label_arr):
            raise ValueError("scores and labels must have the same length")
        if episode_ids is None:
            episode_arr = np.asarray([f"row_{i}" if label else "" for i, label in enumerate(label_arr)])
        else:
            episode_arr = np.asarray(episode_ids).reshape(-1)

        curve = [
            self._threshold_metrics(score_arr, label_arr, episode_arr, float(threshold))
            for threshold in self.thresholds
        ]
        recommended = self._select_threshold(curve)
        return {
            "recommended_threshold": float(recommended["threshold"]) if recommended else 0.5,
            "recommended_operating_point": recommended or {},
            "threshold_curve": curve,
        }

    @staticmethod
    def _threshold_metrics(
        scores: np.ndarray,
        labels: np.ndarray,
        episode_ids: np.ndarray,
        threshold: float,
    ) -> dict[str, float]:
        predicted = scores >= threshold
        positives = labels == 1
        negatives = ~positives
        tp = float(np.sum(predicted & positives))
        fp = float(np.sum(predicted & negatives))
        fn = float(np.sum((~predicted) & positives))
        tn = float(np.sum((~predicted) & negatives))
        precision = tp / max(1.0, tp + fp)
        recall = tp / max(1.0, tp + fn)
        f1 = (2.0 * precision * recall) / max(1e-12, precision + recall)
        false_positive_rate = fp / max(1.0, fp + tn)
        positive_episode_ids = {
            str(eid)
            for eid, label in zip(episode_ids, labels, strict=True)
            if int(label) == 1 and str(eid)
        }
        captured_episode_ids = {
            str(eid)
            for eid, label, pred in zip(episode_ids, labels, predicted, strict=True)
            if int(label) == 1 and bool(pred) and str(eid)
        }
        episode_capture_rate = len(captured_episode_ids) / max(1, len(positive_episode_ids))
        return {
            "threshold": float(threshold),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "false_positive_rate": float(false_positive_rate),
            "episode_capture_rate": float(episode_capture_rate),
            "predicted_positive_rate": float(np.mean(predicted)) if len(predicted) else 0.0,
        }

    @staticmethod
    def _select_threshold(curve: list[dict[str, float]]) -> dict[str, float] | None:
        eligible = [
            row
            for row in curve
            if row["recall"] >= 0.60 and row["episode_capture_rate"] >= 0.70
        ]
        pool = eligible or curve
        if not pool:
            return None
        return sorted(
            pool,
            key=lambda row: (
                row["f1"],
                row["episode_capture_rate"],
                -row["false_positive_rate"],
            ),
            reverse=True,
        )[0]
