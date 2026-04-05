import numpy as np
from scipy.optimize import minimize

class ConstrainedLogisticRegression:
    """
    Physically-Constrained Ridge Logistic Regression.
    Uses L-BFGS-B to solve the logistic loss minimization problem with box constraints 
    on coefficients.
    """
    def __init__(self, C=1.0, bounds=None, fit_intercept=True):
        """
        :param C: Inverse of regularization strength (standard sklearn notation).
        :param bounds: List of (min, max) tuples for each feature coefficient.
        :param fit_intercept: Whether to calculate the intercept for this model.
        """
        self.C = C
        if bounds is not None:
            # Pre-validate if bounds is provided as a list/array
            self.bounds = list(bounds)
        else:
            self.bounds = None
        self.fit_intercept = fit_intercept
        self.coef_ = None
        self.intercept_ = None
        self.classes_ = np.array([0, 1])

    def _logistic_loss(self, theta, X, y, inv_C):
        """
        Binary Cross Entropy with L2 penalty.
        L = - sum(y*log(p) + (1-y)*log(1-p)) + 0.5 * inv_C * ||w||^2
        """
        if self.fit_intercept:
            w = theta[:-1]
            b = theta[-1]
        else:
            w = theta
            b = 0.0
        
        z = np.dot(X, w) + b
        
        # Binary Cross-Entropy using logaddexp for numerical stability
        # -[y*log(sigm(z)) + (1-y)*log(1-sigm(z))] = log(1+exp(z)) - y*z
        # Using np.logaddexp(0, z) is equivalent to log(1+exp(z))
        loss = np.sum(np.logaddexp(0, z) - y * z)
        
        # Ridge Regularization (Penalty)
        reg = 0.5 * inv_C * np.sum(w**2)
        
        return loss + reg

    def _logistic_grad(self, theta, X, y, inv_C):
        """
        Gradient of BCE Loss + L2 Penalty.
        dL/dw = X^T (p - y) + inv_C * w
        dL/db = sum(p - y)
        """
        if self.fit_intercept:
            w = theta[:-1]
            b = theta[-1]
        else:
            w = theta
            b = 0.0
        
        z = np.dot(X, w) + b
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -35, 35)))
        
        dz = p - y
        dw = np.dot(X.T, dz) + inv_C * w
        
        if self.fit_intercept:
            db = np.sum(dz)
            return np.append(dw, db)
        return dw

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        n_samples, n_features = X.shape
        
        # 1. Initialize theta
        if self.fit_intercept:
            theta_start = np.zeros(n_features + 1)
        else:
            theta_start = np.zeros(n_features)
            
        # 2. Setup Bounds
        if self.bounds is None:
            weights_bounds = [(None, None)] * n_features
        else:
            if len(self.bounds) != n_features:
                raise ValueError(f"Bounds length {len(self.bounds)} must match n_features {n_features}")
            weights_bounds = self.bounds
            
        if self.fit_intercept:
            # Intercept is unconstrained unless explicitly requested (not typical)
            full_bounds = weights_bounds + [(None, None)]
        else:
            full_bounds = weights_bounds
            
        inv_C = 1.0 / self.C if self.C != 0 else 1e10 # Handle very small C
        
        # 3. Minimize
        res = minimize(
            fun=self._logistic_loss,
            x0=theta_start,
            args=(X, y, inv_C),
            method='L-BFGS-B',
            jac=self._logistic_grad,
            bounds=full_bounds,
            options={'maxiter': 2000}
        )
        
        # 4. Extract results
        if self.fit_intercept:
            self.coef_ = res.x[:-1].reshape(1, -1)
            self.intercept_ = np.array([res.x[-1]])
        else:
            self.coef_ = res.x.reshape(1, -1)
            self.intercept_ = np.array([0.0])
            
        return self

    def predict_proba(self, X):
        X = np.asarray(X, dtype=float)
        z = np.dot(X, self.coef_[0]) + self.intercept_[0]
        prob1 = 1.0 / (1.0 + np.exp(-np.clip(z, -35, 35)))
        return np.column_stack([1 - prob1, prob1])

    def decision_function(self, X):
        X = np.asarray(X, dtype=float)
        return np.dot(X, self.coef_[0]) + self.intercept_[0]
