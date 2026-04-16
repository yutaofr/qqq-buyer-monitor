import logging
import os
import sys
from pathlib import Path

# Use local project imports
sys.path.append(os.getcwd())
from src.engine.v11.core.prior_knowledge import PriorKnowledgeBase

# SILENCE LOGGING
logging.getLogger().setLevel(logging.CRITICAL)

def run_forensic_math_audit():
    """
    V16.3 FINAL ULTIMATUM AUDIT: NO MOCKS, NO TEMPFILES.
    Directly validates the production state on the physical disk.
    """
    print("\n" + "="*80)
    print("V16.3 Bayesian Physical Truth Audit (No Mocks)")
    print("="*80)

    # 1. Enforce Production Hydration Path
    production_path = Path("data/v13_6_ex_hydrated_prior.json")
    print(f"\nTargeting Production State: {production_path}")

    if not production_path.exists():
        print(f"CRITICAL: {production_path} does not exist. Audit aborted.")
        sys.exit(1)

    try:
        # Load the base without mocks - must be a valid serialized PriorKnowledgeBase state
        pkb = PriorKnowledgeBase(storage_path=production_path)
        priors = pkb.current_priors()

        mid_cycle = priors.get('MID_CYCLE', 0.0)
        late_cycle = priors.get('LATE_CYCLE', 0.0)

        print("\nExtracted Priors:")
        print(f" - MID_CYCLE:  {mid_cycle:.4f}")
        print(f" - LATE_CYCLE: {late_cycle:.4f}")

        # --- HARD MATHEMATICAL ASSERTIONS ---
        print("\nChecking Mathematical Integrity:")

        # MID_CYCLE Verification (72.4% Production Bench)
        assert 0.72 <= mid_cycle <= 0.73, \
            f"FORGERY DETECTED: MID_CYCLE prior ({mid_cycle:.4f}) outside production bounds [0.72, 0.73]"
        print(" [OK] MID_CYCLE Prior Alignment (72.4%) confirmed.")

        # LATE_CYCLE Verification (16.0% Production Bench)
        assert 0.15 <= late_cycle <= 0.17, \
            f"FORGERY DETECTED: LATE_CYCLE prior ({late_cycle:.4f}) outside production bounds [0.15, 0.17]"
        print(" [OK] LATE_CYCLE Prior Alignment (16.0%) confirmed.")

        print("\n" + "="*80)
        print("AUDIT SUCCESS: Physical Truth matches production benchmark.")
        print("="*80)

    except Exception as e:
        print(f"\nAUDIT FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_forensic_math_audit()
