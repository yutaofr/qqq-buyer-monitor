import numpy as np

from src.engine.v11.sentinel import OnlineBivariateGaussian


def test_online_bivariate_gaussian_convergence():
    # Test that EWMA covariance converges to the true covariance of a normal distribution
    np.random.seed(42)
    mean = np.array([0.0, 0.0])
    cov = np.array([[1.0, 0.5], [0.5, 2.0]])

    # Generate 2000 samples
    samples = np.random.multivariate_normal(mean, cov, 2000)

    # Initialize with alpha=0.01 (long memory)
    # Burn-in 1000 samples, then check convergence
    obg = OnlineBivariateGaussian(alpha=0.01, burn_in_samples=1000)

    for i in range(2000):
        obg.update(samples[i])

    # After 2000 samples, it should be reasonably close to the true cov
    # especially since we used 1000 for burn-in
    est_cov = obg.get_covariance()

    assert np.allclose(est_cov, cov, atol=0.3)
    assert obg.is_ready()

def test_tikhonov_regularization():
    # Test that it handles singular/zero variance data gracefully
    obg = OnlineBivariateGaussian(alpha=0.1, ridge_lambda=1e-6)

    # Update with constant data (singular)
    for _ in range(50):
        obg.update(np.array([1.0, 1.0]))

    # Should be able to invert without error
    inv_cov = obg.get_inverse_covariance()
    assert inv_cov is not None
    assert not np.any(np.isnan(inv_cov))

    # Check that diagonal is at least ridge_lambda
    cov = obg.get_covariance()
    # For constant data, diagonal would be 0 without ridge
    assert np.all(np.diag(cov) >= 1e-7) # 1e-6 added to 0
