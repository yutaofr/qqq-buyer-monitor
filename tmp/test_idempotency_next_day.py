
import json
from pathlib import Path
import sys

# Add src to path
sys.path.append("./src")
from engine.v11.core.prior_knowledge import PriorKnowledgeBase

def test_idempotency_cross_day():
    storage = Path("/tmp/test_prior_idempotency.json")
    if storage.exists(): storage.unlink()
    
    # 1. Initialize
    regimes = ["LATE_CYCLE", "MID_CYCLE"]
    pk = PriorKnowledgeBase(storage_path=storage, regimes=regimes)
    initial_counts = sum(pk.counts.values())
    print(f"Initial counts: {initial_counts}")
    
    # 2. Run Day 1 - First time
    pk.update_with_posterior(observation_date="2026-03-31", posterior={"LATE_CYCLE": 1.0})
    counts_d1_r1 = sum(pk.counts.values())
    print(f"Day 31 Run 1 counts: {counts_d1_r1} (Should increase by 1.0)")
    
    # 3. Run Day 31 - Second time (Same day)
    pk.update_with_posterior(observation_date="2026-03-31", posterior={"LATE_CYCLE": 1.0})
    counts_d1_r2 = sum(pk.counts.values())
    print(f"Day 31 Run 2 counts: {counts_d1_r2} (Should NOT increase - IDEMPOTENT)")
    
    # 4. Run Day 1 (Next day)
    pk.update_with_posterior(observation_date="2026-04-01", posterior={"LATE_CYCLE": 1.0})
    counts_d2_r1 = sum(pk.counts.values())
    print(f"Day 01 Run 1 counts: {counts_d2_r1} (Should increase by 1.0 - CROSS-DAY NORMAL)")
    
    # Validations
    assert counts_d1_r1 == initial_counts + 1.0
    assert counts_d1_r2 == counts_d1_r1
    assert counts_d2_r1 == counts_d1_r1 + 1.0
    print("\nVERIFICATION PASSED: Idempotency is date-specific and allows next-day updates.")

if __name__ == "__main__":
    test_idempotency_cross_day()
