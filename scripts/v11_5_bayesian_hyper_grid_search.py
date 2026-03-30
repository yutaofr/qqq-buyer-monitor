import pandas as pd
import numpy as np
import logging
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from sklearn.naive_bayes import GaussianNB
from sklearn.metrics import brier_score_loss, accuracy_score
from src.engine.v11.probability_seeder import ProbabilitySeeder
from src.engine.v11.core.bayesian_inference import BayesianInferenceEngine
from src.engine.v11.core.entropy_controller import EntropyController
from src.engine.v11.signal.hysteresis_beta_mapper import HysteresisBetaMapper

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Standard Base Betas for v11.5
BASE_BETAS = {
    "BUST": 0.5,
    "CAPITULATION": 1.05,
    "RECOVERY": 1.1,
    "LATE_CYCLE": 0.8,
    "MID_CYCLE": 1.0
}

def run_audit_node(params):
    """
    Evaluates one hyper-parameter configuration across the 1999-2026 dataset.
    """
    entropy_threshold, delta_threshold, df_features, df_prices = params
    
    # Split: Train on 1999-2018, Test on 2018-2026
    split_date = pd.to_datetime("2018-01-01")
    train = df_features[df_features.index < split_date]
    test = df_features[df_features.index >= split_date]
    
    feature_cols = [c for c in train.columns if c != "regime"]
    
    # 1. Train Bayesian Brain
    gnb = GaussianNB()
    gnb.fit(train[feature_cols], train["regime"])
    
    # 2. Inference on Test Set
    engine = BayesianInferenceEngine(
        kde_models={r: None for r in gnb.classes_}, # We use GNB's classes
        base_priors=train["regime"].value_counts(normalize=True).to_dict()
    )
    # Using GNB predict_proba directly for efficiency in grid search
    test_probs = gnb.predict_proba(test[feature_cols])
    test_preds = gnb.predict(test[feature_cols])
    
    # 3. Apply Entropy & Hysteresis
    entropy_ctrl = EntropyController(threshold=entropy_threshold)
    mapper = HysteresisBetaMapper(BASE_BETAS, delta_threshold=delta_threshold)
    
    classes = gnb.classes_
    target_betas = []
    
    for i in range(len(test)):
        probs_dict = dict(zip(classes, test_probs[i]))
        # Calculate raw expectation
        raw_beta = mapper.calculate_expectation(probs_dict)
        # Apply Entropy Haircut
        norm_h = entropy_ctrl.calculate_normalized_entropy(probs_dict)
        protected_beta = entropy_ctrl.apply_haircut(raw_beta, norm_h)
        # Apply Hysteresis (Delta + Lock)
        final_beta = mapper.apply_hysteresis(protected_beta)
        target_betas.append(final_beta)
        mapper.tick_cooldown()

    # 4. Performance Metrics
    acc = accuracy_score(test["regime"], test_preds)
    y_true_dummies = pd.get_dummies(test["regime"])[classes].values
    brier = brier_score_loss(y_true_dummies.flatten(), test_probs.flatten())
    
    # COVID-19 RAE Calculation (2020-02 to 2020-05)
    test_results = pd.DataFrame({"target_beta": target_betas}, index=test.index)
    test_results = test_results.join(df_prices["Close"].pct_change().rename("ret")).dropna()
    
    test_results["strat_ret"] = test_results["ret"] * test_results["target_beta"].shift(1)
    test_results["bh_nav"] = (1 + test_results["ret"]).cumprod()
    test_results["strat_nav"] = (1 + test_results["strat_ret"]).cumprod()
    
    covid = test_results.loc["2020-02-01":"2020-05-30"]
    rae = 0.0
    if not covid.empty:
        bh_mdd = (covid["bh_nav"] / covid["bh_nav"].expanding().max() - 1).min()
        strat_mdd = (covid["strat_nav"] / covid["strat_nav"].expanding().max() - 1).min()
        rae = 1 - (abs(strat_mdd) / abs(bh_mdd)) if bh_mdd < 0 else 0
        
    return {
        "ent_thresh": entropy_threshold,
        "delta_thresh": delta_threshold,
        "accuracy": acc,
        "brier": brier,
        "rae_covid": rae,
        "turnover": test_results["target_beta"].diff().abs().mean()
    }

def main():
    # 1. Load Everything
    logger.info("Initializing Performance Audit...")
    seeder = ProbabilitySeeder()
    macro_df = pd.read_csv("data/macro_historical_dump.csv", parse_dates=["observation_date"]).set_index("observation_date")
    regime_df = pd.read_csv("data/v11_poc_phase1_results.csv", parse_dates=["observation_date"]).set_index("observation_date")
    price_df = pd.read_csv("data/qqq_history_cache.csv", parse_dates=["Date"]).set_index("Date")
    
    # 2. Generate Unified Features
    logger.info("Generating Factor Vectors...")
    features = seeder.generate_features(macro_df)
    # Join with regimes
    features = features.join(regime_df["regime"]).dropna()
    # Normalize price index
    price_df.index = pd.to_datetime(price_df.index, utc=True).tz_convert(None).normalize()
    
    # 3. Grid Definition
    entropy_grid = [0.65, 0.70, 0.75, 0.80]
    delta_grid = [0.02, 0.05, 0.08]
    
    tasks = []
    for ent in entropy_grid:
        for delta in delta_grid:
            tasks.append((ent, delta, features, price_df))
            
    # 4. Parallel Grid Search
    logger.info(f"Starting Parallel Audit for {len(tasks)} configurations...")
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(run_audit_node, tasks))
        
    # 5. Output Scorecard
    scorecard = pd.DataFrame(results).sort_values("rae_covid", ascending=False)
    scorecard_path = "data/v11.5_hyperopt_scorecard.csv"
    scorecard.to_csv(scorecard_path, index=False)
    
    print("\n" + "="*80)
    print(f"{'Entropy':<10} | {'Delta':<10} | {'RAE (COV)':<12} | {'Brier':<10} | {'Acc':<10}")
    print("-" * 80)
    for _, row in scorecard.head(10).iterrows():
        print(f"{row['ent_thresh']:<10.2f} | {row['delta_thresh']:<10.2f} | {row['rae_covid']:<12.2%} | {row['brier']:<10.4f} | {row['accuracy']:<10.2%}")
    print("="*80)
    print(f"Full results archived to: {scorecard_path}")

if __name__ == "__main__":
    main()
