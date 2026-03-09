from src.engine.tier0_macro import check_macro_regime, CREDIT_SPREAD_CRISIS_THRESHOLD

def test_check_macro_regime_none():
    assert check_macro_regime(None) is False

def test_check_macro_regime_below_threshold():
    assert check_macro_regime(CREDIT_SPREAD_CRISIS_THRESHOLD - 1.0) is False

def test_check_macro_regime_at_threshold():
    assert check_macro_regime(CREDIT_SPREAD_CRISIS_THRESHOLD) is True

def test_check_macro_regime_above_threshold():
    assert check_macro_regime(CREDIT_SPREAD_CRISIS_THRESHOLD + 100.0) is True

def test_check_erp_regime():
    from src.engine.tier0_macro import check_erp_regime
    
    assert check_erp_regime(None, 4.0) == "Normal"
    assert check_erp_regime(20.0, None) == "Normal"
    
    # PE=20 -> EY = 5%, US10Y = 4% -> ERP = 1.0% -> "Normal"
    assert check_erp_regime(20.0, 4.0) == "Normal"
    
    # PE=25 -> EY = 4%, US10Y = 3.5% -> ERP = 0.5% -> "Defense"
    assert check_erp_regime(25.0, 3.5) == "Defense"
    
    # PE=15 -> EY = 6.66%, US10Y = 1.0% -> ERP = 5.66% -> "Aggressive"
    assert check_erp_regime(15.0, 1.0) == "Aggressive"
