
import pandas as pd

from src.engine.v11.probability_seeder import ProbabilitySeeder


def audit_orthogonality():
    df = pd.read_csv("data/macro_historical_dump.csv", parse_dates=["observation_date"]).set_index("observation_date")
    seeder = ProbabilitySeeder()

    # 手动触发特征生成并捕获诊断信息
    _ = seeder.generate_features(df)
    diag = seeder.latest_diagnostics()

    if "move_21d_raw_z" in diag.columns:
        raw_corr = diag["move_21d_raw_z"].corr(diag["spread_21d"])
        orth_corr = diag["move_21d_orth_z"].corr(diag["spread_21d"])

        print("--- Orthogonality Audit ---")
        print(f"Correlation (Raw Move vs Spread): {raw_corr:.4f}")
        print(f"Correlation (Ortho Move vs Spread): {orth_corr:.4f}")

        # 统计 Beta 演化
        print(f"Beta (Move ~ Spread) Mean: {diag['move_spread_beta'].mean():.4f}")
        print(f"Beta (Move ~ Spread) Std: {diag['move_spread_beta'].std():.4f}")

if __name__ == "__main__":
    audit_orthogonality()
