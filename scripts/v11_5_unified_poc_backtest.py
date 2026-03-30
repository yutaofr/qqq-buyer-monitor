import pandas as pd
import numpy as np
from sklearn.naive_bayes import GaussianNB
from sklearn.metrics import brier_score_loss, accuracy_score
from scipy.stats import entropy
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Paths
MACRO_PATH = "/app/data/macro_historical_dump.csv"
REGIME_PATH = "/app/data/v11_poc_phase1_results.csv"
PRICE_PATH = "/app/data/qqq_history_cache.csv"

def calc_signal(series, window, is_momentum=True, is_accel=False, ewma=False):
    s = series.ewm(span=window).mean() if ewma else series
    diff = s.diff(window)
    if is_accel:
        diff = diff.diff(window)
    if is_momentum or is_accel:
        # Standardize
        return (diff - diff.rolling(252).mean()) / diff.rolling(252).std()
    return (s - s.rolling(252).mean()) / s.rolling(252).std()

def main():
    logger.info("Loading Datasets...")
    macro = pd.read_csv(MACRO_PATH, parse_dates=["observation_date"])
    macro.rename(columns={"observation_date": "date"}, inplace=True)
    macro.set_index("date", inplace=True)

    regimes = pd.read_csv(REGIME_PATH, parse_dates=["observation_date"])
    regimes.set_index("observation_date", inplace=True)
    
    prices = pd.read_csv(PRICE_PATH, parse_dates=["Date"])
    prices.set_index("Date", inplace=True)

    # 1. Unified Feature Engineering (Architect A + Architect B + Architect C)
    logger.info("Engineering Architect Unification Features...")
    df = pd.DataFrame(index=macro.index)
    
    # Architect A (Dual-Horizon Momentum)
    df["erp_63d_mom"] = calc_signal(macro["erp_pct"], 63, ewma=True)
    df["real_yield_10d_mom"] = calc_signal(macro["real_yield_10y_pct"], 10)
    
    # Architect B (Entropy Anchors & Long Horizons)
    df["spread_21d"] = calc_signal(macro["credit_spread_bps"], 21, is_momentum=False)
    # Using NFCI as broad macro anchor proxy
    df["liquidity_252d"] = calc_signal(macro["net_liquidity_usd_bn"], 252, is_momentum=False)

    # Architect C (My Factor Derivative Momentum)
    df["credit_accel_21d"] = calc_signal(macro["credit_spread_bps"], 21, is_accel=True)
    df["liq_mom_4w"] = calc_signal(macro["net_liquidity_usd_bn"], 20, is_momentum=True)
    
    df.index = pd.to_datetime(df.index, utc=True).tz_convert(None).normalize()
    regimes.index = pd.to_datetime(regimes.index, utc=True).tz_convert(None).normalize()
    prices.index = pd.to_datetime(prices.index, utc=True).tz_convert(None).normalize()
    
    print("DF length before fillna:", len(df))
    df = df.fillna(0)
    print("NA counts after fillna:")
    print(df.isna().sum())
    
    print("df before join:", df.head(1).index)
    print("prices before join:", prices.dropna(subset=["Close"]).head(1).index)
    print("prices before join:", prices.dropna(subset=["Close"]).head(1).index)
    
    df = pd.merge(df, regimes[["regime"]].dropna(), left_index=True, right_index=True, how="inner")
    df = pd.merge(df, prices[["Close"]].dropna(), left_index=True, right_index=True, how="inner")
    print(f"DF non-empty rows after join: {len(df)}")
    
    # Base Betas mapping
    beta_map = {"BUST": 0.5, "CAPITULATION": 1.05, "RECOVERY": 1.1, "LATE_CYCLE": 0.8, "MID_CYCLE": 1.0}
    
    # 2. GaussianNB Probabilistic Engine
    logger.info("Training Probabilistic Engine...")
    split_date = pd.to_datetime("2018-01-01")
    train = df.loc[df.index < split_date].copy()
    test = df.loc[df.index >= split_date].copy()
    
    print(f"Train size: {len(train)}, Test size: {len(test)}")
    
    features = ["erp_63d_mom", "real_yield_10d_mom", "spread_21d", "liquidity_252d", "credit_accel_21d", "liq_mom_4w"]
    
    if len(train) == 0:
        logger.error("Train dataset is empty!")
        return
        
    gnb = GaussianNB()
    gnb.fit(train[features], train["regime"])
    
    if len(test) == 0:
        logger.error("Test dataset is empty!")
        return
    
    test_probs = gnb.predict_proba(test[features])
    test_preds = gnb.predict(test[features])
    
    # 3. Model Scoring
    acc = accuracy_score(test["regime"], test_preds)
    
    # Brier Score (calculated against dummy one-hot encoded truths)
    classes = gnb.classes_
    y_true_dummies = pd.get_dummies(test["regime"])[classes].values
    brier = brier_score_loss(y_true_dummies.flatten(), test_probs.flatten())
    
    logger.info(f"Test Accuracy (Top-1): {acc:.2%}")
    logger.info(f"Test Brier Score: {brier:.4f}")
    
    # 4. Entropy Penalty Formulation (Architect B)
    logger.info("Applying Entropy Constraints...")
    test_df = test.copy()
    test_df["entropy"] = [entropy(p, base=2) for p in test_probs]
    max_ent = np.log2(len(classes))
    test_df["norm_entropy"] = test_df["entropy"] / max_ent
    
    # Calculate expected target beta base
    test_df["pred_regime"] = test_preds
    test_df["base_beta"] = test_df["pred_regime"].map(beta_map)
    
    # Apply entropy haircut: if entropy > 0.75, reduce leverage towards 1.0
    haircut = np.clip((test_df["norm_entropy"] - 0.75) * 2, 0, 1) # Scales 0 to 1 as entropy goes 0.75 -> 1.0
    # Conservative fallback
    test_df["target_beta"] = test_df["base_beta"] * (1 - haircut) + 1.0 * haircut
    # Hard bounds
    test_df["target_beta"] = test_df["target_beta"].clip(0.5, 1.25)
    
    # 5. Efficacy Simulation (Expected Variance & RAE proxy)
    ret = test_df["Close"].pct_change()
    test_df["strat_ret"] = ret * test_df["target_beta"].shift(1)
    test_df["bh_nav"] = (1 + ret).cumprod()
    test_df["strat_nav"] = (1 + test_df["strat_ret"]).cumprod()
    
    variance_penalty = test_df["target_beta"].diff().abs().mean()
    
    # COVID RAE Specific
    covid = test_df.loc["2020-02-01":"2020-04-30"]
    if not covid.empty:
        bh_mdd = (covid["bh_nav"] / covid["bh_nav"].expanding().max() - 1).min()
        strat_mdd = (covid["strat_nav"] / covid["strat_nav"].expanding().max() - 1).min()
        rae = 1 - (abs(strat_mdd)/abs(bh_mdd)) if bh_mdd < 0 else 0
        logger.info(f"COVID RAE (Proxy): {rae:.2%}")
    else:
        logger.info("COVID slice unavailable.")

    logger.info(f"Average Turnover (Variance proxy): {variance_penalty:.4f}")
    
    # Output to File
    summary = {
        "Accuracy": f"{acc:.2%}",
        "Brier": f"{brier:.4f}",
        "RAE_COVID": f"{rae:.2%}" if not covid.empty else "N/A",
        "Turnover_Var": f"{variance_penalty:.4f}"
    }
    
    print("\n=== SYSTEM ARCHITECTURE POC METRICS ===")
    for k, v in summary.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    main()
