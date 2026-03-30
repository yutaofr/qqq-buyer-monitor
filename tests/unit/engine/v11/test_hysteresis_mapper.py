import pytest

from src.engine.v11.signal.hysteresis_exposure_mapper import HysteresisExposureMapper

def test_hysteresis_deadband():
    mapper = HysteresisExposureMapper(initial_state="QLD", settlement_t_plus=0) # 无冷却期，专测死区
    
    # 1. Normal to Warning (Cross > 0.40)
    sig1 = mapper.get_signal(p_bust=0.45, is_kill_switch_active=False)
    assert sig1["target_exposure"] == "QQQ"
    assert sig1["action_required"] is True
    
    # 2. Whipsaw test: Drops slightly to 0.35 (should stay QQQ because threshold is <0.20)
    sig2 = mapper.get_signal(p_bust=0.35, is_kill_switch_active=False)
    assert sig2["target_exposure"] == "QQQ"
    assert sig2["action_required"] is False # No action
    
    # 3. Warning to Normal (Drops < 0.20)
    sig3 = mapper.get_signal(p_bust=0.15, is_kill_switch_active=False)
    assert sig3["target_exposure"] == "QLD"
    assert sig3["action_required"] is True

    # 4. Normal to Blackout (Rapid spike to 0.80)
    # 0.80 > 0.40 -> QQQ. Wait, if it's currently QLD, the logic checks >0.40 first and drops to QQQ.
    # In reality, it takes one tick to drop to QQQ, and the next tick to drop to CASH if it's still 0.80.
    sig4 = mapper.get_signal(p_bust=0.80, is_kill_switch_active=False)
    assert sig4["target_exposure"] == "QQQ" # It steps down 1 gear per tick for safety
    sig5 = mapper.get_signal(p_bust=0.80, is_kill_switch_active=False)
    assert sig5["target_exposure"] == "CASH"

def test_settlement_lock():
    mapper = HysteresisExposureMapper(initial_state="QLD", settlement_t_plus=1)
    
    # Tick 1: Action triggers lock
    sig1 = mapper.get_signal(p_bust=0.50, is_kill_switch_active=False)
    assert sig1["target_exposure"] == "QQQ"
    assert mapper.cooldown_days_remaining == 1
    
    # Tick 2: Try to act while locked
    sig2 = mapper.get_signal(p_bust=0.80, is_kill_switch_active=False)
    assert sig2["target_exposure"] == "QQQ" # Stuck in QQQ due to lock
    assert "SETTLEMENT_LOCKED" in sig2["reason"]
    
    # Tick 3: Cooldown expires
    mapper.tick_cooldown()
    sig3 = mapper.get_signal(p_bust=0.80, is_kill_switch_active=False)
    assert sig3["target_exposure"] == "CASH" # Now it can move

def test_resurrection_kill_switch():
    mapper = HysteresisExposureMapper(initial_state="CASH", settlement_t_plus=1)
    
    # 1. Kill-Switch fires!
    sig1 = mapper.get_signal(p_bust=0.99, is_kill_switch_active=True)
    assert sig1["target_exposure"] == "QLD"
    assert "RESURRECTION" in sig1["reason"]
    assert mapper.cooldown_days_remaining == 30 # 30 day immunity
    
    # 2. Verify immunity against high P(BUST)
    sig2 = mapper.get_signal(p_bust=0.99, is_kill_switch_active=False)
    assert sig2["target_exposure"] == "QLD"
    assert "SETTLEMENT_LOCKED" in sig2["reason"]
