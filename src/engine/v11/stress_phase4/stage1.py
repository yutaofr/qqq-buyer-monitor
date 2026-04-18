from __future__ import annotations

import numpy as np
import pandas as pd

from src.engine.v11.stress_phase4.types import Phase4Stage1Output


class Phase4Stage1Model:
    """Interpretable regime-state layer for Phase 4 research."""

    def score_frame(self, frame: pd.DataFrame, state: pd.DataFrame) -> pd.DataFrame:
        drawdown = self._col(frame, "phase3_drawdown")
        transition = self._col(frame, "benchmark_transition_intensity")
        recovery = self._col(frame, "benchmark_recovery_impulse")
        rebound = self._col(frame, "benchmark_rebound_from_trough")
        bust_pressure = self._col(frame, "benchmark_bust_pressure")

        ordinary = ((-drawdown - 0.04) / 0.11).clip(0.0, 1.0) * (1.0 - state["vol_surface_panic"] * 0.35)
        structural_onset = (0.34 * transition + 0.26 * bust_pressure + 0.22 * state["credit_liquidity_stress"] + 0.18 * state["cross_sectional_stress"]).clip(0.0, 1.0)
        healing = (0.40 * recovery + 0.26 * rebound + 0.20 * self._col(frame, "benchmark_prob_RECOVERY") + 0.14 * self._col(frame, "benchmark_bullish_rsi_divergence")).clip(0.0, 1.0)
        onset = (0.55 * transition + 0.25 * state["cross_asset_divergence"] + 0.20 * state["cross_sectional_stress"]).clip(0.0, 1.0)
        ambiguity = (np.minimum(ordinary, structural_onset) + np.minimum(structural_onset, healing) + 0.5 * onset).clip(0.0, 1.0)
        normal = (1.0 - np.maximum.reduce([ordinary.to_numpy(), structural_onset.to_numpy(), onset.to_numpy()])).clip(0.0, 1.0)
        confidence = (1.0 - 0.65 * ambiguity).clip(0.10, 1.0)

        return pd.DataFrame(
            {
                "stage1_normal": normal,
                "stage1_ordinary_correction": ordinary.clip(0.0, 1.0),
                "stage1_transition_onset": onset,
                "stage1_structural_stress_onset": structural_onset,
                "stage1_recovery_healing": healing,
                "stage1_ambiguity": ambiguity,
                "stage1_transition_intensity": transition.clip(0.0, 1.0),
                "stage1_confidence": confidence,
            },
            index=frame.index,
        )

    def score_one(self, row: pd.Series, state_row: pd.Series) -> Phase4Stage1Output:
        frame = pd.DataFrame([row])
        state = pd.DataFrame([state_row])
        scored = self.score_frame(frame.reset_index(drop=True), state.reset_index(drop=True)).iloc[0]
        return Phase4Stage1Output(
            normal=float(scored["stage1_normal"]),
            ordinary_correction=float(scored["stage1_ordinary_correction"]),
            transition_onset=float(scored["stage1_transition_onset"]),
            structural_stress_onset=float(scored["stage1_structural_stress_onset"]),
            recovery_healing=float(scored["stage1_recovery_healing"]),
            ambiguity=float(scored["stage1_ambiguity"]),
            transition_intensity=float(scored["stage1_transition_intensity"]),
            confidence=float(scored["stage1_confidence"]),
        )

    @staticmethod
    def _col(frame: pd.DataFrame, name: str) -> pd.Series:
        return pd.to_numeric(frame[name], errors="coerce").fillna(0.0) if name in frame else pd.Series(0.0, index=frame.index)
