import pandas as pd
from unittest.mock import patch
from src.collector.macro_v3 import fetch_us10y, fetch_fcf_yield, fetch_earnings_revisions_breadth

def test_fetch_us10y_success():
    mock_df = pd.DataFrame({"DGS10": [4.0, 4.1, 4.25]})
    
    with patch("src.collector.macro_v3.fetch_fred_csv", return_value=mock_df):
        us10y = fetch_us10y()
        assert us10y == 4.25

def test_fetch_us10y_empty_df():
    mock_df = pd.DataFrame()
    
    with patch("src.collector.macro_v3.fetch_fred_csv", return_value=mock_df), \
         patch("src.collector.macro_v3.yf.Ticker") as mock_ticker:
        mock_ticker.return_value.history.return_value = pd.DataFrame()
        us10y = fetch_us10y()
        assert us10y is None

def test_fetch_us10y_no_valid_data():
    mock_df = pd.DataFrame({"DGS10": [None, float("nan")]})
    
    with patch("src.collector.macro_v3.fetch_fred_csv", return_value=mock_df), \
         patch("src.collector.macro_v3.yf.Ticker") as mock_ticker:
        mock_ticker.return_value.history.return_value = pd.DataFrame()
        us10y = fetch_us10y()
        assert us10y is None

def test_fetch_us10y_exception():
    with patch("src.collector.macro_v3.fetch_fred_csv", side_effect=Exception("Network Error")), \
         patch("src.collector.macro_v3.yf.Ticker", side_effect=Exception("Network Error")):
        us10y = fetch_us10y()
        assert us10y is None

def test_fetch_fcf_yield():
    fcf = fetch_fcf_yield("QQQ")
    assert isinstance(fcf, float)
    assert 2.5 <= fcf <= 5.0

def test_fetch_earnings_revisions_breadth():
    rev = fetch_earnings_revisions_breadth("QQQ")
    assert isinstance(rev, float)
    assert 35.0 <= rev <= 65.0
