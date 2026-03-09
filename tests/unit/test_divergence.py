import pandas as pd
import numpy as np
from src.engine.divergence import _calculate_rsi, check_divergences

def test_calculate_rsi():
    # Generate a dummy series
    np.random.seed(42)
    # 30 days of synthetic prices
    prices = pd.Series([100 + i for i in range(15)] + [115 - i for i in range(15)])
    rsi = _calculate_rsi(prices, period=14)
    
    assert len(rsi) == 30
    assert pd.isna(rsi.iloc[0]) # First few should be NaN depending on window
    
    # We just ensure it outputs valid values eventually
    valid_rsi = rsi.dropna()
    assert len(valid_rsi) > 0
    assert all((valid_rsi >= 0) & (valid_rsi <= 100))

def test_check_divergences_no_history():
    res = check_divergences(100.0, 20.0, 0.5, None)
    assert res["bonus_score"] == 0
    assert not res["price_breadth"]
    
    # Or history too short
    df = pd.DataFrame({"price": [100.0] * 5})
    res = check_divergences(100.0, 20.0, 0.5, df)
    assert res["bonus_score"] == 0

def test_check_divergences_no_new_low():
    # Price is 150, hist_min is 100
    df = pd.DataFrame({
        "price": [100.0] * 20,
        "vix": [20.0] * 20,
        "breadth": [0.5] * 20
    })
    res = check_divergences(150.0, 20.0, 0.5, df)
    assert res["bonus_score"] == 0

def test_check_divergences_all_divergences():
    # Historic low was 100, VIX 30, Breadth 0.2, RSI low
    # Current is 95 (new low), VIX 25 (lower = div), Breadth 0.4 (higher = div), RSI higher
    
    # Create 30 days of data. Price drops from 150 to 100, then bounces to 120, then drops to 105
    prices = np.concatenate([np.linspace(150, 100, 15), np.linspace(100, 120, 5), np.linspace(120, 105, 10)])
    
    # We just need price to be recorded in df, and min price will be exactly found at idx 14
    df = pd.DataFrame({
        "price": prices,
        "vix": [20.0] * 14 + [30.0] + [25.0] * 15, # VIX at min price (idx 14) is 30
        "breadth": [0.5] * 14 + [0.2] + [0.4] * 15 # Breadth at min price is 0.2
    })
    
    # Current values
    current_price = 95.0 # Lower than hist min (100.0)
    current_vix = 25.0 # Lower than hist VIX at min (30.0) -> Div
    current_breadth = 0.4 # Higher than hist breadth at min (0.2) -> Div
    
    # For RSI, the synthetic series might naturally create a divergence if the second drop is less steep
    # Or we can just mock _calculate_rsi if dealing with exact RSI values is too flaky,
    # but the current logic uses df['price'] to calculate RSI inside.
    res = check_divergences(current_price, current_vix, current_breadth, df)
    
    assert res["price_breadth"] is True
    assert res["price_vix"] is True
    
    # Bonus score: 15 (breadth) + 10 (vix) = 25. RSI might be 5 if it triggers, so 25 or 30
    assert res["bonus_score"] >= 25

def test_check_divergences_exception_handling():
    # Give a dataframe with missing columns to trigger exception in try-except block
    df = pd.DataFrame({"wrong_col": [1, 2, 3]})
    
    # Should safely return
    res = check_divergences(100.0, 20.0, 0.5, df)
    # Wait, check_divergences checks len(df) < 15 before try block, so make it length 20
    df = pd.DataFrame({"wrong_col": [1] * 20})
    res = check_divergences(100.0, 20.0, 0.5, df)
    
    assert res["bonus_score"] == 0

def test_check_divergences_price_revision():
    # Length > 15
    prices = np.concatenate([np.linspace(150, 100, 15), [110.0, 105.0]])
    df = pd.DataFrame({
        "price": prices,
        "vix": [20.0] * 17,
        "breadth": [0.5] * 17
    })
    
    # Under low (100.0), Revision Breadth is 60.0 (>50%)
    res = check_divergences(
        current_price=95.0, 
        current_vix=25.0, 
        current_breadth=0.5, 
        df=df,
        current_revision_breadth=60.0
    )
    
    assert res["price_revision"] is True
    # Initial is 20 points
    assert res["bonus_score"] >= 20
    
    # Under low, Revision Breadth is 40.0 (<50%) -> No divergence
    res2 = check_divergences(
        current_price=95.0, 
        current_vix=25.0, 
        current_breadth=0.5, 
        df=df,
        current_revision_breadth=40.0
    )
    assert res2["price_revision"] is False
