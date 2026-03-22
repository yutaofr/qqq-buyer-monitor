import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from src.collector.macro_v3 import fetch_credit_acceleration, fetch_funding_stress

def test_credit_acceleration_logic():
    """验证信用利差加速度计算逻辑"""
    # 模拟 10 天的利差数据
    # 第1天: 3.0, 第10天: 3.5 (涨幅 16.6% > 15%)
    mock_series = pd.DataFrame({
        "observation_date": pd.date_range(start="2026-03-01", periods=10),
        "BAMLH0A0HYM2": [3.0, 3.05, 3.1, 3.15, 3.2, 3.25, 3.3, 3.35, 3.4, 3.5]
    })
    
    with patch("src.collector.macro_v3.fetch_fred_data", return_value=mock_series):
        accel_pct = fetch_credit_acceleration(window=10)
        # (3.5 - 3.0) / 3.0 = 16.67%
        assert accel_pct == pytest.approx(16.67, abs=0.1)

def test_funding_stress_logic():
    """验证融资压力指标抓取"""
    # 模拟 Chicago Fed NFCI 和 CPFF
    with patch("src.collector.macro_v3.fetch_fred_api") as mock_fred:
        # 模拟 NFCI = 0.1 (正值代表收紧)
        mock_nfci = pd.DataFrame({"observation_date": ["2026-03-10"], "NFCI": [0.1]})
        # 模拟 CPFF = 0.05
        mock_cpff = pd.DataFrame({"observation_date": ["2026-03-10"], "CPFF": [0.05]})
        
        mock_fred.side_effect = [mock_nfci, mock_cpff]
        
        stress = fetch_funding_stress()
        assert stress["nfci"] == 0.1
        assert stress["cpff"] == 0.05
        assert stress["is_stressed"] is True # 因为 NFCI > 0
