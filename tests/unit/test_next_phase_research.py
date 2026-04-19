import json
import os

ARTIFACTS_DIR = "artifacts/next_phase"

def test_final_verdict_schema():
    with open(os.path.join(ARTIFACTS_DIR, "final_verdict.json")) as f:
        data = json.load(f)
    assert data["final_verdict"] == "RETURN_TO_PHASE_5_WITH_NARROWED_SCOPE_AND_PARTIAL_TRUST"
    assert "rationale" in data
    assert not data["next_phase_acceptance_checklist"]["OVF1"]
    assert data["next_phase_acceptance_checklist"]["MP1"]

def test_model_layer_survivability_ceiling():
    with open(os.path.join(ARTIFACTS_DIR, "model_layer_survivability_ceiling.json")) as f:
        data = json.load(f)
    assert data["overall_ceiling_verdict"] in [
        "MODEL_LAYER_HAS_MEANINGFUL_REMAINING_HEADROOM",
        "MODEL_LAYER_HAS_LIMITED_HEADROOM_POLICY_LAYER_NEEDED",
        "MODEL_LAYER_HEADROOM_IS_MINIMAL_EXECUTION_LAYER_DOMINATES"
    ]
