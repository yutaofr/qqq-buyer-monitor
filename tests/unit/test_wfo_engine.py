import pandas as pd
import numpy as np
import pytest
from src.research.wfo_engine import WFOEngine

def mock_backtest(data, params):
    # Returns a dummy execution_df
    df = pd.DataFrame({
        "date": data["observation_date"],
        "close": [100.0] * len(data)
    })
    # Dummy returns based on params
    # Let's say alpha_decay affects performance
    perf = params.get("alpha_decay", 0.05) * 0.01
    df["return_l4"] = [perf] * len(data)
    df["return_base"] = [0.0005] * len(data) # 0.05% daily base
    return df

def test_wfo_engine_rolling_logic():
    # Create 10 years of daily data
    dates = pd.date_range("2010-01-01", periods=3650)
    full_data = pd.DataFrame({
        "observation_date": dates,
        "dummy_val": np.random.randn(3650)
    })
    
    # 7-year IS, 1-year OOS
    wfo = WFOEngine(is_years=7, oos_years=1)
    
    param_grid = [
        {"alpha_decay": 0.01},
        {"alpha_decay": 0.05},
        {"alpha_decay": 0.10}
    ]
    
    results = wfo.run_rolling_optimization(full_data, param_grid, mock_backtest)
    
    assert "combined_oos" in results
    assert "params_history" in results
    
    # With 10 years, 7 IS + 1 OOS = 8 years. 
    # We should have at least 2 OOS windows (Year 8, Year 9).
    # Year 10 is the 10th year.
    assert len(results["params_history"]) >= 2
    
    combined_oos = results["combined_oos"]
    # Check that OOS dates are strictly after the first training period (7 years)
    first_test_date = combined_oos["date"].min()
    assert first_test_date >= pd.Timestamp("2017-01-01")
