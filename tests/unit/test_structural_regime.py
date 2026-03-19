from src.engine.tier0_macro import (
    CREDIT_SPREAD_CRISIS_THRESHOLD,
    assess_structural_regime,
    check_macro_regime,
)


def test_structural_regime_euphoric():
    assert assess_structural_regime(credit_spread=180.0, erp=6.0) == "EUPHORIC"


def test_structural_regime_rich_tightening():
    assert assess_structural_regime(credit_spread=320.0, erp=1.5) == "RICH_TIGHTENING"


def test_structural_regime_neutral():
    assert assess_structural_regime(credit_spread=260.0, erp=3.2) == "NEUTRAL"


def test_structural_regime_transition_stress():
    assert assess_structural_regime(credit_spread=420.0, erp=3.5) == "TRANSITION_STRESS"


def test_structural_regime_crisis():
    assert assess_structural_regime(credit_spread=560.0, erp=5.0) == "CRISIS"


def test_macro_veto_maps_only_to_crisis():
    assert check_macro_regime(CREDIT_SPREAD_CRISIS_THRESHOLD - 1.0, erp=5.0) is False
    assert check_macro_regime(CREDIT_SPREAD_CRISIS_THRESHOLD, erp=5.0) is True
