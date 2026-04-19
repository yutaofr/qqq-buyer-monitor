from scripts.pi_stress_phase4_5_research import Phase45Research


def test_discovery_loop_acceptance():
    research = Phase45Research()
    assert research.run_discovery_loop("cross_sectional_breadth") == "DISCOVERY_ACCEPTED"

def test_discovery_loop_rejection():
    research = Phase45Research()
    assert research.run_discovery_loop("unknown_family") == "DISCOVERY_REJECTED"

def test_taxonomy_evaluation():
    research = Phase45Research()
    assert research.evaluate_taxonomy() == "TRAIN_AS_REDUCED_HIERARCHY"

def test_identifiability_audit():
    research = Phase45Research()
    assert research.identifiability_audit("high") == "NOT_IDENTIFIABLE_ENOUGH_FOR_COMPARISON"
    assert research.identifiability_audit("low") == "IDENTIFIABLE_ONLY_UNDER_REDUCED_COMPLEXITY"
