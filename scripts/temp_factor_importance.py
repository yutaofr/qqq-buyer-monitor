import pandas as pd
import numpy as np
from sklearn.feature_selection import mutual_info_classif
from src.engine.v11.probability_seeder import ProbabilitySeeder
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # 1. Load Data
    logger.info("Loading data for factor importance analysis...")
    seeder = ProbabilitySeeder()
    macro_df = pd.read_csv("data/macro_historical_dump.csv", parse_dates=["observation_date"]).set_index("observation_date")
    regime_df = pd.read_csv("data/v11_poc_phase1_results.csv", parse_dates=["observation_date"]).set_index("observation_date")
    
    # 2. Generate Features
    features = seeder.generate_features(macro_df)
    features = features.join(regime_df["regime"]).dropna()
    
    X = features.drop(columns=["regime"])
    y = features["regime"]
    
    # 3. Mutual Information (Non-linear importance)
    logger.info("Calculating Mutual Information...")
    mi = mutual_info_classif(X, y, discrete_features=False, random_state=42)
    mi_series = pd.Series(mi, index=X.columns).sort_values(ascending=False)
    
    # 4. Correlation Matrix
    corr = X.corr()
    
    print("\n" + "="*80)
    print("V11.5 Probability Seeder Factor Importance (Mutual Information)")
    print("-" * 80)
    for feat, val in mi_series.items():
        print(f"{feat:<25} : {val:.4f}")
    print("="*80)
    
    print("\n" + "="*80)
    print("Factor Correlation Matrix (Redundancy Check)")
    print("-" * 80)
    print(corr.round(2))
    print("="*80)

if __name__ == "__main__":
    main()
