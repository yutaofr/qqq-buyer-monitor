import pytest
import pandas as pd
from datetime import date
from src.collector.historical_macro_seeder import HistoricalMacroSeeder

def test_seeder_calculates_correct_accel_for_2022():
    """验证加载器能为 2022 年特定日期计算出准确的利差加速度"""
    # 模拟 2022 年一段信用利差走阔的数据
    # 2022-05-01: 3.5, 2022-05-15: 4.2 (涨幅 20% > 15%)
    mock_data = pd.DataFrame({
        "observation_date": pd.date_range(start="2022-04-20", periods=30),
        "BAMLH0A0HYM2": [3.5] * 10 + [3.6, 3.7, 3.8, 3.9, 4.0, 4.1, 4.2] + [4.2] * 13
    })
    
    seeder = HistoricalMacroSeeder(mock_df=mock_data)
    
    # 检查 2022-05-06 左右的加速度 (假设 window=10)
    target_date = date(2022, 5, 6)
    features = seeder.get_features_for_date(target_date)
    
    assert "credit_accel" in features
    assert features["credit_accel"] > 15.0
    assert features["credit_accel"] == pytest.approx(20.0, abs=0.5)

def test_seeder_handles_missing_dates():
    """验证加载器能平滑处理缺失日期（使用 ffill）"""
    mock_data = pd.DataFrame({
        "observation_date": [pd.Timestamp("2022-01-01"), pd.Timestamp("2022-01-05")],
        "BAMLH0A0HYM2": [3.0, 3.5]
    })
    seeder = HistoricalMacroSeeder(mock_df=mock_data)
    
    # 请求 2022-01-03 (中间缺失)
    features = seeder.get_features_for_date(date(2022, 1, 3))
    assert features["credit_spread"] == 3.0 # 预期前向填充
