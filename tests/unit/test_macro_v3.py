import pandas as pd
from unittest.mock import patch
from src.collector.macro_v3 import fetch_real_yield, fetch_fcf_yield, fetch_earnings_revisions_breadth

def test_fetch_real_yield_success():
    mock_df = pd.DataFrame({"DFII10": [2.0, 2.1, 2.25]})
    
    with patch("src.collector.macro_v3.fetch_fred_data", return_value=mock_df):
        ry = fetch_real_yield()
        assert ry == 2.25

def test_fetch_real_yield_empty_df():
    mock_df = pd.DataFrame()
    
    with patch("src.collector.macro_v3.fetch_fred_data", return_value=mock_df), \
         patch("src.collector.macro_v3.fetch_treasury_yields", return_value={"10Y": None, "3M": None}), \
         patch("src.collector.macro_v3.yf.Ticker") as mock_ticker:
        mock_ticker.return_value.history.return_value = pd.DataFrame()
        ry = fetch_real_yield()
        assert ry is None

def test_fetch_real_yield_no_valid_data():
    mock_df = pd.DataFrame({"DFII10": [None, float("nan")]})
    
    with patch("src.collector.macro_v3.fetch_fred_data", return_value=mock_df), \
         patch("src.collector.macro_v3.fetch_treasury_yields", return_value={"10Y": None, "3M": None}), \
         patch("src.collector.macro_v3.yf.Ticker") as mock_ticker:
        mock_ticker.return_value.history.return_value = pd.DataFrame()
        ry = fetch_real_yield()
        assert ry is None

def test_fetch_real_yield_exception():
    with patch("src.collector.macro_v3.fetch_fred_data", side_effect=Exception("Network Error")), \
         patch("src.collector.macro_v3.fetch_treasury_yields", side_effect=Exception("Network Error")), \
         patch("src.collector.macro_v3.yf.Ticker", side_effect=Exception("Network Error")):
        ry = fetch_real_yield()
        assert ry is None

def test_fetch_fcf_yield_returns_none_without_trusted_source():
    fcf = fetch_fcf_yield("QQQ")
    assert fcf is None

def test_fetch_earnings_revisions_breadth_returns_none_without_trusted_source():
    rev = fetch_earnings_revisions_breadth("QQQ")
    assert rev is None
