"""NIG conjugate update and Student-t predictive density.

SRD v1.2 Chapter 3: Online Bayesian inference via Normal-Inverse-Gamma
conjugate family. Two pure functions — no state, no side effects.

Sufficient statistic layout (axis=-1, 4 parameters per dimension):
    [..., 0] = mu     — posterior mean
    [..., 1] = kappa  — number of pseudo-observations (run-length counter)
    [..., 2] = alpha  — IG shape parameter
    [..., 3] = beta   — IG rate parameter

Why NIG?
  - Exact conjugacy: closed-form posterior after each observation.
  - Predictive density is Student-t: heavier tails than Gaussian, natural
    for financial data. Derived analytically from marginalizing out sigma^2.
  - Online recursive form: O(1) update per step, no reprocessing history.
"""

import numpy as np
from scipy.special import gammaln


def update_nig(
    old_stats: np.ndarray,
    x_t: np.ndarray,
    forgetting_lambda: float = 1.0,
) -> np.ndarray:
    """Online recursive NIG conjugate update with optional forgetting factor.

    SRD 3.4 — Standard update (λ = 1.0):
        kappa_new = kappa_old + 1
        mu_new    = (kappa_old * mu_old + x_t) / kappa_new
        alpha_new = alpha_old + 0.5
        beta_new  = beta_old + 0.5 * kappa_old * (x_t - mu_old)^2 / kappa_new

    With forgetting (λ < 1.0):
        kappa_new = λ * kappa_old + 1
        mu_new    = (λ * kappa_old * mu_old + x_t) / kappa_new
        alpha_new = λ * alpha_old + 0.5
        beta_new  = λ * beta_old + 0.5 * (λ * kappa_old) * (x_t - mu_old)^2 / kappa_new

    Asymptotes: kappa_∞ = 1/(1-λ)  alpha_∞ = 0.5/(1-λ)
    At λ=0.98: kappa_∞ = 50, alpha_∞ = 25 → ν_eff = 2×25/τ — stays thick-tailed.

    Vectorized over all (N, D) simultaneously — zero Python loops.

    Args:
        old_stats: shape (N, D, 4) — [mu, kappa, alpha, beta] per run-length × dim.
        x_t:       shape (D,) — current observation.
        forgetting_lambda: decay factor λ ∈ (0, 1]. Default 1.0 (no decay).

    Returns:
        new_stats: shape (N, D, 4), same dtype. Input is NOT mutated.
    """
    if not (0.0 < forgetting_lambda <= 1.0):
        raise ValueError("forgetting_lambda must lie in (0, 1].")

    mu_old    = old_stats[:, :, 0]   # (N, D)
    kappa_old = old_stats[:, :, 1]   # (N, D)
    alpha_old = old_stats[:, :, 2]   # (N, D)
    beta_old  = old_stats[:, :, 3]   # (N, D)

    x = x_t[np.newaxis, :]           # (1, D) → broadcasts to (N, D)

    # Apply forgetting: shrink old evidence to λ × its current weight
    kappa_decayed = forgetting_lambda * kappa_old   # (N, D)
    alpha_decayed = forgetting_lambda * alpha_old   # (N, D)
    beta_decayed  = forgetting_lambda * beta_old    # (N, D)

    # Absorb x_t into the decayed prior (standard NIG update algebra)
    kappa_new = kappa_decayed + 1.0
    mu_new    = (kappa_decayed * mu_old + x) / kappa_new
    alpha_new = alpha_decayed + 0.5
    beta_new  = beta_decayed + 0.5 * kappa_decayed * (x - mu_old) ** 2 / kappa_new

    new_stats = np.empty_like(old_stats)
    nan_mask = np.isnan(x_t)

    # Bayesian NaN Marginalization: Skip update for missing dimensions
    new_stats[:, :, 0] = np.where(nan_mask, mu_old, mu_new)
    new_stats[:, :, 1] = np.where(nan_mask, kappa_old, kappa_new)
    new_stats[:, :, 2] = np.where(nan_mask, alpha_old, alpha_new)
    new_stats[:, :, 3] = np.where(nan_mask, beta_old, beta_new)

    return new_stats


def predictive_logpdf(
    suff_stats: np.ndarray,
    x_t: np.ndarray,
    tau: float = 1.0,
    return_components: bool = False,
):
    """Student-t predictive log-density, summed over D conditionally independent dims.

    SRD 3.2: The NIG predictive marginal for each dimension is a Student-t.
    Temperature scaling (SRD Redline #2): nu = 2 * alpha / tau.

    Without tau: nu grows linearly with run-length (nu = 2 * alpha = 2 * (α₀ + r/2)).
    At r=250, nu ≈ 257 → Student-t ≈ Gaussian → no tail sensitivity.
    With tau > 1: nu is reduced, preserving thick tails even at large run-lengths.
    With tau < 1: nu is increased, making tails thinner (more sensitive).

    Args:
        suff_stats: shape (N, D, 4) — current posterior parameters.
        x_t:        shape (D,) — observation to score.
        tau:        temperature scalar > 0. Default 1.0 (no scaling).
        return_components: if True, return (log_dens, log_components_per_dim).

    Returns:
        log_dens: shape (N,) — joint log-density for each run-length hypothesis.
        (optional) log_components: shape (N, D) — individual log likelihoods.
    """
    mu    = suff_stats[:, :, 0]   # (N, D)
    kappa = suff_stats[:, :, 1]   # (N, D)
    alpha = suff_stats[:, :, 2]   # (N, D)
    beta  = suff_stats[:, :, 3]   # (N, D)

    x = x_t[np.newaxis, :]        # (1, D) → (N, D)

    # Student-t parameters derived from NIG marginal
    # Temperature scaling: divide by tau to control effective degrees of freedom
    nu     = 2.0 * alpha / tau                        # (N, D) — key: tau controls tail thickness
    sigma2 = beta * (kappa + 1.0) / (alpha * kappa)  # (N, D) predictive scale

    # Log-PDF of Student-t (numerically stable form)
    log_normalizer = (
        gammaln((nu + 1.0) / 2.0)
        - gammaln(nu / 2.0)
        - 0.5 * np.log(nu * np.pi * sigma2)
    )
    deviation_sq = (x - mu) ** 2                     # (N, D)
    log_kernel = -((nu + 1.0) / 2.0) * np.log1p(deviation_sq / (nu * sigma2))

    log_components = log_normalizer + log_kernel            # (N, D)

    # Bayesian NaN Marginalization: Missing dims contribute 0 to log-density (marginalized out)
    log_components[:, np.isnan(x_t)] = 0.0

    # Sum over D dimensions (conditional independence)
    log_dens = np.sum(log_components, axis=1)               # (N,)

    if return_components:
        return log_dens, log_components
    return log_dens
