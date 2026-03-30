from src.engine.v11.signal.deployment_policy import ProbabilisticDeploymentPolicy


def test_deployment_policy_is_independent_from_beta_and_can_fast_deploy_in_reversal():
    policy = ProbabilisticDeploymentPolicy(initial_state="DEPLOY_BASE")

    decision = policy.decide(
        posteriors={
            "MID_CYCLE": 0.10,
            "BUST": 0.20,
            "CAPITULATION": 0.35,
            "RECOVERY": 0.25,
            "LATE_CYCLE": 0.10,
        },
        entropy=0.22,
        readiness_score=0.88,
        value_score=0.92,
    )

    assert decision["deployment_state"] == "DEPLOY_FAST"
    assert decision["action_required"] is True


def test_deployment_policy_holds_under_high_entropy_noise():
    policy = ProbabilisticDeploymentPolicy(initial_state="DEPLOY_BASE")

    decision = policy.decide(
        posteriors={
            "MID_CYCLE": 0.24,
            "BUST": 0.20,
            "CAPITULATION": 0.18,
            "RECOVERY": 0.18,
            "LATE_CYCLE": 0.20,
        },
        entropy=0.98,
        readiness_score=0.52,
        value_score=0.51,
    )

    assert decision["deployment_state"] == "DEPLOY_BASE"
    assert decision["action_required"] is False
