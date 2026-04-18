from __future__ import annotations

import numpy as np
import pandas as pd


class Phase4HierarchicalChallenger:
    """Formal Phase 4 hierarchical stress-posterior challenger."""

    def score_frame(self, frame: pd.DataFrame, state: pd.DataFrame, stage1: pd.DataFrame) -> pd.DataFrame:
        fast_crash = ((-self._col(frame, "phase3_return_5d") - 0.04) / 0.14).clip(0.0, 1.0)
        drawdown = self._col(frame, "phase3_drawdown")
        slow_damage = ((-drawdown - 0.08) / 0.22).clip(0.0, 1.0).ewm(halflife=10, adjust=False).mean()
        gate = (
            0.28 * state["cross_sectional_stress"]
            + 0.24 * state["credit_liquidity_stress"]
            + 0.20 * stage1["stage1_structural_stress_onset"]
            + 0.16 * state["cross_asset_divergence"]
            + 0.12 * stage1["stage1_transition_onset"]
        ).clip(0.0, 1.0)
        structural_expert = (0.38 * slow_damage + 0.24 * state["credit_liquidity_stress"] + 0.22 * gate + 0.16 * self._col(frame, "benchmark_bust_pressure")).clip(0.0, 1.0)
        crisis_expert = (0.44 * fast_crash + 0.30 * state["vol_surface_panic"] + 0.26 * state["cross_sectional_stress"]).clip(0.0, 1.0)
        healing_discount = (0.25 * stage1["stage1_recovery_healing"] + 0.10 * self._col(frame, "benchmark_prob_RECOVERY")).clip(0.0, 0.35)
        score = (gate * np.maximum(structural_expert, crisis_expert) * (1.0 - healing_discount)).clip(0.0, 1.0)
        return pd.DataFrame(
            {
                "hierarchical_gate": gate,
                "hierarchical_structural_expert": structural_expert,
                "hierarchical_crisis_expert": crisis_expert,
                "phase4_hierarchical_score": score,
            },
            index=frame.index,
        )

    @staticmethod
    def _col(frame: pd.DataFrame, name: str) -> pd.Series:
        return pd.to_numeric(frame[name], errors="coerce").fillna(0.0) if name in frame else pd.Series(0.0, index=frame.index)
