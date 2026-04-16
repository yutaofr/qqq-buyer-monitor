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
    prior_stats: np.ndarray | None = None,
) -> np.ndarray:
    """Online recursive NIG conjugate update.

    SRD 3.4 — Recursive equations (applied identically to all N run-lengths):

        kappa_new = kappa_old + 1
        mu_new    = (kappa_old * mu_old + x_t) / kappa_new
        alpha_new = alpha_old + 0.5
        beta_new  = beta_old + 0.5 * kappa_old * (x_t - mu_old)^2 / kappa_new

    Vectorized over all (N, D) simultaneously — zero Python loops.

    Prior-anchored decay (optional):
        When forgetting_lambda < 1, the old posterior is first shrunk back
        toward the fixed prior before absorbing x_t:

            kappa^- = kappa_0 + λ (kappa_old - kappa_0)
            alpha^- = alpha_0 + λ (alpha_old - alpha_0)
            eta^-   = kappa_0*mu_0 + λ (kappa_old*mu_old - kappa_0*mu_0)
            mu^-    = eta^- / kappa^-
            beta^-  = beta_0 + λ (beta_old - beta_0)

        The standard NIG update is then applied to this decayed state. With
        λ=1 the update exactly matches the SRD v1.2 baseline.

    Args:
        old_stats: shape (N, D, 4), where the last axis holds
                   [mu, kappa, alpha, beta] for each run-length × dim.
        x_t:       shape (D,), the current observation vector.
        forgetting_lambda: decay factor λ in (0, 1]. Default 1.0.
        prior_stats: prior row with shape (D, 4) or broadcastable equivalent.
                     Required when forgetting_lambda < 1.

    Returns:
        new_stats: shape (N, D, 4), same dtype as old_stats.
                   The input is NOT mutated.
    """
    if not (0.0 < forgetting_lambda <= 1.0):
        raise ValueError("forgetting_lambda must lie in (0, 1].")

    # Read out current parameters — views, no copies needed yet
    mu_old = old_stats[:, :, 0]      # (N, D)
    kappa_old = old_stats[:, :, 1]   # (N, D)
    alpha_old = old_stats[:, :, 2]   # (N, D)
    beta_old = old_stats[:, :, 3]    # (N, D)

    # Broadcast x_t from (D,) to (1, D) — matches (N, D) arithmetic
    x = x_t[np.newaxis, :]           # (1, D) → broadcasts to (N, D)

    if forgetting_lambda == 1.0:
        mu_eff = mu_old
        kappa_eff = kappa_old
        alpha_eff = alpha_old
        beta_eff = beta_old
    else:
        if prior_stats is None:
            raise ValueError("prior_stats is required when forgetting_lambda < 1.")

        prior = np.broadcast_to(prior_stats, old_stats.shape)
        mu_0 = prior[:, :, 0]
        kappa_0 = prior[:, :, 1]
        alpha_0 = prior[:, :, 2]
        beta_0 = prior[:, :, 3]

        kappa_eff = kappa_0 + forgetting_lambda * (kappa_old - kappa_0)
        alpha_eff = alpha_0 + forgetting_lambda * (alpha_old - alpha_0)
        eta_0 = kappa_0 * mu_0
        eta_eff = eta_0 + forgetting_lambda * (kappa_old * mu_old - eta_0)
        mu_eff = eta_eff / kappa_eff
        beta_eff = beta_0 + forgetting_lambda * (beta_old - beta_0)

    # Recursive NIG update
    kappa_new = kappa_eff + 1.0
    mu_new = (kappa_eff * mu_eff + x) / kappa_new
    alpha_new = alpha_eff + 0.5
    beta_new = beta_eff + 0.5 * kappa_eff * (x - mu_eff) ** 2 / kappa_new

    # Assemble output — allocate new array to guarantee no mutation
    new_stats = np.empty_like(old_stats)
    new_stats[:, :, 0] = mu_new
    new_stats[:, :, 1] = kappa_new
    new_stats[:, :, 2] = alpha_new
    new_stats[:, :, 3] = beta_new

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
    # Sum over D dimensions (conditional independence)
    log_dens = np.sum(log_components, axis=1)               # (N,)

    if return_components:
        return log_dens, log_components
    return log_dens
