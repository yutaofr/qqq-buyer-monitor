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

import base64
import io
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

    Causal Overdrive (v1.3):
        τ_t = max(τ_floor, τ_base × (1 − γ × z(λ_macro)))
        where z(λ) = clamp((λ − λ_floor) / (λ_ceil − λ_floor), 0, 1)

        τ is computed BEFORE x_t arrives, using only λ_macro (which
        depends on x_{1:t-1}). This preserves Adams & MacKay causality:
        the predictive distribution shape is locked before observation.

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

        # Causal Overdrive parameters
        od_cfg = config.get("overdrive", {})
        self._tau_base:  float = od_cfg.get("tau_base", 1.0)
        self._gamma:     float = od_cfg.get("gamma", 0.0)
        self._tau_floor:  float = od_cfg.get("tau_floor", 2.0)
        self._forgetting_lambda: float = config.get("forgetting", {}).get("lambda", 1.0)

        # Lambda bounds for z(λ) normalization
        m_cfg = config.get("macro_hazard", {})
        self._lambda_floor: float = m_cfg.get("lambda_floor", 0.002)
        self._lambda_ceil:  float = m_cfg.get("lambda_ceil", 0.016)

        # Build (D, 4) prior matrix from config
        self._prior: np.ndarray = self._build_prior()
        self._severity_weights: np.ndarray = self._build_severity_weights()
        self._severity_caps: np.ndarray = self._build_severity_caps()
        self._severity_resonance_method: str = (
            config.get("regime_severity", {}).get("resonance_method", "participation_ratio")
        )
        self._severity_resonance_gamma: float = float(
            config.get("regime_severity", {}).get("resonance_gamma", 1.0)
        )
        if self._severity_resonance_gamma < 0.0:
            raise ValueError("regime_severity.resonance_gamma must be non-negative.")
        self._prior_sigma2: np.ndarray = self._predictive_sigma2(self._prior)

        # Initialise state
        self._probs, self._stats, self._t = self._initial_state()

    # ─────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────

    def _compute_tau(self, lambda_macro: float) -> float:
        """Compute causal τ_t from macro hazard rate.

        Strictly causal: λ_macro depends only on x_{1:t-1}.
        The predictive distribution P(x_t | r, τ_t) is locked before x_t.

        Returns:
            tau_t: float > 0, clamped to [tau_floor, tau_base].
        """
        if self._gamma == 0.0:
            return self._tau_base

        denom = self._lambda_ceil - self._lambda_floor
        if denom <= 0:
            return self._tau_base

        z = np.clip(
            (lambda_macro - self._lambda_floor) / denom,
            0.0, 1.0,
        )
        tau_raw = self._tau_base * (1.0 - self._gamma * z)
        return max(self._tau_floor, tau_raw)

    def update(self, x_t: np.ndarray, lambda_macro: float) -> float:
        """Run one step of the five-step BOCPD loop.

        Args:
            x_t: shape (D,) observation vector at time t.
            lambda_macro: scalar macro hazard rate for this step.

        Returns:
            p_cp_raw: float in [0, 1] — raw changepoint probability.
        """
        # Step 0: Compute causal τ_t (BEFORE seeing x_t's influence on likelihood)
        tau_t = self._compute_tau(lambda_macro)

        # Step 1: predictive log-density with temperature scaling
        log_pred, log_comp = predictive_logpdf(self._stats, x_t, tau=tau_t, return_components=True)

        # Diagnostic: compute baseline likelihood to measure tau's effect
        _, log_comp_base = predictive_logpdf(self._stats, x_t, tau=self._tau_base, return_components=True)
        # We record the likelihood of the highest-probability regime (most confident prior)
        best_r = np.argmax(self._probs)
        self._last_LL_spread_actual = float(log_comp[best_r, 1])  # 1 = SPREAD_ANOMALY
        self._last_LL_spread_base = float(log_comp_base[best_r, 1])

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
        new_stats[1:, :, :] = update_nig(
            self._stats[:-1, :, :],
            x_t,
            forgetting_lambda=self._forgetting_lambda,
        )

        # Store tau_t for diagnostic access
        self._last_tau = tau_t

        # Commit new state
        self._probs = new_probs
        self._stats = new_stats
        self._t += 1
        self._last_regime_diagnostics = self._compute_regime_diagnostics()

        return float(new_probs[0])  # p_cp_raw

    @property
    def last_tau(self) -> float:
        """Last computed τ_t (for diagnostic logging)."""
        return getattr(self, "_last_tau", self._tau_base)

    @property
    def last_LL_spread_actual(self) -> float:
        return getattr(self, "_last_LL_spread_actual", 0.0)

    @property
    def last_LL_spread_base(self) -> float:
        return getattr(self, "_last_LL_spread_base", 0.0)

    @property
    def last_regime_diagnostics(self) -> dict:
        """Diagnostics describing current regime water level, separate from p_cp."""
        return getattr(self, "_last_regime_diagnostics", self._compute_regime_diagnostics()).copy()

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

    def dump_state(self) -> dict:
        """Binary persistence of state limits matrix size explosion over time."""
        buf = io.BytesIO()
        np.savez_compressed(
            buf,
            probs=self._probs,
            stats=self._stats
        )
        return {
            "b64_arrays": base64.b64encode(buf.getvalue()).decode("utf-8"),
            "t": self._t
        }

    def load_state(self, state_dict: dict) -> None:
        """Resume exact memory layout from binary dump."""
        self._t = state_dict["t"]
        buf = io.BytesIO(base64.b64decode(state_dict["b64_arrays"]))
        with np.load(buf, allow_pickle=False) as data:
            self._probs = data["probs"].copy()
            self._stats = data["stats"].copy()

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

    def _build_severity_weights(self) -> np.ndarray:
        """Return normalized severity weights in observation-dimension order."""
        cfg = self._config.get("regime_severity", {})
        weights = cfg.get("weights", {})
        raw = np.array(
            [
                weights.get("ed_accel", 1.0 / self._D),
                weights.get("spread_anomaly", 1.0 / self._D),
                weights.get("fisher_rho", 1.0 / self._D),
            ],
            dtype=np.float64,
        )
        total = raw.sum()
        if total <= 0.0:
            return np.full(self._D, 1.0 / self._D, dtype=np.float64)
        return raw / total

    def _build_severity_caps(self) -> np.ndarray:
        """Return per-dimension log-variance caps in observation-dimension order."""
        cfg = self._config.get("regime_severity", {})
        caps = cfg.get("dimension_caps", {})
        raw = np.array(
            [
                caps.get("ed_accel", np.inf),
                caps.get("spread_anomaly", np.inf),
                caps.get("fisher_rho", np.inf),
            ],
            dtype=np.float64,
        )
        if np.any(raw < 0.0):
            raise ValueError("regime_severity.dimension_caps must be non-negative.")
        return raw

    def _compute_resonance(self, capped_log_ratio: np.ndarray) -> tuple[float, float]:
        """Return continuous cross-dimension resonance PR and multiplier.

        Severity amplitude is still computed with physical weights. PR is computed
        on de-weighted, cap-standardized stress so it measures breadth rather than
        the configured explanatory power of each dimension.
        """
        if self._severity_resonance_method in {"none", None}:
            return float(self._D), 1.0
        if self._severity_resonance_method != "participation_ratio":
            raise ValueError(
                f"Unsupported regime_severity.resonance_method="
                f"{self._severity_resonance_method!r}"
            )

        finite_positive_caps = np.isfinite(self._severity_caps) & (self._severity_caps > 0.0)
        resonance_input = np.zeros_like(capped_log_ratio, dtype=np.float64)
        resonance_input[finite_positive_caps] = (
            capped_log_ratio[finite_positive_caps] / self._severity_caps[finite_positive_caps]
        )
        resonance_input[~finite_positive_caps] = capped_log_ratio[~finite_positive_caps]
        resonance_input = np.maximum(resonance_input, 0.0)

        total = float(np.sum(resonance_input))
        if total <= 0.0:
            return float(self._D), 1.0
        denom = float(np.sum(resonance_input * resonance_input))
        if denom <= 0.0:
            return float(self._D), 1.0

        pr = float(np.clip((total * total) / denom, 1.0, float(self._D)))
        multiplier = float((pr / float(self._D)) ** self._severity_resonance_gamma)
        return pr, multiplier

    @staticmethod
    def _predictive_sigma2(stats: np.ndarray) -> np.ndarray:
        """NIG Student-t predictive variance scale per run-length and dimension."""
        kappa = stats[..., 1]
        alpha = stats[..., 2]
        beta = stats[..., 3]
        return beta * (kappa + 1.0) / (alpha * kappa)

    def _compute_regime_diagnostics(self) -> dict:
        """Compute posterior-mixture regime severity from NIG predictive scales."""
        probs = self._probs
        stats = self._stats
        dominant_r = int(np.argmax(probs))
        dominant_prob = float(probs[dominant_r])

        sigma2_all = self._predictive_sigma2(stats)
        sigma2_mix = np.sum(probs[:, np.newaxis] * sigma2_all, axis=0)
        log_ratio = np.log(np.maximum(sigma2_mix, 1e-300) / self._prior_sigma2)
        positive_log_ratio = np.maximum(log_ratio, 0.0)
        capped_log_ratio = np.minimum(positive_log_ratio, self._severity_caps)
        severity_base = 1.0 - np.exp(-float(np.dot(self._severity_weights, capped_log_ratio)))
        resonance_pr, resonance_multiplier = self._compute_resonance(capped_log_ratio)
        severity = severity_base * resonance_multiplier

        sigma2_dom = sigma2_all[dominant_r]
        return {
            "dominant_run_length": dominant_r,
            "dominant_run_prob": dominant_prob,
            "regime_sigma2_ed": float(sigma2_dom[0]),
            "regime_sigma2_spread": float(sigma2_dom[1]),
            "regime_sigma2_fisher": float(sigma2_dom[2]),
            "regime_sigma2_mix_ed": float(sigma2_mix[0]),
            "regime_sigma2_mix_spread": float(sigma2_mix[1]),
            "regime_sigma2_mix_fisher": float(sigma2_mix[2]),
            "regime_severity_base": float(np.clip(severity_base, 0.0, 1.0 - 1e-12)),
            "regime_resonance_pr": resonance_pr,
            "regime_resonance_multiplier": resonance_multiplier,
            "regime_v_ed": float(positive_log_ratio[0]),
            "regime_v_spread": float(positive_log_ratio[1]),
            "regime_v_fisher": float(positive_log_ratio[2]),
            "regime_v_capped_ed": float(capped_log_ratio[0]),
            "regime_v_capped_spread": float(capped_log_ratio[1]),
            "regime_v_capped_fisher": float(capped_log_ratio[2]),
            "regime_severity": float(np.clip(severity, 0.0, 1.0 - 1e-12)),
        }

    def _initial_state(self) -> tuple[np.ndarray, np.ndarray, int]:
        """Construct fresh initial state: all mass at r=0, all rows = prior."""
        n = self._r_max + 1  # 505

        probs = np.zeros(n, dtype=np.float64)
        probs[0] = 1.0       # 100% mass at run-length 0

        # Broadcast prior (D, 4) → (N, D, 4) by tiling over run-length axis
        stats = np.broadcast_to(self._prior, (n, self._D, 4)).copy()

        return probs, stats, 0
