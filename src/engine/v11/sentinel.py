"""Layer 4 Sentinel: Micro-structure risk and divergence engine."""
import numpy as np
import pandas as pd

class SentinelEngine:
    """
    Orchestrator for Layer 4 Sentinel logic.
    Integrates Online GNB, Smooth Divergence, and Probability Calibration.
    """
    def __init__(self, 
                 alpha: float = 0.05, 
                 span_base: int = 252, 
                 vol_floor: float = 0.005,
                 gamma_brier: float = 10.0,
                 ridge_lambda: float = 1e-6):
        self.gaussian = OnlineBivariateGaussian(alpha=alpha, ridge_lambda=ridge_lambda, burn_in_samples=span_base)
        self.divergence = SmoothDivergenceEngine(span=span_base, vol_floor=vol_floor)
        self.calibrator = ProbabilityCalibrator(gamma=gamma_brier)
        
        # State for low-pass filter on decay
        self.previous_stale_decay = 1.0
        # Historical HWM for surprisal
        self.surprisal_history = []
        
        # State for momentum
        self.previous_mu_macro = None
        self.previous_mu_micro = None
        
    def update(self, 
               r_t: float, 
               v_t: float, 
               p_macro: np.ndarray, 
               mu_macro: np.ndarray,
               y_true_idx: int | None = None,
               stale_days: int = 0,
               nominal_period: int = 30) -> dict:
        """
        Main update cycle for Sentinel.
        r_t: log return
        v_t: log excess volume
        p_macro: Macro posterior distribution
        mu_macro: Macro expected return vector
        y_true_idx: Optional true regime index for calibration
        stale_days: Days since last macro update
        nominal_period: Expected update frequency
        """
        x_t = np.array([r_t, v_t])
        self.gaussian.update(x_t)
        
        # 1. Calculate Surprisal and Penalty
        s_micro = self.gaussian.calculate_surprisal(x_t)
        self.surprisal_history.append(s_micro)
        if len(self.surprisal_history) > 1764: # 7-year rolling HWM
            self.surprisal_history = self.surprisal_history[-1764:]
            
        baseline = np.mean(self.surprisal_history[-252:]) if len(self.surprisal_history) >= 20 else 1.0
        hwm_99 = np.percentile(self.surprisal_history, 99) if len(self.surprisal_history) >= 100 else 3.0
        
        penalty = float(np.exp(max(s_micro - baseline, s_micro - hwm_99)))
        
        # 2. Micro Posterior and JSD
        p_micro = self._infer_micro_posterior(x_t)
        jsd = calculate_jsd(p_macro, p_micro)
        
        # 3. Alignment Score (Z-score + Tanh)
        mu_micro = self.gaussian.mu
        alignment = 1.0
        
        if self.previous_mu_macro is not None and self.previous_mu_micro is not None:
            # Directional momentum product
            delta_macro = mu_macro - self.previous_mu_macro
            delta_micro = mu_micro - self.previous_mu_micro
            
            # Use dot product of change vectors as raw signal
            raw_alignment_signal = float(np.dot(delta_macro, delta_micro))
            alignment = self.divergence.calculate_alignment_score(raw_alignment_signal)
            
        self.previous_mu_macro = mu_macro.copy() if mu_macro is not None else None
        self.previous_mu_micro = mu_micro.copy() if mu_micro is not None else None
        
        # 4. Stale Data Decay with Resumption Low-Pass
        from src.utils.stats import calculate_decay, calculate_inertial_recovery
        raw_stale_decay = calculate_decay(stale_days, nominal_period)
        effective_stale_decay = calculate_inertial_recovery(self.previous_stale_decay, raw_stale_decay)
        self.previous_stale_decay = effective_stale_decay
        
        # 5. Combined Multiplier
        # M_edge = exp(Alignment * JSD)
        m_edge = float(np.exp(alignment * jsd))
        # Effective edge with stale decay
        m_effective_edge = 1.0 + effective_stale_decay * (m_edge - 1.0)
        
        return {
            "s_micro": s_micro,
            "penalty": penalty,
            "jsd": jsd,
            "alignment": alignment,
            "m_edge": m_edge,
            "m_effective_edge": m_effective_edge,
            "stale_decay": effective_stale_decay
        }
        
    def _infer_micro_posterior(self, x: np.ndarray) -> np.ndarray:
        # Placeholder for micro GNB. Returns uniform for now.
        return np.array([0.25, 0.25, 0.25, 0.25])


def calculate_jsd(p: np.ndarray, q: np.ndarray) -> float:
    """
    Calculate Jensen-Shannon Divergence between two distributions.
    Bounded in [0, ln(2)].
    """
    # Ensure arrays
    p = np.array(p)
    q = np.array(q)
    
    # Avoid zero for log
    p = np.clip(p, 1e-12, 1.0)
    q = np.clip(q, 1e-12, 1.0)
    
    # Normalize
    p /= p.sum()
    q /= q.sum()
    
    m = 0.5 * (p + q)
    
    def kl_divergence(a, b):
        return np.sum(a * np.log(a / b))
        
    return 0.5 * kl_divergence(p, m) + 0.5 * kl_divergence(q, m)


class ProbabilityCalibrator:
    """
    Calibrates model confidence using Brier Score and Softplus decay.
    """
    def __init__(self, gamma: float = 10.0, threshold: float = 0.25):
        self.gamma = gamma
        self.threshold = threshold
        
    def calculate_brier_score(self, y_true_idx: int, p_pred: np.ndarray) -> float:
        """
        Calculate Brier Score for a single multi-class prediction.
        y_true_idx: integer index of the true regime.
        """
        y_true = np.zeros_like(p_pred)
        y_true[y_true_idx] = 1.0
        return float(np.mean((p_pred - y_true)**2))
        
    def calculate_confidence_weight(self, brier_score: float) -> float:
        """
        Calculate a continuous confidence weight using Softplus decay.
        Weight is high when Brier Score is low (better than threshold).
        """
        # Softplus-like smooth decay: weight = 1 / (1 + exp(gamma * (brier - threshold)))
        # This is essentially a sigmoid centered at threshold.
        return float(1.0 / (1.0 + np.exp(self.gamma * (brier_score - self.threshold))))


class SmoothDivergenceEngine:
    """
    Engine to calculate topologically smooth divergence signals.
    Implements Z-score normalization with vol floor and Tanh mapping.
    """
    def __init__(self, span: int = 252, vol_floor: float = 0.005):
        self.span = span
        self.vol_floor = vol_floor
        self.signals = []
        
    def calculate_alignment_score(self, raw_signal: float) -> float:
        """
        Calculate a continuous alignment score in [-1, 1].
        Uses rolling Z-score with floor and Tanh mapping.
        """
        self.signals.append(raw_signal)
        if len(self.signals) > self.span * 2: # Keep some history but limit
            self.signals = self.signals[-self.span:]
            
        if len(self.signals) < 20:
            return 0.0
            
        series = pd.Series(self.signals)
        mu = series.mean()
        sigma = max(series.std(), self.vol_floor)
        
        z_signal = (raw_signal - mu) / sigma
        return float(np.tanh(z_signal))


class OnlineBivariateGaussian:
    """
    Online EWMA-based Bivariate Gaussian distribution tracker.
    Implements Tikhonov regularization and Burn-in protocol.
    """
    def __init__(self, alpha: float = 0.05, ridge_lambda: float = 1e-6, burn_in_samples: int = 252):
        self.alpha = alpha
        self.ridge_lambda = ridge_lambda
        self.burn_in_samples = burn_in_samples
        
        self.mu = None
        self.sigma = None
        self.sample_count = 0
        
    def update(self, x: np.ndarray):
        """Update mean and covariance with a new observation x = [r, v]"""
        self.sample_count += 1
        
        if self.mu is None:
            self.mu = x.copy()
            self.sigma = np.eye(2) * 0.01 # Initial small variance
            return
            
        # EWMA update for mean
        self.mu = (1 - self.alpha) * self.mu + self.alpha * x
        
        # EWMA update for covariance
        diff = (x - self.mu).reshape(-1, 1)
        self.sigma = (1 - self.alpha) * self.sigma + self.alpha * (diff @ diff.T)
        
    def get_covariance(self, robust: bool = True) -> np.ndarray:
        """Return the current covariance matrix, optionally with Tikhonov regularization."""
        if self.sigma is None:
            return np.eye(2)
        if robust:
            return self.sigma + self.ridge_lambda * np.eye(2)
        return self.sigma
        
    def get_inverse_covariance(self) -> np.ndarray:
        """
        Return the robust inverse covariance matrix.
        Optimized analytical inverse for 2x2 matrices.
        """
        cov = self.get_covariance(robust=True)
        # Analytical 2x2 inverse:
        # [[a, b], [c, d]]^-1 = 1/(ad-bc) * [[d, -b], [-c, a]]
        a, b = cov[0, 0], cov[0, 1]
        c, d = cov[1, 0], cov[1, 1]
        det = a * d - b * c
        
        # det should not be zero due to Tikhonov regularization, but safety first
        if abs(det) < 1e-15:
            return np.eye(2) * 1e6 # Return very large variance if still singular
            
        inv_cov = np.array([
            [d, -b],
            [-c, a]
        ]) / det
        return inv_cov
        
    def calculate_surprisal(self, x: np.ndarray) -> float:
        """Calculate the Shannon Surprisal (1/2 * Mahalanobis Distance squared)"""
        if self.mu is None:
            return 1.0 # Default expectation
            
        inv_cov = self.get_inverse_covariance()
        diff = x - self.mu
        # D_M^2 = (x-mu)^T * Sigma^-1 * (x-mu)
        dm_sq = float(diff.T @ inv_cov @ diff)
        return 0.5 * dm_sq
        
    def is_ready(self) -> bool:
        """Check if the burn-in period is complete."""
        return self.sample_count >= self.burn_in_samples
