import pytest

from scripts.pi_stress_phase4_7_research import Phase47Research


@pytest.fixture
def research():
    # Use tmp paths if needed, or just let it use default for this simple mock test
    return Phase47Research(reports_dir="reports", artifacts_dir="artifacts/pi_stress_phase4_7")

def test_gate_confirmation_pack(research):
    result = research.run_gate_confirmation_pack()
    assert result["status"] == "PHASE_4_6_GATE_CLAIMS_CONFIRMED"
    assert "Gate_A_Ordinary_correction_control" in result
    assert "Gate_E_Boundary_robustness" in result
    assert "Mechanism_attribution" in result

def test_ttd_leverage_audit(research):
    result = research.run_ttd_leverage_audit()
    assert "audited_windows" in result
    assert "2020_COVID_crash" in result["audited_windows"]
    assert "2018_Q4_crash" in result["audited_windows"]

def test_veto_blind_spot_audit(research):
    result = research.run_veto_blind_spot_audit()
    assert "non_credit_crash_blind_spot" in result
    assert "lagged_credit_blind_spot" in result
    assert "scenario_10_days_lag" in result["lagged_credit_blind_spot"]

def test_hysteresis_drag_audit(research):
    result = research.run_hysteresis_drag_audit()
    assert "audited_windows" in result
    assert "comparisons" in result

def test_override_design_constraint_study(research):
    result = research.run_override_design_constraint_study()
    assert result["is_override_necessary"] is True
    assert "conditional" in result["override_type"]

def test_final_verdict(research):
    checklist = research.generate_acceptance_checklist()
    result = research.determine_final_verdict(checklist)
    assert result["verdict"] == "ADVANCE_TO_PHASE_5_GOVERNED_PREDEPLOYMENT_RESEARCH"
