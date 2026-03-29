
import pandas as pd
import yfinance as yf

from src.engine.tier1 import calculate_tier1
from src.models import MarketData


def check_2025():
    qqq = yf.Ticker("QQQ").history(start="2023-01-01", end="2025-05-31")
    vix = yf.Ticker("^VIX").history(start="2023-01-01", end="2025-05-31")

    df = pd.DataFrame(index=qqq.index)
    df["Close"] = qqq["Close"]
    df["Volume"] = qqq["Volume"]
    df["MA200"] = df["Close"].rolling(200, min_periods=50).mean()
    df["MA50"] = df["Close"].rolling(50, min_periods=20).mean()
    df["High52w"] = df["Close"].rolling(252, min_periods=50).max()

    qqq_dates = [d.date() for d in qqq.index]
    vix_dates = [d.date() for d in vix.index]

    vix_dict = dict(zip(vix_dates, vix["Close"], strict=False))
    df["VIX"] = [vix_dict.get(d, None) for d in qqq_dates]
    df["VIX"] = df["VIX"].ffill()
    df = df.dropna()

    for dt, row in df.iterrows():
        if dt.year == 2025 and (dt.month == 3 or dt.month == 4):
            vix_val = float(row["VIX"])
            fg_synthetic = max(0.0, min(100.0, 100.0 - (vix_val - 10) * 4))

            dev_50 = (row["Close"] - row["MA50"]) / row["MA50"]
            if pd.isna(dev_50):
                pct_50 = 0.5
            elif dev_50 > 0.05:
                pct_50 = 0.65
            elif dev_50 < -0.05:
                pct_50 = 0.20
            else:
                pct_50 = 0.40

            lookback_df_60 = df[df.index <= dt].tail(60).copy()

            mdata = MarketData(
                date=dt.date(),
                price=float(row["Close"]),
                ma200=float(row["MA200"]),
                high_52w=float(row["High52w"]),
                vix=vix_val,
                fear_greed=int(fg_synthetic),
                adv_dec_ratio=0.5,
                pct_above_50d=pct_50,
                options_df=None,
                credit_spread=None,
                forward_pe=None,
                history_window=pd.DataFrame({
                    "price": lookback_df_60["Close"],
                    "vix": lookback_df_60["VIX"],
                    "breadth": 0.5
                })
            )

            t1 = calculate_tier1(mdata)
            if t1.score >= 70:
                print(f"TRIGGERED on {dt.date()}: Score={t1.score}, Price={row['Close']:.2f}")
                print(f"  Drawdown={t1.drawdown_52w.value*100:.1f}%, MA200Dev={t1.ma200_deviation.value*100:.1f}%, VIX={t1.vix.value:.1f}, DivBonus={t1.divergence_bonus}")

if __name__ == "__main__":
    check_2025()
