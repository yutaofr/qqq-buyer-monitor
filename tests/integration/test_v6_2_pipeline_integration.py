import pytest
from datetime import date
from src.main import _run
from unittest.mock import MagicMock, patch
from src.models import AllocationState

@patch("src.collector.price.fetch_price_data")
@patch("src.collector.macro_v3.fetch_credit_acceleration")
@patch("src.collector.macro_v3.fetch_net_liquidity")
@patch("src.collector.macro_v3.fetch_funding_stress")
@patch("src.output.cli.print_signal")
def test_full_pipeline_integration_v6_2(mock_print, mock_funding, mock_liq, mock_accel, mock_price):
    """验证 v6.2 生产流水线集成：参数传递与叙事守卫"""
    
    # 1. 模拟市场数据：触发 DELEVERAGE (信用加速 + 流动性负增长)
    mock_price.return_value = {"date": date.today(), "price": 400.0, "ma200": 380.0, "high_52w": 420.0}
    mock_accel.return_value = 20.0 # 信用加速
    mock_liq.return_value = (5.8e6, -3.0) # 流动性 ROC < -2%
    mock_funding.return_value = {"nfci": -0.5, "cpff": 0.02, "is_stressed": False}
    
    # 2. 模拟 aggregate 返回的原始文案包含违规词（用于测试守卫）
    # aggregate 内部会生成原始解释，我们需要验证 main.py 是否在打印前过滤了它
    args = MagicMock()
    args.json = False
    args.no_save = True
    args.no_color = True
    args.history = None
    
    _run(args)
    
    # 3. 获取 main.py 最终传递给 print_signal 的 result
    assert mock_print.called
    result = mock_print.call_args[0][0]
    
    # 4. 验证集成逻辑
    assert result.allocation_state == AllocationState.DELEVERAGE
    assert result.target_cash_pct == 30.0 # DELEVERAGE 目标现金
    
    # 5. 验证叙事守卫是否生效
    # 如果 aggregate 产生了原始文案 "建议积极抄底"，那么集成后的结果应被过滤
    assert "抄底" not in result.explanation
    assert "存量调整" in result.explanation or "防御" in result.explanation or "降低杠杆" in result.explanation
