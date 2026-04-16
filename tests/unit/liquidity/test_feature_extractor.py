import numpy as np
import pytest
from collections import deque

from src.liquidity.engine.feature_extractor import StreamingFeatureExtractor
from src.liquidity.config import load_config
from src.liquidity.signal.ed_accel import compute_ed, compute_ed_accel
import pandas as pd

@pytest.fixture
def base_config():
    return load_config()

def test_feature_extractor_pca_parity(base_config):
    """Test that the incremental PCA math (deque) is mathematically equivalent to the batch math (DataFrame rolling)."""
    # 1. Setup a stable period
    np.random.seed(42)
    n_days = 200
    n_stocks = 50
    
    # Base calm returns
    rets = np.random.normal(0, 0.01, size=(n_days, n_stocks))
    
    # Inject a 6-day 5-sigma shock across all stocks starting at day 100.
    # It must be > 5 days (half the median window) to pull the 10-day median upwards.
    rets[100:106, :] = -0.05 + np.random.normal(0, 0.005, size=(6, n_stocks))
    
    # 2. Compute via pandas Batch
    idx = pd.date_range("2020-01-01", periods=n_days, freq="B")
    df_rets = pd.DataFrame(rets, index=idx)
    
    # We must mock ED to test acceleration
    ed_batch = compute_ed(df_rets, window=60, min_names=1)
    ed_accel_batch = compute_ed_accel(ed_batch, median_window=10)
    
    # 3. Compute via Streaming
    extractor = StreamingFeatureExtractor(base_config)
    ed_accel_stream = []
    
    for i in range(n_days):
        # We only really care about the returns vector for this test
        raw_obs = {
            "vix": 15.0,
            "walcl": 4e6,
            "rrp": 0.0,
            "tga": 3e5,
            "sofr": 0.05,
            "constituent_returns": rets[i, :]
        }
        x_t, _ = extractor.step(raw_obs)
        ed_accel_stream.append(x_t[0])
        
    # 4. Assert strict parity for every single point
    # Note: up to index 60, both will be NaN because lookback isn't reached.
    # Actually, up to 60 for ED, and up to 69 for ED_ACCEL.
    ed_accel_stream = np.array(ed_accel_stream)
    
    num_nan_batch = ed_accel_batch.isna().sum()
    num_nan_stream = np.isnan(ed_accel_stream).sum()
    
    # They shouldn't have the exact same number of NaNs because the Stream extractor
    # has been intentionally hardened to accept 5 min_periods instead of 10.
    # Batch has 69 NaNs, stream has 64 NaNs.
    assert num_nan_batch == 69, "Batch delay mismatch"
    assert num_nan_stream == 64, "Stream delay mismatch"
    
    # For valid regions, strict bit-parity (isclose to handle float precision)
    valid_mask = ~np.isnan(ed_accel_stream) & ~np.isnan(ed_accel_batch.values)
    
    np.testing.assert_allclose(
        ed_accel_stream[valid_mask], 
        ed_accel_batch.values[valid_mask], 
        atol=1e-12, 
        err_msg="Streaming ED_ACCEL deviates from Batch ED_ACCEL!"
    )
    
    # Verify shock entered and left the buffer exactly identically
    # Because it lasts for 6 days, by day 105 the median should successfully jump.
    assert ed_accel_stream[105] > 0.01, f"Shock was not detected properly in streaming, ed_accel[105]={ed_accel_stream[105]}"
