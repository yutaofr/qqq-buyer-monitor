"""Final Verification Script for SRD-v13.4. Checks Entropy and UI metadata."""

from pathlib import Path

import pandas as pd

from src.engine.v11.conductor import V11Conductor


def verify():
    print("=== SRD-v13.4 Final Verification ===")

    # 1. Load the hydrated prior
    hydrated_prior_path = Path("src/engine/v11/resources/v13_6_ex_hydrated_prior.json")
    if not hydrated_prior_path.exists():
        hydrated_prior_path = Path("data/v13_6_ex_hydrated_prior.json")
    macro_path = "data/macro_historical_dump.csv"

    conductor = V11Conductor(
        macro_data_path=macro_path,
        prior_state_path=str(hydrated_prior_path),
        snapshot_dir="/tmp/v13_verification",
    )

    # 2. Get latest market row
    df = pd.read_csv(macro_path, parse_dates=["observation_date"]).set_index("observation_date")
    latest_row = df.tail(1).copy()
    # Ensure mandatory fields for execution overlay
    latest_row["qqq_close"] = 440.0
    latest_row["source_qqq_close"] = "direct"
    latest_row["qqq_close_quality_score"] = 1.0
    latest_row["qqq_volume"] = 50_000_000
    latest_row["source_qqq_volume"] = "direct"
    latest_row["qqq_volume_quality_score"] = 1.0

    # Run daily process
    runtime = conductor.daily_run(latest_row)

    # KPI 1: Entropy Convergence
    # v13.7 Reality: Conflict between Wall Street and Main Street results in high entropy.
    # We expect entropy to be within reasonable bounds but high enough to trigger Floor.
    entropy = runtime["entropy"]
    print(f"Result Entropy: {entropy:.4f}")
    if entropy < 0.95:
        print("[PASS] Entropy within rational conflict bounds.")
    else:
        print("[FAIL] Entropy too high. Check Quality Score logic.")

    # KPI 2: UI Metadata check
    print(f"Hydration Anchor: {runtime['signal'].get('hydration_anchor')}")
    if runtime["signal"].get("hydration_anchor") == "2018-01-01":
        print("[PASS] UI Metadata: hydration_anchor is correctly透传.")
    else:
        print("[FAIL] UI Metadata: hydration_anchor missing or incorrect.")

    # KPI 3: Beta Floor Protection
    # target_beta is final_beta (smoothed)
    # protected_beta is pre-smoothing intercept
    print(f"Protected Beta: {runtime['protected_beta']:.2f}")
    if runtime["protected_beta"] >= 0.5:
        print("[PASS] Beta Floor (0.5) is enforced.")
    else:
        print("[FAIL] Beta Floor failed to intercept.")

    # KPI 4: Diagnostics Payload
    if "v13_4_diagnostics" in runtime and "level_contributions" in runtime["v13_4_diagnostics"]:
        print("[PASS] Full-Stack Transparency: Contribution data captured.")
    else:
        print("[FAIL] Diagnostics payload missing.")


if __name__ == "__main__":
    verify()
