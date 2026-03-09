from src.engine.tier0_macro import check_macro_regime, CREDIT_SPREAD_CRISIS_THRESHOLD

def test_check_macro_regime_none():
    assert check_macro_regime(None) is False

def test_check_macro_regime_below_threshold():
    assert check_macro_regime(CREDIT_SPREAD_CRISIS_THRESHOLD - 1.0) is False

def test_check_macro_regime_at_threshold():
    assert check_macro_regime(CREDIT_SPREAD_CRISIS_THRESHOLD) is True

def test_check_macro_regime_above_threshold():
    assert check_macro_regime(CREDIT_SPREAD_CRISIS_THRESHOLD + 100.0) is True
