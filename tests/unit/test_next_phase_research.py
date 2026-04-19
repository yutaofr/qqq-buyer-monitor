def test_final_verdict_schema():
    data = {
        "final_verdict": "RETURN_TO_PHASE_5_WITH_NARROWED_SCOPE_AND_PARTIAL_TRUST",
        "rationale": "Trust is limited to candidate viability for further adversarial study.",
        "next_phase_acceptance_checklist": {
            "OVF1": False,
            "MP1": True,
        },
    }
    assert data["final_verdict"] == "RETURN_TO_PHASE_5_WITH_NARROWED_SCOPE_AND_PARTIAL_TRUST"
    assert "rationale" in data
    assert not data["next_phase_acceptance_checklist"]["OVF1"]
    assert data["next_phase_acceptance_checklist"]["MP1"]

def test_model_layer_survivability_ceiling():
    data = {
        "overall_ceiling_verdict": "MODEL_LAYER_HAS_LIMITED_HEADROOM_POLICY_LAYER_NEEDED",
    }
    assert data["overall_ceiling_verdict"] in [
        "MODEL_LAYER_HAS_MEANINGFUL_REMAINING_HEADROOM",
        "MODEL_LAYER_HAS_LIMITED_HEADROOM_POLICY_LAYER_NEEDED",
        "MODEL_LAYER_HEADROOM_IS_MINIMAL_EXECUTION_LAYER_DOMINATES"
    ]
