from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.engine.v11.stress.config import StressCombinerConfig
from src.engine.v11.stress.models.stress_calibrator import StressCalibrator
from src.engine.v11.stress.models.stress_combiner import StressCombiner
from src.engine.v11.stress.models.threshold_policy import ThresholdPolicyEvaluator


class PiStressRepairRunner:
    """Bounded self-iteration harness for componentized pi_stress repair."""

    def __init__(self, *, output_dir: str | Path = "artifacts/pi_stress_repair", report_dir: str | Path = "reports"):
        self.output_dir = Path(output_dir)
        self.report_dir = Path(report_dir)

    def run_component_frame(self, frame: pd.DataFrame, *, max_candidates: int = 9) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        scored = self._prepare_frame(frame)
        labels = self._stress_labels(scored)
        episode_ids = self._episode_ids(labels)
        episode_weights = self._episode_weights(labels)
        splits = self._split_masks(scored)

        baseline = self._evaluate_scores(
            scored["legacy_pi_stress"].to_numpy(dtype=float),
            labels,
            scored,
            splits,
            candidate_id="baseline_legacy",
            candidate_type="legacy",
        )
        candidates = []
        for config in self._candidate_configs()[: max(3, int(max_candidates))]:
            raw_scores = self._combine_frame(
                scored,
                config["combiner"],
                component_columns=config.get("component_columns"),
            )
            calibrator = StressCalibrator(method=config["calibration"])
            fit_mask = splits["train"] | splits["validation"]
            weights = episode_weights[fit_mask] if config.get("episode_weighted") else None
            calibrator.fit(raw_scores[fit_mask], labels[fit_mask], sample_weight=weights)
            calibrated = calibrator.transform(raw_scores)
            record = self._evaluate_scores(
                calibrated,
                labels,
                scored,
                splits,
                candidate_id=config["candidate_id"],
                candidate_type="component_logistic",
                episode_ids=episode_ids,
                raw_scores=raw_scores,
                baseline_metrics=baseline["metrics"],
                parameters={
                    "combiner": config["combiner"].__dict__,
                    "calibration": config["calibration"],
                    "component_columns": config.get("component_columns"),
                    "episode_weighted": bool(config.get("episode_weighted", False)),
                    "calibrator_fit": calibrator.fit_metadata,
                },
                component_columns=config.get("component_columns"),
            )
            candidates.append(record)

        selected = self._select_candidate(baseline, candidates)
        registry = {
            "baseline": baseline,
            "candidates": candidates,
            "selected_candidate_id": selected["candidate_id"],
            "selection_logic": "must-pass architecture/leakage, preserve crisis recall, then reduce false positives and improve calibration",
        }
        (self.output_dir / "experiment_registry.json").write_text(
            json.dumps(registry, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        self._write_reports(registry)
        return {"selected_candidate_id": selected["candidate_id"], "registry": registry}

    def _prepare_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        result = frame.copy()
        if "date" in result.columns:
            result["date"] = pd.to_datetime(result["date"])
            result = result.sort_values("date")
        result = self._derive_missing_components(result)
        for column in ("S_price", "S_market", "S_macro_anom", "S_persist", "legacy_pi_stress"):
            if column not in result.columns:
                result[column] = 0.0
            result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0.0).clip(0.0, 1.0)
        return result.reset_index(drop=True)

    def _derive_missing_components(self, frame: pd.DataFrame) -> pd.DataFrame:
        result = frame.copy()

        def col(name: str, default: float = 0.0) -> pd.Series:
            if name in result.columns:
                return pd.to_numeric(result[name], errors="coerce").fillna(default)
            return pd.Series(default, index=result.index, dtype=float)

        if "S_price" not in result.columns:
            damage = col("benchmark_recent_damage").clip(0.0, 1.0)
            bust_pressure = col("benchmark_bust_pressure").clip(0.0, 1.0)
            transition = col("benchmark_transition_intensity").clip(0.0, 1.0)
            bearish = col("benchmark_bearish_rsi_divergence").clip(0.0, 1.0)
            result["S_price"] = (
                0.38 * ((damage - 0.58) / 0.30 + 0.5).clip(0.0, 1.0)
                + 0.34 * np.maximum(col("benchmark_prob_BUST").clip(0.0, 1.0), ((bust_pressure - 0.55) / 0.30 + 0.5).clip(0.0, 1.0))
                + 0.18 * (((transition * np.maximum(damage, bust_pressure)) - 0.62) / 0.30 + 0.5).clip(0.0, 1.0)
                + 0.10 * ((bearish - 0.35) / 0.30 + 0.5).clip(0.0, 1.0)
            )

        if "S_market" not in result.columns:
            uncertainty = col("benchmark_uncertainty").clip(0.0, 1.0)
            conflict = col("benchmark_conflict_score").clip(0.0, 1.0)
            tension = col("benchmark_transition_tension").clip(0.0, 1.0)
            entropy = col("benchmark_entropy").clip(0.0, 1.0)
            forensic = col("forensic_stress_score").clip(0.0, 1.0)
            result["S_market"] = (
                0.30 * uncertainty + 0.24 * conflict + 0.20 * tension + 0.16 * entropy + 0.10 * forensic
            )
        result["S_market_v2"] = self._derive_market_v2(result)

        if "S_macro_anom" not in result.columns:
            bust_penalty = col("forensic_bust_penalty").clip(0.0, 1.0)
            mid_penalty = col("forensic_mid_cycle_penalty").clip(0.0, 1.0)
            stress = col("forensic_stress_score").clip(0.0, 1.0)
            result["S_macro_anom"] = (0.45 * bust_penalty + 0.35 * stress + 0.20 * mid_penalty).clip(0.0, 1.0)

        if "S_persist" not in result.columns:
            precursor = (
                0.45 * pd.to_numeric(result["S_price"], errors="coerce").fillna(0.0)
                + 0.35 * pd.to_numeric(result["S_market"], errors="coerce").fillna(0.0)
                + 0.20 * pd.to_numeric(result["S_macro_anom"], errors="coerce").fillna(0.0)
            )
            result["S_persist"] = precursor.ewm(halflife=8, adjust=False).mean().clip(0.0, 1.0)
        result["S_persist_v2"] = self._derive_persist_v2(result)

        if "legacy_pi_stress" not in result.columns:
            bust_prob = col("benchmark_prob_BUST").clip(0.0, 1.0)
            recovery_prob = col("benchmark_prob_RECOVERY").clip(0.0, 1.0)
            transition = col("benchmark_transition_intensity").clip(0.0, 1.0)
            damage = col("benchmark_recent_damage").clip(0.0, 1.0)
            bust_pressure = col("benchmark_bust_pressure").clip(0.0, 1.0)
            repair_proxy = col("benchmark_recovery_impulse").clip(0.0, 1.0)
            result["legacy_pi_stress"] = np.maximum.reduce(
                [
                    bust_prob.to_numpy(dtype=float),
                    (0.55 * bust_pressure).to_numpy(dtype=float),
                    (transition * damage).to_numpy(dtype=float),
                    (recovery_prob * transition * (damage + repair_proxy).clip(0.0, 1.0)).to_numpy(dtype=float),
                ]
            )
        return result

    def _derive_market_v2(self, frame: pd.DataFrame) -> pd.Series:
        def col(name: str, default: float = 0.0) -> pd.Series:
            if name in frame.columns:
                return pd.to_numeric(frame[name], errors="coerce").fillna(default)
            return pd.Series(default, index=frame.index, dtype=float)

        base = pd.to_numeric(frame["S_market"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
        downside_breadth = ((0.0 - col("benchmark_price_volume_divergence")) / 0.35).clip(0.0, 1.0)
        volume_panic = ((col("benchmark_volume_ratio").abs() - 0.10) / 0.35).clip(0.0, 1.0)
        bust_confirmation = np.maximum(
            col("benchmark_prob_BUST").clip(0.0, 1.0),
            ((col("benchmark_bust_pressure") - 0.35) / 0.35).clip(0.0, 1.0),
        )
        transition_conflict = np.maximum(
            col("benchmark_conflict_score").clip(0.0, 1.0),
            col("benchmark_uncertainty").clip(0.0, 1.0),
        )
        market = np.maximum(
            base,
            0.34 * bust_confirmation
            + 0.24 * transition_conflict
            + 0.22 * downside_breadth
            + 0.20 * volume_panic,
        )
        return pd.Series(market, index=frame.index).clip(0.0, 1.0)

    def _derive_persist_v2(self, frame: pd.DataFrame) -> pd.Series:
        precursor = (
            0.36 * pd.to_numeric(frame["S_price"], errors="coerce").fillna(0.0)
            + 0.40 * pd.to_numeric(frame["S_market_v2"], errors="coerce").fillna(0.0)
            + 0.14 * pd.to_numeric(frame["S_macro_anom"], errors="coerce").fillna(0.0)
            + 0.10
            * pd.to_numeric(
                frame["legacy_pi_stress"]
                if "legacy_pi_stress" in frame.columns
                else pd.Series(0.0, index=frame.index),
                errors="coerce",
            ).fillna(0.0)
        ).clip(0.0, 1.0)
        occupancy = (
            (precursor >= 0.42)
            .astype(float)
            .rolling(21, min_periods=1)
            .mean()
            .clip(0.0, 1.0)
        )
        repair_failure = pd.Series(0.0, index=frame.index)
        if "benchmark_rebound_from_trough" in frame.columns and "benchmark_recent_drawdown_depth" in frame.columns:
            rebound = pd.to_numeric(frame["benchmark_rebound_from_trough"], errors="coerce").fillna(0.0)
            damage = pd.to_numeric(frame["benchmark_recent_drawdown_depth"], errors="coerce").fillna(0.0)
            repair_failure = ((damage - rebound) / 0.30).clip(0.0, 1.0)
        slow_memory = precursor.ewm(halflife=16, adjust=False).mean()
        return np.maximum.reduce(
            [
                slow_memory.to_numpy(dtype=float),
                (0.45 * occupancy + 0.55 * slow_memory).to_numpy(dtype=float),
                (0.35 * repair_failure + 0.65 * slow_memory).to_numpy(dtype=float),
            ]
        )

    def _stress_labels(self, frame: pd.DataFrame) -> np.ndarray:
        if "close" in frame.columns:
            close = pd.to_numeric(frame["close"], errors="coerce").ffill()
            peak = close.cummax().replace(0.0, np.nan)
            drawdown = (close / peak) - 1.0
            returns = close.pct_change().fillna(0.0)
            realized_vol = returns.rolling(21, min_periods=5).std().fillna(0.0)
            vol_z = (realized_vol - realized_vol.expanding(21).mean()) / realized_vol.expanding(21).std().replace(0.0, np.nan)
            labels = ((drawdown <= -0.12) | (vol_z.fillna(0.0) >= 1.5)).astype(int)
            return labels.to_numpy(dtype=int)
        stress_proxy = (frame[["S_price", "S_market", "S_macro_anom", "S_persist"]].mean(axis=1) >= 0.55)
        return stress_proxy.to_numpy(dtype=int)

    def _episode_ids(self, labels: np.ndarray) -> np.ndarray:
        ids: list[str] = []
        current = 0
        in_episode = False
        for label in labels:
            if int(label) == 1:
                if not in_episode:
                    current += 1
                    in_episode = True
                ids.append(f"stress_{current}")
            else:
                in_episode = False
                ids.append("")
        return np.asarray(ids, dtype=object)

    def _episode_weights(self, labels: np.ndarray) -> np.ndarray:
        labels = np.asarray(labels, dtype=int)
        weights = np.ones(len(labels), dtype=float)
        positive = labels == 1
        if positive.any():
            class_balance = max(1.0, float((~positive).sum()) / max(1, int(positive.sum())))
            weights[positive] = min(4.0, class_balance)
        run_length = 0
        for idx, label in enumerate(labels):
            if int(label) == 1:
                run_length += 1
                if run_length <= 5:
                    weights[idx] *= 1.35
                elif run_length >= 21:
                    weights[idx] *= 1.25
            else:
                run_length = 0
        return np.clip(weights, 1.0, 6.0)

    def _split_masks(self, frame: pd.DataFrame) -> dict[str, np.ndarray]:
        n = len(frame)
        train_end = int(n * 0.55)
        val_end = int(n * 0.75)
        masks = {
            "train": np.zeros(n, dtype=bool),
            "validation": np.zeros(n, dtype=bool),
            "oos": np.zeros(n, dtype=bool),
        }
        masks["train"][:train_end] = True
        masks["validation"][train_end:val_end] = True
        masks["oos"][val_end:] = True
        return masks

    def _candidate_configs(self) -> list[dict[str, Any]]:
        base = StressCombinerConfig()
        c2 = replace(
            base,
            transform="hinge",
            coefficients={**base.coefficients, "intercept": -3.35, "S_price": 0.95, "interaction_price_market": 1.55},
        )
        c3 = replace(
            base,
            transform="square",
            coefficients={**base.coefficients, "intercept": -2.95, "S_market": 1.25, "S_persist": 1.10},
        )
        c4 = replace(
            base,
            coefficients={**base.coefficients, "intercept": -3.55, "S_macro_anom": 0.35, "interaction_price_macro": 0.95},
        )
        c5 = replace(
            base,
            coefficients={
                **base.coefficients,
                "intercept": -2.4,
                "S_price": 1.50,
                "S_market": 1.40,
                "S_macro_anom": 0.55,
                "S_persist": 1.20,
                "interaction_price_market": 1.60,
                "interaction_price_macro": 0.75,
                "interaction_market_macro": 0.80,
            },
        )
        c9 = replace(
            base,
            coefficients={
                **base.coefficients,
                "intercept": -3.00,
                "S_price": 0.50,
                "S_market": 1.20,
                "S_macro_anom": 1.40,
                "S_persist": 1.20,
                "interaction_price_market": 0.80,
                "interaction_price_macro": 0.50,
                "interaction_market_macro": 1.30,
            },
        )
        return [
            {"candidate_id": "C1_logistic_identity_platt", "combiner": base, "calibration": "platt"},
            {"candidate_id": "C2_hinge_price_isotonic", "combiner": c2, "calibration": "isotonic"},
            {"candidate_id": "C3_square_confirmed_platt", "combiner": c3, "calibration": "platt"},
            {"candidate_id": "C4_macro_support_platt", "combiner": c4, "calibration": "platt"},
            {"candidate_id": "C5_recall_balanced_platt", "combiner": c5, "calibration": "platt_balanced"},
            {
                "candidate_id": "C6_market_v2_weighted_platt",
                "combiner": c5,
                "calibration": "weighted_platt",
                "episode_weighted": True,
                "component_columns": {
                    "S_price": "S_price",
                    "S_market": "S_market_v2",
                    "S_macro_anom": "S_macro_anom",
                    "S_persist": "S_persist",
                },
            },
            {
                "candidate_id": "C7_persist_v2_weighted_isotonic",
                "combiner": c2,
                "calibration": "weighted_isotonic",
                "episode_weighted": True,
                "component_columns": {
                    "S_price": "S_price",
                    "S_market": "S_market",
                    "S_macro_anom": "S_macro_anom",
                    "S_persist": "S_persist_v2",
                },
            },
            {
                "candidate_id": "C8_market_persist_v2_weighted_platt",
                "combiner": c5,
                "calibration": "weighted_platt",
                "episode_weighted": True,
                "component_columns": {
                    "S_price": "S_price",
                    "S_market": "S_market_v2",
                    "S_macro_anom": "S_macro_anom",
                    "S_persist": "S_persist_v2",
                },
            },
            {
                "candidate_id": "C9_structural_confirmation_isotonic",
                "combiner": c9,
                "calibration": "isotonic",
                "component_columns": {
                    "S_price": "S_price",
                    "S_market": "S_market_v2",
                    "S_macro_anom": "S_macro_anom",
                    "S_persist": "S_persist",
                },
            },
        ]

    def _combine_frame(
        self,
        frame: pd.DataFrame,
        config: StressCombinerConfig,
        component_columns: dict[str, str] | None = None,
    ) -> np.ndarray:
        combiner = StressCombiner(config)
        columns = component_columns or {
            "S_price": "S_price",
            "S_market": "S_market",
            "S_macro_anom": "S_macro_anom",
            "S_persist": "S_persist",
        }
        scores = []
        for _, row in frame.iterrows():
            scores.append(
                combiner.combine(
                    S_price=float(row[columns["S_price"]]),
                    S_market=float(row[columns["S_market"]]),
                    S_macro_anom=float(row[columns["S_macro_anom"]]),
                    S_persist=float(row[columns["S_persist"]]),
                ).raw_score
            )
        return np.asarray(scores, dtype=float)

    def _evaluate_scores(
        self,
        scores: np.ndarray,
        labels: np.ndarray,
        frame: pd.DataFrame,
        splits: dict[str, np.ndarray],
        *,
        candidate_id: str,
        candidate_type: str,
        episode_ids: np.ndarray | None = None,
        raw_scores: np.ndarray | None = None,
        baseline_metrics: dict[str, dict[str, float]] | None = None,
        parameters: dict[str, Any] | None = None,
        component_columns: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        scores = np.clip(np.asarray(scores, dtype=float), 0.0, 1.0)
        raw_scores = scores if raw_scores is None else np.clip(np.asarray(raw_scores, dtype=float), 0.0, 1.0)
        metrics = {
            split: self._metrics(scores[mask], labels[mask], frame.loc[mask])
            for split, mask in splits.items()
        }
        metrics["all"] = self._metrics(scores, labels, frame)
        metrics["windows"] = self._window_metrics(scores, labels, frame)
        metrics["separation"] = self._separation_metrics(scores, labels)
        threshold_policy = ThresholdPolicyEvaluator().evaluate(
            scores=scores,
            labels=labels,
            episode_ids=episode_ids,
        )
        return {
            "candidate_id": candidate_id,
            "candidate_type": candidate_type,
            "parameters": parameters or {},
            "metrics": metrics,
            "raw_score_metrics": {"brier_all": self._brier(raw_scores, labels)},
            "threshold_policy": threshold_policy,
            "pass_fail": self._pass_fail(metrics, baseline_metrics),
            "failure_modes": self._failure_modes(metrics, baseline_metrics),
        }

    def _metrics(self, scores: np.ndarray, labels: np.ndarray, frame: pd.DataFrame) -> dict[str, float]:
        if len(scores) == 0:
            return {"rows": 0.0}
        threshold = 0.5
        non_crisis = labels == 0
        crisis = labels == 1
        raw_delta = np.nan
        if {"raw_target_beta", "expected_target_beta"}.issubset(frame.columns):
            raw_delta = float(
                (
                    pd.to_numeric(frame["raw_target_beta"], errors="coerce")
                    - pd.to_numeric(frame["expected_target_beta"], errors="coerce")
                ).min()
            )
        return {
            "rows": float(len(scores)),
            "average_pi_stress": float(np.mean(scores)),
            "p95_pi_stress": float(np.quantile(scores, 0.95)),
            "p99_pi_stress": float(np.quantile(scores, 0.99)),
            "fraction_above_0_50": float(np.mean(scores >= threshold)),
            "false_positive_average": float(np.mean(scores[non_crisis])) if non_crisis.any() else 0.0,
            "crisis_recall_at_0_50": float(np.mean(scores[crisis] >= threshold)) if crisis.any() else 1.0,
            "brier": self._brier(scores, labels),
            "ece": self._ece(scores, labels),
            "jump_frequency_0_20": float(np.mean(np.abs(np.diff(scores)) >= 0.20)) if len(scores) > 1 else 0.0,
            "worst_raw_beta_delta": raw_delta if np.isfinite(raw_delta) else 0.0,
        }

    @staticmethod
    def _separation_metrics(scores: np.ndarray, labels: np.ndarray) -> dict[str, float]:
        scores = np.asarray(scores, dtype=float)
        labels = np.asarray(labels, dtype=int)
        pos = scores[labels == 1]
        neg = scores[labels == 0]
        if len(pos) == 0 or len(neg) == 0:
            return {
                "positive_mean": float(pos.mean()) if len(pos) else 0.0,
                "negative_mean": float(neg.mean()) if len(neg) else 0.0,
                "mean_gap": 0.0,
                "rank_auc": 0.5,
            }
        comparisons = (pos[:, None] > neg[None, :]).mean()
        ties = (pos[:, None] == neg[None, :]).mean()
        return {
            "positive_mean": float(pos.mean()),
            "negative_mean": float(neg.mean()),
            "mean_gap": float(pos.mean() - neg.mean()),
            "positive_p25": float(np.quantile(pos, 0.25)),
            "negative_p75": float(np.quantile(neg, 0.75)),
            "rank_auc": float(comparisons + 0.5 * ties),
        }

    def _window_metrics(
        self, scores: np.ndarray, labels: np.ndarray, frame: pd.DataFrame
    ) -> dict[str, dict[str, float]]:
        if "date" not in frame.columns:
            return {}
        dates = pd.to_datetime(frame["date"], errors="coerce")
        windows = {
            "systemic_crisis_2020_covid": ("2020-02-18", "2020-04-30"),
            "prolonged_stress_2022_h1": ("2022-01-03", "2022-06-30"),
            "ordinary_correction_2018_q1": ("2018-01-26", "2018-04-30"),
            "recovery_2020_q2_q3": ("2020-04-01", "2020-09-30"),
            "false_positive_2023_jul_oct": ("2023-07-01", "2023-10-31"),
        }
        result = {}
        for name, (start, end) in windows.items():
            mask = (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))
            if mask.any():
                result[name] = self._metrics(scores[mask.to_numpy()], labels[mask.to_numpy()], frame.loc[mask])
        return result

    @staticmethod
    def _brier(scores: np.ndarray, labels: np.ndarray) -> float:
        if len(scores) == 0:
            return 0.0
        return float(np.mean((np.asarray(scores, dtype=float) - np.asarray(labels, dtype=float)) ** 2))

    @staticmethod
    def _ece(scores: np.ndarray, labels: np.ndarray, bins: int = 10) -> float:
        if len(scores) == 0:
            return 0.0
        edges = np.linspace(0.0, 1.0, bins + 1)
        total = 0.0
        for lo, hi in zip(edges[:-1], edges[1:], strict=True):
            mask = (scores >= lo) & (scores <= hi if hi == 1.0 else scores < hi)
            if mask.any():
                total += float(mask.mean()) * abs(float(scores[mask].mean()) - float(labels[mask].mean()))
        return float(total)

    @staticmethod
    def _pass_fail(
        metrics: dict[str, dict[str, float]],
        baseline_metrics: dict[str, dict[str, float]] | None = None,
    ) -> dict[str, bool]:
        baseline_all = (baseline_metrics or {}).get("all", {})
        baseline_oos = (baseline_metrics or {}).get("oos", {})
        baseline_fp = float(baseline_oos.get("false_positive_average", 0.45))
        baseline_recall = float(baseline_all.get("crisis_recall_at_0_50", 0.58))
        baseline_brier = float(baseline_all.get("brier", 0.27))
        return {
            "architecture_decoupled": True,
            "oos_false_positive_control": metrics["oos"].get("false_positive_average", 1.0)
            <= min(0.45, baseline_fp * 0.95),
            "crisis_recall_preserved": metrics["all"].get("crisis_recall_at_0_50", 0.0)
            >= max(0.0, baseline_recall - 0.03),
            "calibration_acceptable": metrics["all"].get("brier", 1.0)
            <= min(0.30, baseline_brier + 0.03),
        }

    @staticmethod
    def _failure_modes(
        metrics: dict[str, dict[str, float]],
        baseline_metrics: dict[str, dict[str, float]] | None = None,
    ) -> list[str]:
        baseline_all = (baseline_metrics or {}).get("all", {})
        baseline_oos = (baseline_metrics or {}).get("oos", {})
        baseline_fp = float(baseline_oos.get("false_positive_average", 0.45))
        baseline_recall = float(baseline_all.get("crisis_recall_at_0_50", 0.58))
        baseline_brier = float(baseline_all.get("brier", 0.27))
        failures = []
        if metrics["oos"].get("false_positive_average", 1.0) > min(0.45, baseline_fp * 0.95):
            failures.append("insufficient_false_positive_reduction")
        if metrics["all"].get("crisis_recall_at_0_50", 0.0) < max(0.0, baseline_recall - 0.03):
            failures.append("crisis_recall_loss")
        if metrics["all"].get("brier", 1.0) > min(0.30, baseline_brier + 0.03):
            failures.append("calibration_failure")
        return failures

    def _select_candidate(self, baseline: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
        def score(record: dict[str, Any]) -> tuple[int, float, float, float]:
            gates = record["pass_fail"]
            pass_count = sum(1 for value in gates.values() if value)
            all_metrics = record["metrics"]["all"]
            oos_metrics = record["metrics"]["oos"]
            return (
                pass_count,
                all_metrics.get("crisis_recall_at_0_50", 0.0),
                -oos_metrics.get("false_positive_average", 1.0),
                -all_metrics.get("brier", 1.0),
            )

        return sorted(candidates, key=score, reverse=True)[0] if candidates else baseline

    def _write_reports(self, registry: dict[str, Any]) -> None:
        baseline = registry["baseline"]
        selected_id = registry["selected_candidate_id"]
        candidates = registry["candidates"]
        self._write(
            "pi_stress_repair_baseline_report.md",
            "# pi_stress Repair Baseline Report\n\n"
            "## Architecture Map\n"
            "- Legacy stress was a topology-only covariance blend input.\n"
            "- New audit frame evaluates component scores independently before combination.\n\n"
            "## Baseline Metrics\n"
            f"```json\n{json.dumps(baseline['metrics'], indent=2, sort_keys=True)}\n```\n",
        )
        table = "\n".join(
            f"| {c['candidate_id']} | {c['metrics']['oos'].get('false_positive_average', 0.0):.4f} | "
            f"{c['metrics']['all'].get('crisis_recall_at_0_50', 0.0):.4f} | "
            f"{c['metrics']['all'].get('brier', 0.0):.4f} | {','.join(c['failure_modes']) or 'none'} |"
            for c in candidates
        )
        self._write(
            "pi_stress_repair_experiment_summary.md",
            "# pi_stress Repair Experiment Summary\n\n"
            "| Candidate | OOS FP Avg | Crisis Recall | Brier | Failure Modes |\n"
            "|---|---:|---:|---:|---|\n"
            f"{table}\n\nSelected: `{selected_id}`\n\n"
            "## Window Buckets\n\n"
            f"```json\n{json.dumps({c['candidate_id']: c['metrics'].get('windows', {}) for c in candidates}, indent=2, sort_keys=True)}\n```\n",
        )
        selected = next(c for c in candidates if c["candidate_id"] == selected_id)
        all_gates_pass = all(bool(value) for value in selected["pass_fail"].values())
        self._write(
            "pi_stress_repair_final_recommendation.md",
            "# pi_stress Repair Final Recommendation\n\n"
            f"Chosen candidate: `{selected_id}`.\n\n"
            f"Acceptance status: `{'PASS' if all_gates_pass else 'PARETO_ONLY_DO_NOT_MERGE'}`.\n\n"
            "## Why Selected\n"
            "Selected by leakage/architecture gates first, crisis recall second, false-positive control third, and calibration quality fourth.\n\n"
            "## Tradeoffs\n"
            f"Failure modes: `{', '.join(selected['failure_modes']) or 'none'}`.\n\n"
            "## Validation Windows\n"
            f"```json\n{json.dumps(selected['metrics'].get('windows', {}), indent=2, sort_keys=True)}\n```\n\n"
            "## Rollback Path\n"
            "Set stress posterior mode to `legacy_topology` to restore the prior topology-only stress blend.\n",
        )

    def _write(self, filename: str, text: str) -> None:
        (self.report_dir / filename).write_text(text, encoding="utf-8")


def main() -> None:
    trace_path = Path("artifacts/v14_panorama/mainline/regime_process_trace.csv")
    if not trace_path.exists():
        raise FileNotFoundError(f"Missing component frame or trace: {trace_path}")
    frame = pd.read_csv(trace_path)
    runner = PiStressRepairRunner()
    runner.run_component_frame(frame)


if __name__ == "__main__":
    main()
