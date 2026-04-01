import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from src.collector import macro

def test_fetch_fred_api_with_vintage_extracts_initial_releases():
    # Mock response data representing multiple vintages for the same observation date
    mock_response = {
        "observations": [
            # Obs date 2024-01-01, first release on 2024-01-05
            {"date": "2024-01-01", "realtime_start": "2024-01-05", "value": "3.5"},
            # Obs date 2024-01-01, second release (revision) on 2024-02-05
            {"date": "2024-01-01", "realtime_start": "2024-02-05", "value": "3.4"},
            # Obs date 2024-02-01, first release on 2024-02-05
            {"date": "2024-02-01", "realtime_start": "2024-02-05", "value": "4.0"},
        ]
    }

    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response
        
        # Test the new vintage=True parameter (which we haven't implemented yet)
        with patch.dict("os.environ", {"FRED_API_KEY": "fake_key"}):
            df = macro.fetch_fred_api("UNRATE", vintage=True)

    assert df is not None
    assert len(df) == 2
    assert "published_date" in df.columns
    
    # Should keep the EARLIEST realtime_start for each date
    jan_row = df[df["observation_date"] == "2024-01-01"].iloc[0]
    assert jan_row["published_date"] == "2024-01-05"
    assert jan_row["UNRATE"] == 3.5

    feb_row = df[df["observation_date"] == "2024-02-01"].iloc[0]
    assert feb_row["published_date"] == "2024-02-05"
    assert feb_row["UNRATE"] == 4.0
