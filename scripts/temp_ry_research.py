import pandas as pd
import numpy as np
from src.engine.v11.probability_seeder import ProbabilitySeeder
import logging

logging.basicConfig(level=logging.ERROR)

def test_structural_real_yield():
    # Load Data
    macro_df = pd.read_csv("data/macro_historical_dump.csv", parse_dates=["observation_date"]).set_index("observation_date")
    
    # 1. Baseline: 10d Real Yield Momentum (Existing)
    ry = macro_df["real_yield_10y_pct"]
    ry_10d = ry.diff(10)
    z_10d = (ry_10d - ry_10d.rolling(252).mean()) / ry_10d.rolling(252).std()
    
    # 2. Proposal: 126d Real Yield Z-Score (Structural)
    # We look at the level versus its long-term average
    z_structural = (ry - ry.rolling(504).mean()) / ry.rolling(504).std()
    
    # Analyze 2022 Inflation Bear (2022-01-01 to 2022-12-31)
    df_2022 = pd.DataFrame({"ry_10d_z": z_10d, "ry_structural_z": z_structural}, index=macro_df.index).loc["2022-01-01":"2022-12-31"]
    
    print("\n2022 Audit: Real Yield Sensitivity")
    print("-" * 50)
    print(f"10d Mom Z (Existing) - Mean: {df_2022['ry_10d_z'].mean():.2f}, Max: {df_2022['ry_10d_z'].max():.2f}")
    print(f"Structural Z (Proposal) - Mean: {df_2022['ry_structural_z'].mean():.2f}, Max: {df_2022['ry_structural_z'].max():.2f}")
    
    # Analyze 2020 COVID (Target Beta should NOT be affected much by this new factor)
    df_2020 = pd.DataFrame({"ry_structural_z": z_structural}, index=macro_df.index).loc["2020-02-01":"2020-04-01"]
    print("\n2020 Audit: Real Yield Sensitivity (Should be low/negative stress)")
    print("-" * 50)
    print(f"Structural Z (Proposal) - Mean: {df_2020['ry_structural_z'].mean():.2f}")

if __name__ == "__main__":
    test_structural_real_yield()
