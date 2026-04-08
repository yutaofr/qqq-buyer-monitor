from src.research.recovery_hmm.execution_tensor import compute_shadow_weight


def test_shadow_execution_tensor_applies_entropy_and_fdas_multipliers():
    result = compute_shadow_weight(
        state="RECOVERY",
        entropy=0.80,
        fdas_triggered=True,
        preserve_production_floor=True,
    )

    assert result["w_base"] == 1.0
    assert result["m_entropy"] < 1.0
    assert result["m_fdas"] == 0.15
    assert result["w_final"] >= 0.5
