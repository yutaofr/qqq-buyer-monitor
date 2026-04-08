from src.research.recovery_hmm.contract import RecoveryHmmShadowContract


def test_recovery_hmm_shadow_contract_does_not_mutate_production_defaults():
    contract = RecoveryHmmShadowContract()

    assert contract.shadow_only is True
    assert contract.production_beta_floor == 0.5
    assert contract.may_modify_live_target_beta is False
