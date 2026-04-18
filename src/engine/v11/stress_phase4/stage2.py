from __future__ import annotations

import numpy as np
import pandas as pd

from src.engine.v11.stress_phase4.types import Phase4Stage2Output


class Phase4Stage2Model:
    """Conditional severity layer that consumes Stage 1 state outputs."""

    def score_frame(self, frame: pd.DataFrame, state: pd.DataFrame, stage1: pd.DataFrame) -> pd.DataFrame:
        fast_crash = ((-self._col(frame, "phase3_return_5d") - 0.04) / 0.14).clip(0.0, 1.0)
        drawdown = self._col(frame, "phase3_drawdown")
        slow_damage = ((-drawdown - 0.08) / 0.22).clip(0.0, 1.0).ewm(halflife=10, adjust=False).mean()
        repair_failure = ((self._col(frame, "benchmark_recent_drawdown_depth") - self._col(frame, "benchmark_rebound_from_trough")) / 0.28).clip(0.0, 1.0)
        healing_relief = (0.42 * stage1["stage1_recovery_healing"] + 0.25 * self._col(frame, "benchmark_prob_RECOVERY")).clip(0.0, 1.0)

        structural = (
            0.26 * stage1["stage1_structural_stress_onset"]
            + 0.20 * slow_damage
            + 0.18 * repair_failure
            + 0.16 * state["credit_liquidity_stress"]
            + 0.12 * state["cross_sectional_stress"]
            + 0.08 * state["cross_asset_divergence"]
            - 0.20 * healing_relief
        ).clip(0.0, 1.0)
        crisis = (
            0.34 * fast_crash
            + 0.25 * state["vol_surface_panic"]
            + 0.18 * state["cross_sectional_stress"]
            + 0.13 * self._col(frame, "benchmark_uncertainty")
            + 0.10 * stage1["stage1_transition_onset"]
            - 0.12 * healing_relief
        ).clip(0.0, 1.0)
        non_crisis = (stage1["stage1_ordinary_correction"] * (1.0 - 0.45 * state["credit_liquidity_stress"]) * (1.0 - 0.35 * state["vol_surface_panic"])).clip(0.0, 1.0)
        severity = np.maximum(crisis, structural * (0.70 + 0.30 * stage1["stage1_confidence"])).clip(0.0, 1.0)
        return pd.DataFrame(
            {
                "stage2_non_crisis_anomaly": non_crisis,
                "stage2_elevated_structural_stress": structural,
                "stage2_systemic_crisis": crisis,
                "phase4_severity_score": severity,
                "stage2_confidence": (stage1["stage1_confidence"] * (1.0 - 0.25 * stage1["stage1_ambiguity"])).clip(0.10, 1.0),
            },
            index=frame.index,
        )

    def score_one(self, row: pd.Series, state_row: pd.Series, stage1_row: pd.Series) -> Phase4Stage2Output:
        frame = pd.DataFrame([row])
        state = pd.DataFrame([state_row])
        stage1 = pd.DataFrame([stage1_row])
        scored = self.score_frame(frame.reset_index(drop=True), state.reset_index(drop=True), stage1.reset_index(drop=True)).iloc[0]
        return Phase4Stage2Output(
            non_crisis_anomaly=float(scored["stage2_non_crisis_anomaly"]),
            elevated_structural_stress=float(scored["stage2_elevated_structural_stress"]),
            systemic_crisis=float(scored["stage2_systemic_crisis"]),
            severity_score=float(scored["phase4_severity_score"]),
            confidence=float(scored["stage2_confidence"]),
        )

    @staticmethod
    def _col(frame: pd.DataFrame, name: str) -> pd.Series:
        return pd.to_numeric(frame[name], errors="coerce").fillna(0.0) if name in frame else pd.Series(0.0, index=frame.index)
