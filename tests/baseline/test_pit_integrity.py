import pandas as pd
import pytest
from unittest.mock import MagicMock
from src.engine.baseline.data_loader import load_all_baseline_data

@pytest.fixture
def mock_macro(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("src.engine.baseline.data_loader.fetch_fred_data", mock)
    return mock

def test_pit_no_lookahead(mock_macro):
    """
    Verify that monthly data (IPMAN) is NOT used before its effective date.
    Observation Date: 2020-01-01
    Effective Date (22 BDays): ~2020-02-03
    """
    # 1. Create a monthly observation
    ipman_raw = pd.DataFrame({
        "observation_date": ["2020-01-01"],
        "IPMAN": [55.0]
    })
    
    # 2. Create daily price/vix data that spans the gap
    vix_raw = pd.DataFrame({
        "observation_date": pd.date_range("2019-12-01", "2020-03-01", freq="B"),
        "VIXCLS": 20.0
    })
    
    def side_effect(series_id, **kwargs):
        if series_id == "IPMAN": return ipman_raw
        if series_id == "VIXCLS": return vix_raw
        return None
    
    mock_macro.side_effect = side_effect
    
    # 3. Load combined data
    df = load_all_baseline_data()
    
    # 4. Critical Checks
    # On 2020-01-02 (day after observation), IPMAN must be NaN
    assert pd.isna(df.loc["2020-01-02", "IPMAN"]), "Monthly data leaked on observation date+1"
    
    # On 2020-01-20 (still before 22 BDays), IPMAN must be NaN
    assert pd.isna(df.loc["2020-01-20", "IPMAN"]), "Monthly data leaked before release lag"
    
    # On 2020-02-04 (after release lag), IPMAN should be available
    assert df.loc["2020-02-04", "IPMAN"] == 55.0, "Monthly data not available after release lag"
