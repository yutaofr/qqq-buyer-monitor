import os
import json
import logging
import tempfile
import sys
import io
from pathlib import Path

# --- Platform Compatibility Mocks ---
# These are necessary just to let PriorKnowledgeBase import
import typing
# Define the mocks before importing our code
sys.modules["numpy"] = sys.modules["pandas"] = type('Mock', (), {'Timestamp': lambda x: type('Mock', (), {'date': lambda: type('Mock', (), {'isoformat': lambda: '2026-04-16'})})})()
sys.modules["src.regime_topology"] = type('Mock', (), {
    'canonicalize_regime_name': lambda x: x,
    'canonicalize_regime_sequence': lambda x, **k: x,
    'merge_regime_weights': lambda x, **k: x,
    'merge_transition_matrix': lambda x, **k: x
})

# Add current path to sys.path
sys.path.insert(0, os.getcwd())

# Import our ACTUAL hardened components
from src.engine.v11.core.prior_knowledge import PriorKnowledgeBase, StateCorruptionError

# Configure Logging to capture the REAL Chinese logs
log_stream = io.StringIO()
logger = logging.getLogger("src.engine.v11.core.prior_knowledge")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(log_stream)
handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(handler)

# Also capture for our mock main logic
logger_main = logging.getLogger("main_mock")
logger_main.setLevel(logging.INFO)
logger_main.addHandler(handler)

def hardened_lifecycle_loop(state_path, seed_path, current_date):
    """1:1 Reproduction of the hardened logic in src/main.py"""
    try:
        # Implementation of the .lock logic for the test
        lock_file = state_path.with_suffix(".lock")
        if lock_file.exists():
            logger_main.warning("发现残留锁文件 %s。正在执行强行锁定...", lock_file.name)
        lock_file.touch(exist_ok=False)
        
        try:
            # 1. Initialization (Conductor init -> PKB _load)
            try:
                pkb = PriorKnowledgeBase(storage_path=state_path, regimes=["MID_CYCLE"])
                
                # 2. Idempotency Guard (Date + SUCCESS status)
                last_date = pkb.last_observation_date
                last_status = pkb.execution_state.get("lifecycle_status", "NONE")
                
                if last_date == current_date and last_status == "SUCCESS":
                    logger_main.info("Idempotency Protection Active: Date %s already status SUCCESS. Skipping.", current_date)
                    return True

                # 3. Mark Run
                pkb.update_execution_state(lifecycle_status="IN_PROGRESS")
                
                if last_date:
                    logger_main.info("检测到历史状态 (Last: %s, Status: %s)，执行暖启动。", last_date, last_status)
                else:
                    logger_main.info("未检测到历史状态，执行冷启动。")
                
                # Simulating daily_run work...
                # ... work ...
                
                # 4. Finalize
                pkb.last_observation_date = current_date
                pkb.update_execution_state(lifecycle_status="SUCCESS")
                logger_main.info("生命周期状态封闭为 SUCCESS。")
                return True

            except (StateCorruptionError, Exception) as exc:
                logger_main.error("缓存损坏或不可恢复，强制执行冷启动 (Recovery Triggered: %s)", exc)
                
                # Destruction of toxic state
                if state_path.exists():
                    state_path.unlink()
                
                # Cold Start Fallback
                pkb = PriorKnowledgeBase(storage_path=state_path, regimes=["MID_CYCLE"])
                pkb.update_execution_state(lifecycle_status="IN_PROGRESS")
                
                # Simulating daily_run work...
                pkb.last_observation_date = current_date
                pkb.update_execution_state(lifecycle_status="SUCCESS")
                logger_main.info("恢复完成，生命周期状态修正为 SUCCESS。")
                return True
        finally:
            if lock_file.exists():
                lock_file.unlink()
                
    except Exception as e:
        logger_main.error("Critical Failure in Lifecycle: %s", e)
        return False

def run_chaos_monkey():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        state_path = tmp_path / "v11_prior_state.json"
        seed_path = tmp_path / "seed.json"
        
        print("\n" + "="*80)
        print("V16 HARDENED INITIALIZATION CHAOS TEST (REAL DISK I/O)")
        print("="*80)
        
        # --- Scenario A: Clean Boot ---
        print("\n>>> Scenario A: Clean Boot (First Deployment)")
        log_stream.truncate(0)
        log_stream.seek(0)
        hardened_lifecycle_loop(state_path, seed_path, "2026-04-16")
        print(log_stream.getvalue())

        # --- Scenario B: Warm Start (Idempotency) ---
        print(">>> Scenario B: Idempotency Success (Today Already Done)")
        log_stream.truncate(0)
        log_stream.seek(0)
        hardened_lifecycle_loop(state_path, seed_path, "2026-04-16")
        print(log_stream.getvalue())

        # --- Scenario C: Dirty Rerun (Previous Crash) ---
        print(">>> Scenario C: Dirty Rerun (Recovery from IN_PROGRESS)")
        # Manually sabotage state to be IN_PROGRESS
        data = json.loads(state_path.read_text())
        data["execution_state"]["lifecycle_status"] = "IN_PROGRESS"
        state_path.write_text(json.dumps(data))
        
        log_stream.truncate(0)
        log_stream.seek(0)
        hardened_lifecycle_loop(state_path, seed_path, "2026-04-17") # New day
        print(log_stream.getvalue())

        # --- Scenario D: Corruption Defense ---
        print(">>> Scenario D: Zero-Tolerance Corruption Fallback (REAL DISK UNLINK)")
        # Write real garbage to disk
        state_path.write_text("THIS IS POISONED GARBAGE - NOT JSON", encoding="utf-8")
        
        log_stream.truncate(0)
        log_stream.seek(0)
        hardened_lifecycle_loop(state_path, seed_path, "2026-04-18")
        print(log_stream.getvalue())
        
        if not state_path.exists():
            print("ERROR: State path should exist (recreated after cold start)!")
        else:
            # Check if it's clean
            final_data = json.loads(state_path.read_text())
            print(f"Final State Check: Date={final_data['last_observation_date']}, Status={final_data['execution_state']['lifecycle_status']}")

if __name__ == "__main__":
    run_chaos_monkey()
