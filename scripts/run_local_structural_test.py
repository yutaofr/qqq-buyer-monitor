"""
run_local_structural_test.py
Zero-overhead event-loop backtest targeting the 2022+ Structural Shift Era.
"""
import logging
import pandas as pd
import numpy as np

from src.liquidity.data.panel_builder import build_pit_aligned_panel
from src.liquidity.engine.pipeline import LiquidityPipeline
from src.liquidity.config import load_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("structural_test")

def main():
    logger.info("Initializing pure structural physics audit...")
    config = load_config()
    
    panel, constituent_rets = build_pit_aligned_panel("2005-01-01", "2026-04-16", config=config)
    rets_matrix = constituent_rets.to_numpy(dtype=float)
    
    pipeline = LiquidityPipeline(config, burn_in=252)
    telemetry = []

    logger.info("Engaging single-threaded sequential event loop...")
    
    for i, (date, row) in enumerate(panel.iterrows()):
        obs = {
            "vix": float(row["VIXCLS"]),
            "walcl": float(row["WALCL"]),
            "rrp": float(row["RRPONTSYD"]),
            "tga": float(row["WTREGEN"]),
            "sofr": float(row["SOFR"]),
            "constituent_returns": rets_matrix[i, :]
        }
        
        weight, log = pipeline.step(timestamp=date, raw_obs=obs)
        
        # Only log telemetry after 2022 begins, optimizing output noise
        if date >= pd.Timestamp("2022-01-01"):
            # The burn-in guard is long past, so pipeline is active
            if log["state"] != "active":
                continue
                
            x_t = log["x_t"]
            
            telemetry.append({
                "date": date,
                "weight": weight,
                "P_cp": log["p_cp"],
                "vol_guard_cap": log.get("vol_guard_cap", 1.0),
                "ed_accel_signal": x_t[0],
                "spread_signal": x_t[1],
                "fisher_rho_signal": x_t[2],
                "lambda_macro": log["lambda_macro"],
                "s_t": log["s_t"]
            })

    # Convert to DataFrame for analytics
    df = pd.DataFrame(telemetry).set_index("date")
    
    # Analyze the SVB Collapse (March 2023)
    svb_window = df.loc["2023-03-01":"2023-03-31"]
    logger.info(f"\n--- SVB Crisis (March 2023) ---")
    logger.info(f"Max P_cp in Window: {svb_window['P_cp'].max():.4f}")
    logger.info(f"Min Vol Guard Cap: {svb_window['vol_guard_cap'].min():.4f}")
    logger.info(f"Min Weight: {svb_window['weight'].min():.4f}")

    # Analyze 0DTE suppression (Full Year 2022 Bear Market)
    bear_window = df.loc["2022-01-01":"2023-01-01"]
    logger.info(f"\n--- 2022 Grinding Bear Market ---")
    logger.info(f"Days P_cp > 0.8: {(bear_window['P_cp'] > 0.8).sum()}")
    logger.info(f"Average Vol Guard Cap: {bear_window['vol_guard_cap'].mean():.4f}")
    
    # Analyze 2024 Mega-Cap Divergence (July/August 2024 rotation shock)
    if "2024-08-01" in df.index or df.index[-1] >= pd.Timestamp("2024-07-01"):
        rotation_window = df.loc["2024-07-01":"2024-08-31"]
        logger.info(f"\n--- 2024 Summer Rotation Shock ---")
        logger.info(f"Max Fisher Rho breakdown: {rotation_window['fisher_rho_signal'].min():.4f}")
        logger.info(f"Max P_cp: {rotation_window['P_cp'].max():.4f}")
        logger.info(f"Min Weight: {rotation_window['weight'].min():.4f}")

    df.to_csv("structural_audit_2022_present.csv")
    logger.info("Telemetry dumped to structural_audit_2022_present.csv")

if __name__ == "__main__":
    main()
