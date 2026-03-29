from unittest.mock import MagicMock, patch

import pandas as pd

from src.collector.macro_v3 import fetch_move_index, fetch_net_liquidity


@patch("src.collector.macro_v3.fetch_fred_data")
def test_fetch_net_liquidity_success(mock_fred):
    # Mock data for WALCL (Millions), WTREASMS (Billions), RRPONTSYD (Billions)
    # WALCL: 8000000 Million = 8000 Billion
    # TGA: 500 Billion
    # RRP: 1000 Billion
    # Net: 8000 - 500 - 1000 = 6500 Billion

    dates = pd.date_range(start="2024-01-01", periods=10, freq="W")

    def side_effect(series_id):
        df = pd.DataFrame({
            "observation_date": dates,
            series_id: [1.0]*10
        })
        if series_id == "WALCL":
            df[series_id] = [8000000.0] * 10
        elif series_id == "WDTGAL":
            df[series_id] = [500000.0] * 10
        elif series_id == "RRPONTSYD":
            df[series_id] = [1000.0] * 10
        return df

    mock_fred.side_effect = side_effect

    val, roc = fetch_net_liquidity()
    assert val == 6500.0
    assert roc == 0.0

@patch("yfinance.Ticker")
def test_fetch_move_index_success(mock_ticker):
    mock_instance = MagicMock()
    mock_instance.history.return_value = pd.DataFrame({"Close": [80.5]}, index=[pd.Timestamp("2024-01-01")])
    mock_ticker.return_value = mock_instance

    val = fetch_move_index()
    assert val == 80.5
