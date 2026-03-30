import pytest
import pandas as pd
import numpy as np

from src.engine.v11.core.kill_switch import DynamicZScoreKillSwitch
from src.engine.v11.core.t_bill_allocator import SyntheticLiquidityAllocator

def test_dynamic_zscore_kill_switch():
    ks = DynamicZScoreKillSwitch(rolling_window=60, z_threshold=2.5)
    
    # Simulate a history of Term Structure (VIX3M - VIX)
    # Normal days: Contango, TS around +5 to +8, momentum around 0
    np.random.seed(42)
    # We need 3-day momentum to be stable. So we make the TS itself very stable.
    normal_ts = np.random.normal(6.0, 0.5, 60)
    
    # Crisis hits: Deep backwardation (drop over several days)
    crisis_ts = np.array([4.0, 0.0, -5.0, -10.0, -15.0])
    
    # Recovery: Violent reversion
    # t-3: -15, t: -1. Momentum = +14.0
    recovery_ts = np.array([-12.0, -8.0, -1.0])
    
    ts_series = pd.Series(np.concatenate([normal_ts, crisis_ts, recovery_ts]))
    
    # VIX 1M series (must be dropping at the end for kill switch to fire)
    vix_normal = np.random.normal(15, 2, 60)
    vix_crisis = np.array([30, 40, 50, 60, 80])
    vix_recovery = np.array([75, 70, 65]) # dropping
    vix_series = pd.Series(np.concatenate([vix_normal, vix_crisis, vix_recovery]))
    
    # Evaluate at the peak of crisis (VIX=80, momentum positive) -> Should be False
    idx_peak = 64
    is_resurrected_peak = ks.evaluate_resurrection(
        is_blackout=True, 
        ts_series=ts_series, 
        vix_1m=vix_series, 
        current_idx=idx_peak
    )
    assert not is_resurrected_peak, "Should not trigger when VIX is still rising"
    
    # Evaluate at recovery (VIX=65, dropping, TS violently reverting) -> Should be True
    idx_recovery = 67
    is_resurrected_recovery = ks.evaluate_resurrection(
        is_blackout=True, 
        ts_series=ts_series, 
        vix_1m=vix_series, 
        current_idx=idx_recovery
    )
    assert is_resurrected_recovery, "Should trigger on violent TS reversion and dropping VIX"
    
    # Evaluate without blackout -> Should be False
    is_resurrected_no_blackout = ks.evaluate_resurrection(
        is_blackout=False, 
        ts_series=ts_series, 
        vix_1m=vix_series, 
        current_idx=idx_recovery
    )
    assert not is_resurrected_no_blackout, "Should only trigger during Blackout"

def test_synthetic_liquidity_allocator():
    allocator = SyntheticLiquidityAllocator(nq_multiplier=20, margin_buffer=0.30)
    
    t_bill_value = 1000000.0 # $1M in T-Bills
    target_exposure = 500000.0 # Want $500k in QQQ equivalent
    nq_price = 15000.0 # 1 NQ contract = $300,000 notional
    
    # Scenario 1: Normal VIX (20), standard margin (18k per contract)
    result_normal = allocator.calculate_futures_order(
        t_bill_value=t_bill_value,
        target_notional_exposure=target_exposure,
        nq_current_price=nq_price,
        current_vix=20.0,
        base_im_per_contract=18000.0
    )
    
    assert result_normal["action"] == "BUY_NQ_FUTURES"
    assert result_normal["contracts"] == 1 # 500k / 300k = 1.66 -> 1 contract
    # IM = 18000 * (1 + 20/100) = 21600
    assert result_normal["margin_locked"] == 21600.0
    
    # Scenario 2: Extreme Crisis VIX (80), Margin expansion, Collateral Haircut
    target_exposure_huge = 8000000.0 # Want $8M exposure
    result_crisis = allocator.calculate_futures_order(
        t_bill_value=t_bill_value,
        target_notional_exposure=target_exposure_huge,
        nq_current_price=nq_price,
        current_vix=80.0,
        base_im_per_contract=18000.0
    )
    
    # Analysis in crisis:
    # Haircut = 5% -> Usable collateral = 950,000
    # Available for margin (30% buffer) = 950,000 * 0.7 = 665,000
    # Dynamic IM = 18000 * (1 + 80/100) = 32400 per contract
    # Max contracts allowed = floor(665,000 / 32400) = 20
    # Requested contracts = 8M / 300k = 26
    # Should be capped at 20.
    
    assert result_crisis["action"] == "BUY_NQ_FUTURES"
    assert result_crisis["contracts"] == 20
    assert result_crisis["margin_locked"] == 20 * 32400.0
