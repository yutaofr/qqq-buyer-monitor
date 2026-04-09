from src.engine.v11.core.entropy_controller import EntropyController
from src.engine.v11.core.execution_pipeline import compute_effective_entropy
from src.engine.v11.signal.regime_stabilizer import RegimeStabilizer


def test_reproduce_entropy_miscalibration_at_high_confidence():
    """
    Audit Finding: H remains near 0.83 even when conviction is 96%.
    Current Goal: Reproduce this 'Red' state.
    """
    ctrl = EntropyController()
    # 96% BUST, 4% distributed among others
    probs = {"MID_CYCLE": 0.0133, "LATE_CYCLE": 0.0133, "BUST": 0.96, "RECOVERY": 0.0134}

    h_norm = ctrl.calculate_normalized_entropy(probs)

    # Mathematical expectation for Shannon Entropy (N=4) at 96% is ~0.154
    # The audit says it's 0.83 in the 'Trace'. This might be due to effective_entropy.
    print(f"DEBUG: Normalized Shannon Entropy = {h_norm:.4f}")

    # If the audit says it stayed at 0.83, let's see what effective_entropy does if Q=0.5
    eff_h = compute_effective_entropy(posterior_entropy=h_norm, quality_score=0.5)
    print(f"DEBUG: Effective Entropy (Q=0.5) = {eff_h:.4f}")

    # We want a fix where high confidence (96%) yields low H, regardless of Q being slightly lower.
    # V14.6 Fix: Entropy should be low (0.16) when conviction is high (96%)
    assert eff_h < 0.25

def test_reproduce_recovery_suppression_barrier():
    """
    Audit Finding: Recovery transition barrier is too high (1.4+).
    """
    # Current entropy in audit is ~0.85
    entropy = 0.85
    stabilizer = RegimeStabilizer(initial_regime="BUST")

    # Calculate barrier
    barrier = stabilizer._entropy_barrier(entropy, n_states=4)
    print(f"DEBUG: Barrier at H=0.85 = {barrier:.4f}")

    # Findings: Barrier is 1.417.
    # To switch, we need 1.41 evidence.
    # If BUST=0.6, RECOVERY=0.4, daily evidence = 0.4 - 0.6 is negative?
    # No, evidence += max(0, challenger - current).
    # If challenger=RECOVERY(0.35) and current=BUST(0.3), daily = 0.05.
    # 1.41 / 0.05 = 28 days to switch! (Deadly delay)

    assert barrier > 1.0 # This reproduces the 'Red' state where switching is almost impossible.

def test_reproduce_beta_flatline_damping():
    """
    Audit Finding: Target Beta stays at 0.6 even if Raw is 1.0.
    """
    ctrl = EntropyController()
    probs = {"MID_CYCLE": 0.0133, "LATE_CYCLE": 0.0133, "BUST": 0.96, "RECOVERY": 0.0134}
    h_norm = ctrl.calculate_normalized_entropy(probs) # Now conviction-adjusted (~0.09)
    raw_beta = 1.0 # Significant re-risking signal

    # In v14.6, with H_norm ~ 0.09:
    # confidence = exp(-0.6 * (0.09 * ln(4))^2) = ~0.99
    # Haircut = 0.5 + 0.5 * 0.99 = 0.995

    # Surplus = 1.0 - 0.5 = 0.5
    # multiplier = exp(-0.6 * (0.85 * ln(4))^2) = ~0.435
    # Haircut = 0.5 + 0.5 * 0.435 = 0.717

    final_beta = ctrl.apply_haircut(raw_beta, h_norm, state_count=4)
    print(f"DEBUG: Haircut Beta (Raw=1.0, H=0.85) = {final_beta:.4f}")

    # In v14.6, we want the haircut to be less aggressive when entropy is conviction-adjusted.
    # 0.71 was the old 'Red' value. We expect it to be higher (closer to 1.0) now.
    assert final_beta > 0.8

def test_reproduce_recovery_barrier_scaling():
    """
    Verify Fix 1C: Barrier Scale should apply when release is hinted.
    """
    stabilizer = RegimeStabilizer(initial_regime="BUST")
    entropy = 0.85
    base_barrier = stabilizer._entropy_barrier(entropy, n_states=4) # 1.4167

    # Simulate a realistic release hint from PriceTopology
    release_hint = {
        "topology_regime": "RECOVERY",
        "topology_confidence": 0.25,
        "repair_persistence": 0.35,
        "recovery_impulse": 0.30,
        "damage_memory": 0.40,
        "transition_intensity": 0.70
    }

    # We need to compute the challenger and scaling by calling _resolve_release_candidate
    probs = {"BUST": 0.4, "RECOVERY": 0.6} # Dominant challenger
    res = stabilizer._resolve_release_candidate(
        normalized=probs,
        current_regime="BUST",
        entropy=entropy,
        release_hint=release_hint
    )
    assert res is not None

    scaled_barrier = stabilizer._apply_barrier_scaling(
        base_barrier,
        scaling_factor=res["barrier_scale"],
        is_recovery=True
    )

    # Red state: scaled_barrier was ~0.35.
    # Green goal: scaled_barrier < 0.2 (due to 0.4x discount on top of ~0.3 scaling)
    print(f"DEBUG: Scaled Barrier at H=0.85 with hint = {scaled_barrier:.4f}")
    assert scaled_barrier < 0.2

def test_reproduce_regime_chattering():
    """
    Verify Fix 5A & 5B: Prevent Chattering.
    """
    stabilizer = RegimeStabilizer(initial_regime="MID_CYCLE")

    # Simulate noise: MID=0.55, LATE=0.45, H=0.6
    entropy = 0.6
    probs = {"MID_CYCLE": 0.55, "LATE_CYCLE": 0.45, "BUST": 0.0, "RECOVERY": 0.0}

    # Red state: barrier for H=0.6 is 0.375.
    # If delta is 0.1 per day, it takes 4 days.
    # In v14.6, we want a minimum barrier of 0.5 for MID/LATE.

    # 1. First run, no flip
    res = stabilizer.update(posteriors=probs, entropy=entropy)
    assert res["stable_regime"] == "MID_CYCLE"

    # 2. Simulate 8 days of noise where LATE > MID slightly
    probs_late = {"MID_CYCLE": 0.45, "LATE_CYCLE": 0.55, "BUST": 0.0, "RECOVERY": 0.0}
    # delta = 0.55 - 0.45 = 0.1.

    for d in range(8):
        res = stabilizer.update(posteriors=probs_late, entropy=entropy)
        # We expect no flip for at least 8 days with delta=0.1
        assert res["stable_regime"] == "MID_CYCLE", f"Flipped too early on day {d+1}"

    # Day 9: evidence will cross 0.5 (approx 0.51)
    res = stabilizer.update(posteriors=probs_late, entropy=entropy)

    print(f"DEBUG: Stable regime after 9 days of moderate noise = {res['stable_regime']}")
    # In Green state, we want them to hold for ~10 days.
    # On Day 9 it might flip or not depending on the decay.
    # Let's assert it still holds on Day 8.
    assert res["stable_regime"] == "LATE_CYCLE", "Should have flipped by day 9"
