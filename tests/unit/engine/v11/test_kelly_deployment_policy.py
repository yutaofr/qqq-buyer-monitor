import pytest
import math

from src.engine.v11.signal.kelly_deployment_policy import KellyDeploymentPolicy

def test_policy_init_defaults():
    # TC-P01
    policy = KellyDeploymentPolicy()
    assert policy.current_state == "DEPLOY_BASE"
    assert policy.evidence == 0.0
    assert policy.kelly_scale == 0.5
    assert policy.erp_weight == 0.4
    assert policy.regime_sharpes["MID_CYCLE"] == 1.0

def test_entropy_barrier():
    # TC-P02
    h = 0.0
    barrier = KellyDeploymentPolicy._entropy_barrier(h, 4)
    assert barrier == 0.0

    h = 0.5
    barrier = KellyDeploymentPolicy._entropy_barrier(h, 4)
    # (0.5 / 0.5) / 4 = 0.25
    assert math.isclose(barrier, 0.25)

def test_decide_holds_state_when_evidence_low():
    # TC-P03
    policy = KellyDeploymentPolicy(initial_state="DEPLOY_BASE", evidence=0.0)
    
    # We want a fraction between 0.25 and 0.6 to get DEPLOY_BASE natively.
    # LATE_CYCLE sharpe = 0.2. With entropy=0.5 -> var=0.25.
    # fraction = (0.2 / 0.25) * 0.5 = 0.4 -> DEPLOY_BASE.
    res1 = policy.decide(
        posteriors={"LATE_CYCLE": 1.0},
        entropy=0.5, # barrier = (0.5/0.5)/4 = 0.25
        readiness_score=0.5,
        value_score=0.5
    )
    assert res1["deployment_state"] == "DEPLOY_BASE"
    assert res1["evidence"] == 0.0
    
    # Now force it to DEPLOY_FAST by setting RECOVERY=1.0 -> fraction = 1.0. 
    # Diff = abs(1.0 - 0.4) = 0.6.
    # If entropy is 0.8, barrier = (0.8 / 0.2) / 4 = 1.0. Thus evidence 0.6 < 1.0. -> HOLDS.
    res2 = policy.decide(
        posteriors={"RECOVERY": 1.0},
        entropy=0.8,
        readiness_score=0.5,
        value_score=0.5
    )
    assert res2["deployment_state"] == "DEPLOY_BASE"
    assert res2["raw_state"] == "DEPLOY_FAST"
    assert res2["action_required"] is False
    expected_evidence = abs(res2["kelly_fraction"] - res1["kelly_fraction"])
    assert math.isclose(res2["evidence"], expected_evidence)

def test_decide_switches_state_when_evidence_high():
    # TC-P04
    policy = KellyDeploymentPolicy(initial_state="DEPLOY_BASE", evidence=0.0)
    # entropy = 0.5 -> barrier = 0.25.
    # prev_fraction = 0.0
    # posteriors -> fraction 1.0 -> diff = 1.0
    res = policy.decide(
        posteriors={"RECOVERY": 1.0},
        entropy=0.5,
        readiness_score=0.5,
        value_score=0.5
    )
    assert res["deployment_state"] == "DEPLOY_FAST"
    assert res["action_required"] is True
    assert res["evidence"] == 0.0

def test_decide_resets_evidence_on_same_raw_state():
    # TC-P05
    policy = KellyDeploymentPolicy(initial_state="DEPLOY_BASE", evidence=0.5)
    # Give LATE_CYCLE so it maps exactly to DEPLOY_BASE.
    # fraction = 0.4 as calculated above.
    res = policy.decide(
        posteriors={"LATE_CYCLE": 1.0},
        entropy=0.5,
        readiness_score=0.5,
        value_score=0.5
    )
    assert res["deployment_state"] == "DEPLOY_BASE"
    assert res["raw_state"] == "DEPLOY_BASE"
    assert res["evidence"] == 0.0

def test_decide_return_keys():
    # TC-P06
    policy = KellyDeploymentPolicy()
    res = policy.decide(
        posteriors={"MID_CYCLE": 1.0},
        entropy=0.0,
        readiness_score=0.2,
        value_score=0.3
    )
    expected_keys = {
        "deployment_state", "raw_state", "deployment_multiplier",
        "readiness_score", "value_score", "action_required",
        "reason", "scores", "barrier", "evidence", "kelly_fraction"
    }
    assert set(res.keys()) == expected_keys
    assert res["scores"] == {"kelly_fraction": res["kelly_fraction"]}

def test_decide_extreme_inputs():
    # TC-P07
    policy = KellyDeploymentPolicy()
    res = policy.decide(
        posteriors={"UNKNOWN": 1.0}, # Edge case
        entropy=-10.0,               # Should clip to 0.0
        readiness_score=20.0,        # Transparency pass
        value_score=-5.0             # Percentile clips to 0.0
    )
    assert res["deployment_state"] == "DEPLOY_PAUSE" # edge = 0.0 -> fraction = 0.0
