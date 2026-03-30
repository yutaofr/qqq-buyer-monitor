
import pandas as pd
import numpy as np
from src.engine.v11.core.calibration_service import CalibrationService
from src.engine.v11.core.feature_library import FeatureLibraryManager

def debug():
    dataset_path = "data/v11_feature_library.csv"
    df = pd.read_csv(dataset_path)
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    
    library = FeatureLibraryManager(storage_path=dataset_path, persist=False)
    library.df = df.copy()
    standardized = library.get_standardized_features()
    
    calibrator = CalibrationService()
    baseline_features = ["spread_stress_pct", "liquidity_stress_pct", "vix_stress_pct", "drawdown_stress_pct", "breadth_stress_pct", "term_structure_stress_pct"]
    
    # Use a small subset for calibration
    train = df.head(1000)
    std_train = standardized.head(1000)
    calibrator.calibrate(std_train, train, feature_cols=baseline_features)
    
    # Inspect one packet
    test_row = standardized.iloc[1500]
    packet = calibrator.get_inference_packet(test_row)
    
    print(f"Packet keys: {packet.keys()}")
    print(f"PCA Coords Type: {type(packet['pca_coords'])}")
    print(f"PCA Coords Shape: {getattr(packet['pca_coords'], 'shape', 'N/A')}")
    print(f"PCA Coords Content: {packet['pca_coords']}")
    
    # Try flat indexing
    try:
        print(f"Flat Access [0]: {packet['pca_coords'][0]}")
        print(f"Flat Access [1]: {packet['pca_coords'][1]}")
    except Exception as e:
        print(f"Flat Access Error: {e}")

if __name__ == "__main__":
    debug()
