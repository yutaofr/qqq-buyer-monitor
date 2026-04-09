
import csv
import json
import os
import sys

# Add src to path
sys.path.append(os.getcwd())

from src.store.db import init_db


def seed_database(csv_path: str, db_path: str):
    print(f"Seeding {db_path} from {csv_path}...")
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    conn = init_db(db_path)

    # Check if we already have data
    cursor = conn.execute("SELECT COUNT(*) FROM signals")
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"Database already has {count} records. Skipping seeding to prevent duplication.")
        conn.close()
        return

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        rows_to_insert = []
        for row in reader:
            # Reconstruct the expected json_blob for the UI
            # Note: actual_regime_probability, predicted_regime, brier, etc are in the CSV

            probs = {
                "MID_CYCLE": float(row.get("prob_MID_CYCLE", 0)),
                "LATE_CYCLE": float(row.get("prob_LATE_CYCLE", 0)),
                "BUST": float(row.get("prob_BUST", 0)),
                "RECOVERY": float(row.get("prob_RECOVERY", 0))
            }

            # Create a mock SignalResult blob that matches src/store/db.py:_to_json_dict
            blob = {
                "date": row["date"],
                "price": 0.0, # Not strictly needed for the chart
                "target_beta": 0.0, # Not strictly needed for the chart
                "probabilities": probs,
                "priors": {},
                "entropy": 0.0,
                "stable_regime": row["predicted_regime"],
                "target_allocation": {"beta": 0.0, "reason": "Seed data"},
                "logic_trace": [],
                "explanation": "Historical seed data",
                "metadata": {"version": "v14.0-ULTIMA-SEED"}
            }

            rows_to_insert.append((
                row["date"],
                0.0,
                0.0,
                json.dumps(blob, ensure_ascii=False)
            ))

    print(f"Inserting {len(rows_to_insert)} records...")
    conn.executemany(
        "INSERT OR REPLACE INTO signals (date, target_beta, price, json_blob) VALUES (?, ?, ?, ?)",
        rows_to_insert
    )
    conn.commit()
    conn.close()
    print("Seeding complete.")

if __name__ == "__main__":
    # Use the tau5.0 audit results as the truth for history
    CSV_SRC = "artifacts/v13_matrix/tau5.0/probability_audit.csv"
    DB_DST = "data/signals.db"
    seed_database(CSV_SRC, DB_DST)
