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


def update_nig(old_stats: np.ndarray, x_t: np.ndarray) -> np.ndarray:
    """Online recursive NIG conjugate update.

    SRD 3.4 — Recursive equations (applied identically to all N run-lengths):

        kappa_new = kappa_old + 1
        mu_new    = (kappa_old * mu_old + x_t) / kappa_new
        alpha_new = alpha_old + 0.5
        beta_new  = beta_old + 0.5 * kappa_old * (x_t - mu_old)^2 / kappa_new

    Vectorized over all (N, D) simultaneously — zero Python loops.

    Args:
        old_stats: shape (N, D, 4), where the last axis holds
                   [mu, kappa, alpha, beta] for each run-length × dim.
        x_t:       shape (D,), the current observation vector.

    Returns:
        new_stats: shape (N, D, 4), same dtype as old_stats.
                   The input is NOT mutated.
    """
    # Read out current parameters — views, no copies needed yet
    mu_old    = old_stats[:, :, 0]   # (N, D)
    kappa_old = old_stats[:, :, 1]   # (N, D)
    alpha_old = old_stats[:, :, 2]   # (N, D)
    beta_old  = old_stats[:, :, 3]   # (N, D)

    # Broadcast x_t from (D,) to (1, D) — matches (N, D) arithmetic
    x = x_t[np.newaxis, :]           # (1, D) → broadcasts to (N, D)

    # Recursive NIG update (SRD 3.4, verbatim)
    kappa_new = kappa_old + 1.0
    mu_new    = (kappa_old * mu_old + x) / kappa_new
    alpha_new = alpha_old + 0.5
    beta_new  = beta_old + 0.5 * kappa_old * (x - mu_old) ** 2 / kappa_new

    # Assemble output — allocate new array to guarantee no mutation
    new_stats = np.empty_like(old_stats)
    new_stats[:, :, 0] = mu_new
    new_stats[:, :, 1] = kappa_new
    new_stats[:, :, 2] = alpha_new
    new_stats[:, :, 3] = beta_new

    return new_stats


def predictive_logpdf(suff_stats: np.ndarray, x_t: np.ndarray) -> np.ndarray:
    """Student-t predictive log-density, summed over D conditionally independent dims.

    SRD 3.2: The NIG predictive marginal for each dimension is a Student-t with:
        nu    = 2 * alpha
        mu    = mu (posterior mean)
        sigma2 = beta * (kappa + 1) / (alpha * kappa)

    Log-PDF of Student-t with location mu, scale sigma2, and nu degrees of freedom:
        log f(x) = log Gamma((nu+1)/2) - log Gamma(nu/2)
                   - 0.5 * log(nu * pi * sigma2)
                   - ((nu+1)/2) * log(1 + (x-mu)^2 / (nu * sigma2))

    For the BOCPD update we need the joint log-density across all D dimensions.
    Because dimensions are conditionally independent given the run-length:
        log f(x) = sum_d log f_d(x_d)

    This is reduced to a single sum over axis=1 (the D axis).

    Args:
        suff_stats: shape (N, D, 4) — current posterior parameters.
        x_t:        shape (D,) — observation to score.

    Returns:
        log_dens: shape (N,) — joint log-density for each run-length hypothesis.
    """
    mu    = suff_stats[:, :, 0]   # (N, D)
    kappa = suff_stats[:, :, 1]   # (N, D)
    alpha = suff_stats[:, :, 2]   # (N, D)
    beta  = suff_stats[:, :, 3]   # (N, D)

    x = x_t[np.newaxis, :]        # (1, D) → (N, D)

    # Student-t parameters derived from NIG marginal
    nu     = 2.0 * alpha                             # (N, D) degrees of freedom
    sigma2 = beta * (kappa + 1.0) / (alpha * kappa)  # (N, D) predictive scale

    # Log-PDF of Student-t (numerically stable form)
    log_normalizer = (
        gammaln((nu + 1.0) / 2.0)
        - gammaln(nu / 2.0)
        - 0.5 * np.log(nu * np.pi * sigma2)
    )
    deviation_sq = (x - mu) ** 2                     # (N, D)
    log_kernel = -((nu + 1.0) / 2.0) * np.log1p(deviation_sq / (nu * sigma2))

    # Sum over D dimensions (conditional independence)
    log_dens = np.sum(log_normalizer + log_kernel, axis=1)  # (N,)
    return log_dens
