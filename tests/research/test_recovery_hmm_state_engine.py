from src.research.recovery_hmm.state_engine import recovery_to_midcycle_probability


def test_recovery_to_midcycle_transition_depends_on_level_and_momentum_decay():
    p_fast_recovery = recovery_to_midcycle_probability(level_score=0.7, decay_score=0.9)
    p_faded_recovery = recovery_to_midcycle_probability(level_score=0.7, decay_score=0.1)

    assert p_fast_recovery < p_faded_recovery
