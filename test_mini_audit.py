import os
import pandas as pd
import json
from src.backtest import run_v11_audit

# Create dummy data
os.makedirs("data", exist_ok=True)
dates = pd.date_range("2024-01-01", periods=100)
import numpy as np
np.random.seed(42)
macro_data = pd.DataFrame({
    "observation_date": dates,
    "effective_date": dates,
    "credit_spread_bps": 300 + np.random.randn(100) * 10,
    "real_yield_10y_pct": 0.01 + np.random.randn(100) * 0.001,
    "net_liquidity_usd_bn": 6000 + np.random.randn(100) * 100,
    "treasury_vol_21d": 10 + np.random.randn(100) * 2,
    "copper_gold_ratio": 0.2 + np.random.randn(100) * 0.01,
    "breakeven_10y": 0.02 + np.random.randn(100) * 0.002,
    "core_capex_mm": 100 + np.random.randn(100) * 5,
    "usdjpy": 150 + np.random.randn(100) * 2,
    "erp_ttm_pct": 0.05 + np.random.randn(100) * 0.005
})
macro_data.to_csv("data/macro_historical_dump_test.csv", index=False)

regime_data = pd.DataFrame({
    "observation_date": dates,
    "regime": ["MID_CYCLE"]*100
})
regime_data.to_csv("data/v11_poc_phase1_results_test.csv", index=False)

price_data = pd.DataFrame({
    "Close": [100.0 + i*0.1 for i in range(100)],
    "Volume": [1000]*100
}, index=dates)
price_data.to_csv("data/qqq_history_cache.csv")

# Run audit
results = run_v11_audit(
    dataset_path="data/macro_historical_dump_test.csv",
    regime_path="data/v11_poc_phase1_results_test.csv",
    evaluation_start="2024-03-01",
    artifact_dir="artifacts/v12_audit_test"
)
print("Audit completed successfully")
