import numpy as np
import pandas as pd

from src.engine.baseline.sidecar import train_sidecar_model


def test_sidecar_train_audit_fallback():
    """
    Test that Sidecar model training detects coefficient inversion and falls back to constrained solver.
    """
    np.random.seed(42)
    # 1. Create data where Feature 0 (growth) is POSITIVELY correlated with y
    # and Feature 1 (stress) is NEGATIVELY correlated. (Opposite of physical rules)
    n = 2000
    X = pd.DataFrame(
        {
            "growth_composite": np.random.randn(n),
            "stress_composite_extreme": np.random.randn(n),
            "liquidity_composite": np.random.randn(n),
            "vxn_acceleration": np.random.randn(n),
            "qqq_spy_relative_weakness": np.random.randn(n),
        }
    )

    # Target following inverted logic:
    # y=1 if growth is high or stress is low (highly unrealistic but triggers audit)
    y = ((X["growth_composite"] - X["stress_composite_extreme"]) > 1.0).astype(int)

    # 2. Run train_sidecar_model
    # This should trigger audit failure and fallback to constrained optimization
    model = train_sidecar_model(X, pd.Series(y))

    # 3. Check results
    assert hasattr(model, "constrained_flag")
    assert model.constrained_flag is True, (
        "Model should have fallen back to constrained optimization"
    )

    # Check that coefficients strictly respect the rules
    # growth_composite idx 0: <= 0
    # stress_composite_extreme idx 1: >= 0
    coeffs = model.coef_[0]

    # Even though growth is positively correlated with y, the coefficient should be forced to <= 0
    assert coeffs[0] <= 1e-10, f"growth_composite coefficient ({coeffs[0]}) should be <= 0"
    assert coeffs[1] >= -1e-10, f"stress_composite_extreme coefficient ({coeffs[1]}) should be >= 0"

    # Check that it provides valid probabilities
    probs = model.predict_proba(X)
    assert probs.shape == (n, 2)
    assert (probs >= 0).all() and (probs <= 1).all()


def test_sidecar_train_no_fallback_on_valid_data():
    """
    Test that Sidecar model training does NOT fall back to constrained optimization on physically valid data.
    """
    np.random.seed(42)
    n = 1000
    X = pd.DataFrame(
        {
            "growth_composite": np.random.randn(n),
            "stress_composite_extreme": np.random.randn(n),
            "liquidity_composite": np.random.randn(n),
            "vxn_acceleration": np.random.randn(n),
            "qqq_spy_relative_weakness": np.random.randn(n),
        }
    )
    # Physically correct logic: low growth, high stress, low liquidity, low vxn_accel (wait vxn is high), high weakness
    # Stress and VXN should be positive
    # Growth, Liq, Weakness should be negative
    y = (
        (X["stress_composite_extreme"] * 0.5)
        + (X["vxn_acceleration"] * 0.2)
        - (X["growth_composite"] * 0.5)
        - (X["liquidity_composite"] * 0.2)
        - (X["qqq_spy_relative_weakness"] * 0.2)
        > 1.0
    ).astype(int)

    model = train_sidecar_model(X, pd.Series(y))

    assert hasattr(model, "constrained_flag")
    assert model.constrained_flag is False, (
        "Model should NOT have fallen back to constrained optimization"
    )
    assert model.coef_[0, 0] <= 0
    assert model.coef_[0, 1] >= 0
