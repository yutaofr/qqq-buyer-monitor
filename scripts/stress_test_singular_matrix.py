"""V12.1 Stress Test: Singular Matrix Immunity."""
import numpy as np

from src.engine.v11.sentinel import OnlineBivariateGaussian


def run_stress_test():
    print("\n--- Running Singular Matrix Stress Test ---")

    # Initialize with Ridge
    obg = OnlineBivariateGaussian(alpha=0.1, ridge_lambda=1e-6)

    # 1. Constant Data (Complete Collinearity)
    print("Testing Case 1: Identical constant data (Zero Variance)...")
    for _ in range(100):
        obg.update(np.array([0.0, 0.0]))

    try:
        _ = obg.get_inverse_covariance()
        surprisal = obg.calculate_surprisal(np.array([0.01, 0.01]))
        print(f"SUCCESS: Inverse obtained. Surprisal for 1% move: {surprisal:.4f}")
    except Exception as e:
        print(f"FAILED: Linear Algebra Error: {e}")
        return

    # 2. Perfect Linearity (Perfect Correlation)
    print("\nTesting Case 2: Perfect Linear Correlation (r = v)...")
    obg_lin = OnlineBivariateGaussian(alpha=0.1, ridge_lambda=1e-6)
    for i in range(100):
        val = float(i) * 0.001
        obg_lin.update(np.array([val, val]))

    try:
        _ = obg_lin.get_inverse_covariance()
        # A move OFF the line should trigger massive surprisal
        surprisal_off = obg_lin.calculate_surprisal(np.array([0.1, -0.1]))
        print(f"SUCCESS: Inverse obtained. Surprisal off-line: {surprisal_off:.4f}")
    except Exception as e:
        print(f"FAILED: Linear Algebra Error: {e}")
        return

    # 3. Floating Point Extremes
    print("\nTesting Case 3: Extreme small values (Underflow potential)...")
    obg_tiny = OnlineBivariateGaussian(alpha=0.1, ridge_lambda=1e-6)
    for _ in range(100):
        obg_tiny.update(np.array([1e-15, 1e-15]))

    try:
        _ = obg_tiny.get_inverse_covariance()
        print("SUCCESS: Inverse obtained for tiny values.")
    except Exception as e:
        print(f"FAILED: Linear Algebra Error: {e}")
        return

    print("\nRESULT: PASSED (System is immune to LinAlgError via Tikhonov)")

if __name__ == "__main__":
    run_stress_test()
