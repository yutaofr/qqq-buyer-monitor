"""Regime Volatility Floor — Level Detector for Crisis Depth.

Physical motivation
-------------------
BOCPD is a first-order detector: it fires when the *current* regime is
structurally inconsistent with the *previous* one (∂regime/∂t).  Once the
engine has accepted the crisis as the new regime, P_cp collapses to near-zero
even though the market is still in free-fall.

This module implements a complementary *zero-order* guard: it measures the
absolute level of predicted spread variance (σ²_spread from the NIG posterior)
and prevents leverage from recovering while that variance remains historically
elevated.

Design principles
-----------------
- **Causal**: uses only observations *already seen* (rolling window, no lookahead).
- **Orthogonal**: does NOT feed back into P_cp or AEMA — purely additive cap.
- **Conservative**: asymmetrically slow to release (floor_alpha_down ≪ up).
- **Fail-closed**: while the warm-up buffer is too short, the cap is 1.0 (permissive),
  matching existing burn-in conventions.

SRD reference: Architecture extension after Story 6.2 (Forgetting Factor).
"""

from __future__ import annotations

from collections import deque
import base64
import io

import numpy as np


class RegimeVolatilityFloor:
    """Rolling-quantile volatility guard on predictive spread variance.

    Tracks a rolling window of NIG σ²_spread observations.  When the current
    value exceeds the configured quantile of the window, the maximum allowed
    leverage is capped at ``stress_max_leverage``.

    The cap is also smoothed asymmetrically so it does not snap off instantly
    after a single quiet day: it decays via a slow EMA (``floor_alpha_down``).

    Args:
        window:              Look-back length in trading days.  Default 252.
        quantile:            Threshold percentile (0-1).  Default 0.95.
        stress_max_leverage: Maximum l_target when in stress zone.  Default 0.5.
        min_obs:             Minimum buffer length before any cap is applied.
                             Set equal to burn_in inside the runner.  Default 63.
        floor_alpha_down:    EMA decay for the smoothed cap (slow release).
                             ~0.02 → half-life ≈ 34 trading days.

    Usage::
        guard = RegimeVolatilityFloor(window=252, quantile=0.95)
        cap = guard.update(sigma2_spread)      # call once per bar
        l_target = min(l_target_from_aema, cap)
    """

    def __init__(
        self,
        window:              int   = 252,
        quantile:            float = 0.95,
        stress_max_leverage: float = 0.50,
        min_obs:             int   = 63,
        floor_alpha_down:    float = 0.02,
        abs_floor_variance:  float = 0.0,
        calm_max_leverage:   float = 2.0,
    ) -> None:
        if not (0.0 < quantile < 1.0):
            raise ValueError("quantile must be in (0, 1).")
        if not (0.0 <= stress_max_leverage <= 1.0):
            raise ValueError("stress_max_leverage must be in [0, 1].")
        if not (0.0 < floor_alpha_down <= 1.0):
            raise ValueError("floor_alpha_down must be in (0, 1].")
        if abs_floor_variance < 0.0:
            raise ValueError("abs_floor_variance must be non-negative.")

        self._buf              = deque(maxlen=window)
        self._quantile         = quantile
        self._stress_max_lev   = stress_max_leverage
        self._min_obs          = min_obs
        self._floor_alpha_down = floor_alpha_down
        self._abs_floor_variance = abs_floor_variance
        self._calm_max_lev     = calm_max_leverage

        # Smoothed cap value (starts permissive)
        self._smoothed_cap: float = self._calm_max_lev
        # Raw (unsmoothed) cap at the last call
        self._raw_cap: float = self._calm_max_lev
        # Last threshold value
        self._threshold: float = float("inf")

    # ── Public API ────────────────────────────────────────────────────────

    def update(self, sigma2: float) -> float:
        """Absorb one observation and return the current leverage cap ∈ [0, 1].

        The returned cap must be applied as::

            l_target_guarded = min(l_target, cap)

        Args:
            sigma2: NIG predictive variance for the spread dimension.

        Returns:
            A leverage cap in [``stress_max_leverage``, ``calm_max_leverage``].
        """
        self._buf.append(float(sigma2))

        # Not enough data yet → permissive
        if len(self._buf) < self._min_obs:
            self._raw_cap   = self._calm_max_lev
            self._threshold = float("inf")
        else:
            self._threshold = max(
                float(np.quantile(list(self._buf), self._quantile)),
                self._abs_floor_variance
            )
            self._raw_cap   = (
                self._stress_max_lev if sigma2 > self._threshold else self._calm_max_lev
            )

        # Asymmetric smoothing: snap tight immediately, release slowly
        if self._raw_cap < self._smoothed_cap:
            # New stress → jump directly to raw cap (fast)
            self._smoothed_cap = self._raw_cap
        else:
            # Recovering → EMA with slow alpha
            self._smoothed_cap = (
                self._floor_alpha_down * self._raw_cap
                + (1.0 - self._floor_alpha_down) * self._smoothed_cap
            )

        # Never go above calm_max_leverage
        self._smoothed_cap = min(self._smoothed_cap, self._calm_max_lev)
        return self._smoothed_cap

    def dump_state(self) -> dict:
        buf = io.BytesIO()
        np.savez_compressed(buf, buf_arr=np.array(self._buf, dtype=np.float64) if len(self._buf) > 0 else np.empty(0))
        return {
            "b64_buf": base64.b64encode(buf.getvalue()).decode("utf-8"),
            "smoothed_cap": self._smoothed_cap,
            "raw_cap": self._raw_cap,
            "threshold": self._threshold,
        }
        
    def load_state(self, state_dict: dict) -> None:
        self._smoothed_cap = state_dict["smoothed_cap"]
        self._raw_cap = state_dict["raw_cap"]
        self._threshold = state_dict["threshold"]
        buf = io.BytesIO(base64.b64decode(state_dict["b64_buf"]))
        with np.load(buf, allow_pickle=False) as data:
            self._buf.clear()
            if len(data["buf_arr"]) > 0:
                self._buf.extend(data["buf_arr"].tolist())

    @property
    def is_active(self) -> bool:
        """True when the guard is currently capping leverage."""
        return self._smoothed_cap < 1.0

    @property
    def current_cap(self) -> float:
        """Current smoothed leverage cap (last value returned by update())."""
        return self._smoothed_cap

    @property
    def threshold(self) -> float:
        """Last computed σ²_spread percentile threshold."""
        return self._threshold

    @property
    def buffer_size(self) -> int:
        """Number of observations currently in the rolling window."""
        return len(self._buf)
