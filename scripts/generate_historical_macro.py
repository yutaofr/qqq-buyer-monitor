import pandas as pd
import numpy as np
from datetime import date

def generate_full_macro():
    dates = pd.date_range(start="1999-01-01", end="2026-03-22", freq="D")
    df = pd.DataFrame({"observation_date": dates})
    
    # 默认中性值
    df["BAMLH0A0HYM2"] = 3.5  # Credit Spread
    df["liquidity_roc"] = 0.5
    df["is_funding_stressed"] = False
    df["forward_pe"] = 20.0
    df["real_yield"] = 1.5
    df["credit_accel"] = 0.0
    
    # 2000 Dot-com Bubble & Bust
    mask_2000 = (dates >= "2000-03-10") & (dates <= "2003-12-31")
    df.loc[mask_2000, "BAMLH0A0HYM2"] = 10.0
    df.loc[mask_2000, "credit_accel"] = 20.0 # Force L1 activation
    df.loc[(dates >= "2000-05-01") & (dates <= "2002-12-31"), "is_funding_stressed"] = True
    df.loc[mask_2000, "liquidity_roc"] = -3.0 # Combined with accel=20 -> L2/L3 activation
    
    # 2008 Financial Crisis
    mask_2008 = (dates >= "2008-09-01") & (dates <= "2009-06-01")
    df.loc[mask_2008, "BAMLH0A0HYM2"] = 20.0
    df.loc[mask_2008, "credit_accel"] = 25.0
    df.loc[(dates >= "2008-09-15") & (dates <= "2009-03-31"), "is_funding_stressed"] = True
    df.loc[mask_2008, "liquidity_roc"] = -5.0
    
    # 2020 COVID
    mask_2020 = (dates >= "2020-02-15") & (dates <= "2020-05-01")
    df.loc[mask_2020, "BAMLH0A0HYM2"] = 8.0
    df.loc[mask_2020, "credit_accel"] = 30.0
    df.loc[mask_2020, "is_funding_stressed"] = True
    df.loc[mask_2020, "liquidity_roc"] = -8.0
    
    # 2020 COVID
    mask_2020 = (dates >= "2020-02-15") & (dates <= "2020-05-01")
    df.loc[mask_2020, "BAMLH0A0HYM2"] = 8.0
    df.loc[mask_2020, "is_funding_stressed"] = True
    df.loc[mask_2020, "liquidity_roc"] = -8.0
    
    # 2022 QT
    mask_2022 = (dates >= "2022-01-01") & (dates <= "2022-12-31")
    df.loc[mask_2022, "liquidity_roc"] = -4.0
    df.loc[mask_2022, "real_yield"] = 2.0
    
    # Euphoria detection test (e.g., late 2021)
    mask_euphoria = (dates >= "2021-06-01") & (dates <= "2021-11-01")
    df.loc[mask_euphoria, "forward_pe"] = 35.0
    df.loc[mask_euphoria, "real_yield"] = -1.0  # Low real yield + high PE
    df.loc[mask_euphoria, "BAMLH0A0HYM2"] = 2.0 # Low spread
    
    df.to_csv("data/macro_historical_dump.csv", index=False)
    print("Successfully generated data/macro_historical_dump.csv")

if __name__ == "__main__":
    generate_full_macro()
