"""BOCPD engine core: five-step online changepoint detection loop.

SRD v1.2 Chapter 8: Bayesian Online Changepoint Detection with NIG conjugate
priors and macro-economic hazard rate modulation.

Architecture:
    BOCPDState   — immutable snapshot of engine state at time t
    BOCPDEngine  — stateful wrapper; one instance per backtest segment

Memory layout:
    run_length_probs  (505,)    — P(r_t = r | x_{1:t})
    suff_stats        (505, 3, 4) — NIG parameters [mu, kappa, alpha, beta]
                                   per (run-length, dimension)

Five-step update loop (SRD 8.2):
    1. Predictive log-density  — exp(logpdf(suff_stats, x_t)) → pred (505,)
    2. Hazard vector           — compute_hazard(g_r, lambda_macro) → h (505,)
    3. Posterior mass:
         new_probs[0]  = sum(probs * h * pred)          ← changepoint mass
         new_probs[r]  = probs[r-1] * (1-h[r-1]) * pred[r-1]  ← growth
    4. Normalize               — new_probs /= sum(new_probs)
    5. NIG shift + update (SRD 8.4):
         new_stats[0]    = prior          ← fresh regime, always
         new_stats[1:]   = update(old_stats[:-1], x_t)  ← right-shift + absorb
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.liquidity.engine.hazard import compute_hazard, precompute_g_r
from src.liquidity.engine.nig import predictive_logpdf, update_nig


@dataclass
class BOCPDState:
    """Immutable snapshot of engine state at time t.

    Attributes:
        run_length_probs: (R_MAX+1,) posterior over run lengths.
        suff_stats: (R_MAX+1, D, 4) NIG sufficient statistics indexed by
                    [run_length, dimension, {mu, kappa, alpha, beta}].
        t: number of update steps completed.
    """

    run_length_probs: np.ndarray   # (R_MAX+1,)
    suff_stats: np.ndarray         # (R_MAX+1, D, 4)
    t: int


class BOCPDEngine:
    """Online Bayesian changepoint detector with NIG conjugate priors.

    One instance per backtest segment. Segments must NOT share state
    (SRD 7.1). Construct a new instance for each structural segment.

    Args:
        config: parameter dict loaded from bocpd_params.json.
    """

    _D = 3   # observation dimension: [ED_ACCEL, SPREAD_ANOMALY, FISHER_RHO]

    def __init__(self, config: dict) -> None:
        self._config = config
        h_cfg = config["hazard"]
        self._r_max: int = h_cfg["R_MAX"]          # 504
        self._r_stable: int = h_cfg["R_STABLE"]    # 63
        self._kappa_hz: int = h_cfg["KAPPA_HAZARD"]  # 5

        # Precompute time-invariant g(r) vector once at init
        self._g_r: np.ndarray = precompute_g_r(
            r_max=self._r_max,
            r_stable=self._r_stable,
            kappa=self._kappa_hz,
        )

        # Build (D, 4) prior matrix from config
        self._prior: np.ndarray = self._build_prior()

        # Initialise state
        self._probs, self._stats, self._t = self._initial_state()

    # ─────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────

    def update(self, x_t: np.ndarray, lambda_macro: float) -> float:
        """Run one step of the five-step BOCPD loop.

        Args:
            x_t: shape (D,) observation vector at time t.
            lambda_macro: scalar macro hazard rate for this step.

        Returns:
            p_cp_raw: float in [0, 1] — raw changepoint probability.
        """
        # Step 1: predictive log-density → convert to linear scale
        log_pred = predictive_logpdf(self._stats, x_t)    # (N,)
        # Numerically stable exponentiation: subtract max before exp
        log_pred_stable = log_pred - log_pred.max()
        pred = np.exp(log_pred_stable)                     # (N,) in (0, 1]

        # Step 2: hazard vector for this macro environment
        h = compute_hazard(self._g_r, lambda_macro, r_max=self._r_max)  # (N,)

        # Step 3: posterior mass update
        new_probs = np.empty_like(self._probs)
        # Changepoint mass: all current run-lengths contribute to r=0
        new_probs[0] = np.sum(self._probs * h * pred)
        # Growth mass: run-lengths shift right by 1 (no changepoint happened)
        new_probs[1:] = self._probs[:-1] * (1.0 - h[:-1]) * pred[:-1]

        # Step 4: normalize (guard against numerical underflow → uniform fallback)
        total = new_probs.sum()
        if total > 0.0:
            new_probs /= total
        else:
            # Underflow recovery: reset to prior (uniform over short r)
            new_probs[:] = 0.0
            new_probs[0] = 1.0

        # Step 5: NIG shift + update (SRD 8.4 — off-by-one protection)
        new_stats = np.empty_like(self._stats)
        # r=0: always fresh prior (brand-new regime hypothesis)
        new_stats[0, :, :] = self._prior                        # INV-4
        # r=1..R_MAX: absorb x_t into the previous (r-1) stats (right-shift)
        new_stats[1:, :, :] = update_nig(self._stats[:-1, :, :], x_t)

        # Commit new state
        self._probs = new_probs
        self._stats = new_stats
        self._t += 1

        return float(new_probs[0])  # p_cp_raw

    def get_state(self) -> BOCPDState:
        """Return a deep-copy snapshot of the current engine state."""
        return BOCPDState(
            run_length_probs=self._probs.copy(),
            suff_stats=self._stats.copy(),
            t=self._t,
        )

    def set_state(self, state: BOCPDState) -> None:
        """Restore engine state from a snapshot (for segment replay)."""
        self._probs = state.run_length_probs.copy()
        self._stats = state.suff_stats.copy()
        self._t = state.t

    # ─────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────

    def _build_prior(self) -> np.ndarray:
        """Build the (D, 4) prior matrix from config.

        Layout: each row = [mu_0, kappa_0, alpha_0, beta_0] for one dimension.
        """
        priors = self._config["nig_priors"]
        dim_keys = ["ed_accel", "spread_anomaly", "fisher_rho"]
        prior = np.array([
            [priors[k]["mu_0"], priors[k]["kappa_0"],
             priors[k]["alpha_0"], priors[k]["beta_0"]]
            for k in dim_keys
        ], dtype=np.float64)    # (D, 4)
        return prior

    def _initial_state(self) -> tuple[np.ndarray, np.ndarray, int]:
        """Construct fresh initial state: all mass at r=0, all rows = prior."""
        n = self._r_max + 1  # 505

        probs = np.zeros(n, dtype=np.float64)
        probs[0] = 1.0       # 100% mass at run-length 0

        # Broadcast prior (D, 4) → (N, D, 4) by tiling over run-length axis
        stats = np.broadcast_to(self._prior, (n, self._D, 4)).copy()

        return probs, stats, 0
