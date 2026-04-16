import pandas as pd
import json
from datetime import datetime

# Input paths
EXEC_TRACE_PATH = "artifacts/v14_mainline_audit/execution_trace.csv"
PROB_TRACE_PATH = "artifacts/v14_mainline_audit/probability_audit.csv"
STRUCTURAL_TRACE_PATH = "structural_audit_2020_present.csv"
QQQ_PRICE_PATH = "data/qqq_history_cache.csv"
OUTPUT_JSON_PATH = "src/web/public/glassbox_trace.json"

def main():
    print("Loading data...")
    df_exec = pd.read_csv(EXEC_TRACE_PATH)
    df_prob = pd.read_csv(PROB_TRACE_PATH)
    df_struct = pd.read_csv(STRUCTURAL_TRACE_PATH)

    # Align dates
    df_exec['date'] = pd.to_datetime(df_exec['date']).dt.strftime('%Y-%m-%d')
    df_prob['date'] = pd.to_datetime(df_prob['date']).dt.strftime('%Y-%m-%d')
    df_struct['date'] = pd.to_datetime(df_struct['date']).dt.strftime('%Y-%m-%d')

    print("Merging data...")
    # Base frame is the structural truth which holds physics to April 15
    df = df_struct.copy()

    # Left join V14 probabilities and targets that stopped on March 31
    df = df.merge(df_exec[['date', 'target_bucket', 'deployment_state', 'target_beta', 'raw_target_beta', 'lock_active', 'entropy']], on='date', how='left')
    df = df.merge(df_prob[['date', 'prob_MID_CYCLE', 'prob_LATE_CYCLE', 'prob_BUST', 'prob_RECOVERY']], on='date', how='left')
    
    # Forward fill the gap from March 31 to April 15
    cols_to_ffill = [
        'target_bucket', 'deployment_state', 'target_beta', 'raw_target_beta', 
        'lock_active', 'entropy', 'prob_MID_CYCLE', 'prob_LATE_CYCLE', 'prob_BUST', 'prob_RECOVERY'
    ]
    df[cols_to_ffill] = df[cols_to_ffill].ffill()
    
    # Filter 2020+
    df = df[df['date'] >= '2020-01-01'].sort_values('date')

    print(f"Total points aligned: {len(df)}")

    # Extract JSON nodes
    trace_data = []
    
    for _, row in df.iterrows():
        # pb format: [MID, LATE, BUST, RECOVERY]
        pb = [
            round(float(row['prob_MID_CYCLE']), 4),
            round(float(row['prob_LATE_CYCLE']), 4),
            round(float(row['prob_BUST']), 4),
            round(float(row['prob_RECOVERY']), 4)
        ]
        
        trace_data.append({
            "d": row['date'],
            "c": round(float(row['qqq_price']), 2),
            "sma": round(float(row['qqq_sma200']), 2),
            "pb": pb,
            "beta": round(float(row['target_beta']), 4),
            "raw_beta": round(float(row['raw_target_beta']), 4),
            "ent": round(float(row['entropy']), 4),
            "lock": bool(row['momentum_lockout']),
            "bucket": str(row['target_bucket']),
            "deploy": str(row['deployment_state']),
            "pcp": round(float(row['P_cp']), 4),
            "vol": round(float(row['vol_guard_cap']), 2),
            "st": round(float(row['s_t']), 4),
            "sigma2": round(float(row['sigma2_spread']), 4),
            "roll": round(float(row['roll_threshold']), 4),
            "weight": round(float(row['weight']), 4)
        })

    # Output JSON structure
    out_dict = {
        "meta": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "data_range": [df['date'].min(), df['date'].max()],
            "total_points": len(df),
            "engine_version": "v16.0 Glassbox"
        },
        "events": [
            {
              "id": "covid_crash",
              "label": "🦠 2020 新冠熔断",
              "date_range": ["2020-02-19", "2020-03-23"]
            },
            {
              "id": "bear_market_2022",
              "label": "🐻 2022 绞肉机",
              "date_range": ["2022-01-03", "2022-10-12"]
            },
            {
              "id": "svb_crisis",
              "label": "🏦 2023 SVB危机",
              "date_range": ["2023-03-08", "2023-03-31"]
            },
            {
              "id": "mega_divergence",
              "label": "🤖 2024 巨头分化",
              "date_range": ["2024-07-10", "2024-08-31"]
            },
            {
              "id": "latest_pullback",
              "label": "🌀 2025/2026 回调",
              "date_range": ["2025-01-01", str(df['date'].iloc[-1])]
            }
        ],
        "trace": trace_data
    }

    with open(OUTPUT_JSON_PATH, "w") as f:
        json.dump(out_dict, f, separators=(',', ':'))

    print(f"Successfully wrote {OUTPUT_JSON_PATH}")

if __name__ == "__main__":
    main()
