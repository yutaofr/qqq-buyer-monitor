import numpy as np
from collections import deque
from typing import Dict, Any, Tuple
import io
import base64

from src.liquidity.signal.macro_hazard import map_to_hazard


class StreamingFeatureExtractor:
    def __init__(self, config: dict):
        self.ed_cfg = config["ed_signal"]
        self.macro_cfg = config["macro_hazard"]
        
        # Sizing
        self.ed_win = self.ed_cfg["window"]
        self.ed_med_win = self.ed_cfg["median_window"]
        self.min_names = self.ed_cfg["min_names"]
        
        self.macro_weights = self.macro_cfg["weights"]
        self.macro_lookback = self.macro_cfg["rank_lookback"]
        
        # Raw Data Buffers
        self.returns_buf = deque(maxlen=self.ed_win)
        self.vix_buf = deque(maxlen=252)
        
        # We need historical values of macro variables to compute pct_change
        self.walcl_buf = deque(maxlen=self.macro_lookback + 20)
        self.rrp_buf = deque(maxlen=self.macro_lookback + 5)
        self.tga_buf = deque(maxlen=self.macro_lookback + 20)
        self.sofr_buf = deque(maxlen=self.macro_lookback)
        
        # Intermediate Buffers
        self.ed_buf = deque(maxlen=self.ed_med_win + 1)
        self.ed_med_buf = deque(maxlen=2)
        
        self.ed_accel_buf = deque(maxlen=20)
        self.spread_buf = deque(maxlen=20)
        
    def step(self, raw_obs: dict) -> Tuple[np.ndarray, float]:
        """Process one tick of raw market observations.
        
        raw_obs keys must include:
        - 'constituent_returns': np.ndarray (size 50, order matters)
        - 'vix': float
        - 'walcl': float
        - 'rrp': float
        - 'tga': float
        - 'sofr': float
        
        Returns:
            x_t (np.ndarray): [ed_accel, spread_anomaly, fisher_rho]
            lambda_macro (float): Macro hazard rate
        """
        # Append raw data
        self.returns_buf.append(raw_obs["constituent_returns"])
        self.vix_buf.append(raw_obs["vix"])
        
        self.walcl_buf.append(raw_obs["walcl"])
        self.rrp_buf.append(raw_obs["rrp"])
        self.tga_buf.append(raw_obs["tga"])
        self.sofr_buf.append(raw_obs["sofr"])
        
        # 1. ED Computation (PCA exact parity)
        ed = self._compute_ed()
        self.ed_buf.append(ed)
        
        # 1b. ED Acceleration
        ed_accel = self._compute_ed_accel()
        self.ed_accel_buf.append(ed_accel)
        
        # 2. Spread Anomaly
        spread = self._compute_spread()
        self.spread_buf.append(spread)
        
        # 3. Fisher Rho
        fisher = self._compute_fisher()
        
        # 4. Macro Hazard
        lam = self._compute_macro()
        
        x_t = np.array([ed_accel, spread, fisher], dtype=np.float64)
        return x_t, lam

    def _compute_ed(self) -> float:
        if len(self.returns_buf) < self.ed_win:
            return np.nan
        mat = np.array(self.returns_buf)
        # Drop columns with any NaNs
        valid_cols = ~np.isnan(mat).any(axis=0)
        if np.sum(valid_cols) < self.min_names:
            return np.nan
            
        mat = mat[:, valid_cols]
        # Filter zero-variance
        col_std = np.std(mat, axis=0, ddof=1)
        mat = mat[:, col_std > 0]
        
        if mat.shape[1] < self.min_names:
            return np.nan
            
        cov = np.cov(mat, rowvar=False)
        if cov.ndim == 0:
            return 1.0
            
        eigenvalues = np.linalg.eigvalsh(cov)
        eigenvalues = np.maximum(eigenvalues, 0.0)
        total = eigenvalues.sum()
        if total == 0:
            return np.nan
        return float(eigenvalues.max() / total)
        
    def _compute_ed_accel(self) -> float:
        if len(self.ed_buf) < self.ed_med_win:
            # We need at least median_window for first median
            self.ed_med_buf.append(np.nan)
            return np.nan
            
        recent_ed = np.array(self.ed_buf)[-self.ed_med_win:]
        # Use min_periods=5 (half window) to survive sparse NaN ticks
        valid_mask = ~np.isnan(recent_ed)
        if np.sum(valid_mask) < 5:
            med = np.nan
        else:
            med = np.median(recent_ed[valid_mask])
            
        self.ed_med_buf.append(med)
        
        if len(self.ed_med_buf) < 2:
            return np.nan
            
        diff = self.ed_med_buf[-1] - self.ed_med_buf[-2]
        return float(diff)
        
    def _compute_spread(self) -> float:
        if len(self.vix_buf) < 126:
            return np.nan
            
        vix_arr = np.array(self.vix_buf)
        valid_mask = ~np.isnan(vix_arr)
        if np.sum(valid_mask) < 126:
            return np.nan
            
        mu = np.mean(vix_arr[valid_mask])
        std = np.std(vix_arr[valid_mask], ddof=1)
        if std == 0 or np.isnan(std):
            return 0.0
            
        current = self.vix_buf[-1]
        if np.isnan(current):
            return np.nan
            
        return float((current - mu) / std)
        
    def _compute_fisher(self) -> float:
        if len(self.ed_accel_buf) < 20 or len(self.spread_buf) < 20:
            return np.nan
            
        ed_arr = np.array(self.ed_accel_buf)
        sp_arr = np.array(self.spread_buf)
        
        valid = ~np.isnan(ed_arr) & ~np.isnan(sp_arr)
        # rolling(20, min_periods=10) logic
        if np.sum(valid) < 10:
            return np.nan
            
        ed_valid = ed_arr[valid]
        sp_valid = sp_arr[valid]
        
        std_e = np.std(ed_valid, ddof=1)
        std_s = np.std(sp_valid, ddof=1)
        if std_e == 0 or std_s == 0:
            return 0.0
            
        rho = np.corrcoef(ed_valid, sp_valid)[0, 1]
        if np.isnan(rho):
            return 0.0
            
        return float(0.5 * np.log((1 + rho) / (1 - rho + 1e-8)))

    def _compute_macro(self) -> float:
        transformed = {}
        
        # 1. Transform directions
        if len(self.walcl_buf) > 20:
            walcl_arr = np.array(self.walcl_buf)
            transformed["walcl"] = -(walcl_arr[20:] - walcl_arr[:-20]) / walcl_arr[:-20]
        else:
            transformed["walcl"] = np.array([])
            
        if len(self.rrp_buf) > 5:
            rrp_arr = np.array(self.rrp_buf)
            transformed["rrp"] = -(rrp_arr[5:] - rrp_arr[:-5]) / rrp_arr[:-5]
        else:
            transformed["rrp"] = np.array([])
            
        if len(self.tga_buf) > 20:
            tga_arr = np.array(self.tga_buf)
            transformed["tga"] = (tga_arr[20:] - tga_arr[:-20]) / tga_arr[:-20]
        else:
            transformed["tga"] = np.array([])
            
        transformed["fra_ois"] = np.array(self.sofr_buf)
        
        # 2. Get Ranks
        ranks = {}
        for key in ["walcl", "rrp", "tga", "fra_ois"]:
            arr = transformed[key]
            if len(arr) < self.macro_lookback:
                ranks[key] = np.nan
            else:
                window = arr[-self.macro_lookback:]
                current = window[-1]
                if np.isnan(current):
                    ranks[key] = np.nan
                else:
                    ranks[key] = np.sum(window <= current) / len(window)
                    
        # 3. Composite
        weighted_sum = 0.0
        avail_weight = 0.0
        
        for key, w in self.macro_weights.items():
            val = ranks[key]
            if not np.isnan(val):
                weighted_sum += val * w
                avail_weight += w
                
        if avail_weight == 0.0:
            composite = np.nan
        else:
            composite = weighted_sum / avail_weight
            
        # 4. Map to Hazard
        if np.isnan(composite):
            return self.macro_cfg["lambda_floor"]
            
        return float(self.macro_cfg["lambda_floor"] + (self.macro_cfg["lambda_ceil"] - self.macro_cfg["lambda_floor"]) * composite)

    def dump_state(self) -> str:
        """Serialize state into a deterministic base64-encoded compressed npz.
        
        Using binary serialization guarantees that float states perfectly align
        mathematically across processes/restarts, unlike JSON which cuts float tails.
        """
        buf = io.BytesIO()
        np.savez_compressed(
            buf,
            returns=np.array(self.returns_buf, dtype=np.float64) if len(self.returns_buf) > 0 else np.empty(0),
            vix=np.array(self.vix_buf, dtype=np.float64),
            walcl=np.array(self.walcl_buf, dtype=np.float64),
            rrp=np.array(self.rrp_buf, dtype=np.float64),
            tga=np.array(self.tga_buf, dtype=np.float64),
            sofr=np.array(self.sofr_buf, dtype=np.float64),
            ed=np.array(self.ed_buf, dtype=np.float64),
            ed_med=np.array(self.ed_med_buf, dtype=np.float64),
            ed_accel=np.array(self.ed_accel_buf, dtype=np.float64),
            spread=np.array(self.spread_buf, dtype=np.float64),
        )
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def load_state(self, b64_state: str) -> None:
        """Deserialize state from base64 string."""
        buf = io.BytesIO(base64.b64decode(b64_state))
        with np.load(buf, allow_pickle=False) as data:
            self.returns_buf.clear()
            if len(data["returns"]) > 0:
                self.returns_buf.extend(data["returns"])
                
            self.vix_buf.clear()
            self.vix_buf.extend(data["vix"])
            
            self.walcl_buf.clear()
            self.walcl_buf.extend(data["walcl"])
            
            self.rrp_buf.clear()
            self.rrp_buf.extend(data["rrp"])
            
            self.tga_buf.clear()
            self.tga_buf.extend(data["tga"])
            
            self.sofr_buf.clear()
            self.sofr_buf.extend(data["sofr"])
            
            self.ed_buf.clear()
            self.ed_buf.extend(data["ed"])
            
            self.ed_med_buf.clear()
            self.ed_med_buf.extend(data["ed_med"])
            
            self.ed_accel_buf.clear()
            self.ed_accel_buf.extend(data["ed_accel"])
            
            self.spread_buf.clear()
            self.spread_buf.extend(data["spread"])
