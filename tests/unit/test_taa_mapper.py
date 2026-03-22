import pytest
from src.engine.aggregator import get_target_allocation, aggregate
from src.models import AllocationState, Signal, Tier1Result, Tier2Result, SignalDetail
from datetime import date

def test_taa_mapper_values():
    """验证 TAA 映射矩阵的准确性 (SRD 3.0)"""
    # L3 防御测试
    l3_target = get_target_allocation(AllocationState.CASH_FLIGHT)
    assert l3_target.target_cash_pct == 0.60
    assert l3_target.target_qld_pct == 0.0
    assert l3_target.target_beta == 0.40
    
    # 趋势增强测试 (FAST_ACCUMULATE)
    fast_target = get_target_allocation(AllocationState.FAST_ACCUMULATE)
    assert fast_target.target_cash_pct == 0.05
    assert fast_target.target_qld_pct == 0.15
    assert fast_target.target_beta == 1.10

def test_taa_sum_is_100_percent():
    """验证所有状态下的权重总和为 100% (AC-2)"""
    for state in AllocationState:
        target = get_target_allocation(state)
        total = target.target_cash_pct + target.target_qqq_pct + target.target_qld_pct
        assert total == pytest.approx(1.0)

def test_aggregate_output_contains_target_allocation():
    """验证 aggregate 引擎集成输出"""
    t1 = Tier1Result(score=50, drawdown_52w=None, ma200_deviation=None, vix=None, 
                    fear_greed=SignalDetail("F&G", 50, 0, (0,0), False, False), breadth=None)
    t2 = Tier2Result(adjustment=0, put_wall=None, call_wall=None, gamma_flip=None, 
                    support_confirmed=False, support_broken=False, upside_open=False, 
                    gamma_positive=True, gamma_source="yf", put_wall_distance_pct=0.0, call_wall_distance_pct=0.0)
    
    result = aggregate(date.today(), 400.0, t1, t2)
    # 默认应为 BASE_DCA 配置
    assert result.target_allocation.target_cash_pct == 0.10
    assert result.target_allocation.target_beta == 0.90
