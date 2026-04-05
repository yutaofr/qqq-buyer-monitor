import numpy as np
import pandas as pd
from src.engine.baseline.data_loader import load_all_baseline_data
from src.engine.baseline.sidecar import calculate_sidecar_composites, generate_sidecar_target, train_sidecar_model, audit_sidecar_coeffs

def verify_alignment():
    data = load_all_baseline_data()
    X = calculate_sidecar_composites(data)
    y = generate_sidecar_target(data["QQQ"], data["^VXN"])
    
    # Debug Data
    print(f"X shape: {X.shape}, y shape: {y.shape}")
    print(f"y non-zero count: {y.dropna().sum()}")
    print(f"X NaNs: {X.isna().sum().sum()}")
    
    # Train on a window that actually has targets
    valid_y = y.dropna()
    if valid_y.sum() == 0:
        print("Warning: No positive targets found in window.")
    
    model = train_sidecar_model(X.loc[valid_y.index].tail(5000), valid_y.tail(5000))
    
    coeffs = dict(zip(X.columns, model.coef_[0]))
    print("\n--- Sidecar Coefficient Alignment Audit ---")
    for name, val in coeffs.items():
        print(f"{name}: {val:.6f}")
    
    is_valid = audit_sidecar_coeffs(model, X.columns.tolist())
    print(f"Physical Audit Result: {'PASSED' if is_valid else 'FAILED'}")

if __name__ == "__main__":
    verify_alignment()
