import sys
from unittest.mock import MagicMock, patch
import logging
import io
import json
from pathlib import Path

# 1. Mock heavy dependencies BEFORE importing our code
sys.modules["pandas"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["sklearn"] = MagicMock()
sys.modules["sklearn.naive_bayes"] = MagicMock()
sys.modules["yfinance"] = MagicMock()
sys.modules["requests"] = MagicMock()

import src.main as main

def setup_log_capture():
    log_capture_string = io.StringIO()
    ch = logging.StreamHandler(log_capture_string)
    ch.setLevel(logging.INFO)
    main_logger = logging.getLogger("qqq_monitor")
    main_logger.addHandler(ch)
    main_logger.setLevel(logging.INFO)
    return log_capture_string

def test_lifecycle_scenarios():
    log_stream = setup_log_capture()
    
    seed_path = Path("v16_mock_seed.json")
    seed_data = {
        "regimes": ["MID_CYCLE"],
        "counts": {"MID_CYCLE": 100},
        "execution_state": {"last_observation_date": "2026-04-15"},
        "bootstrap_fingerprint": "abc"
    }
    seed_data_json = json.dumps(seed_data)
    seed_path.write_text(seed_data_json)
    
    state_path = Path("v16_mock_state.json")
    
    # Common mocks
    with patch("src.main.CloudPersistenceBridge"), \
         patch("src.collector.price.fetch_price_data") as mock_fetch, \
         patch("src.main._materialize_prior_state"), \
         patch("src.engine.v11.utils.bootstrap_guardian.BootstrapGuardian"), \
         patch("src.engine.baseline.execution.run_baseline_inference"), \
         patch("src.main._build_v11_signal_result"), \
         patch("src.main._persist_and_export_web_artifacts"), \
         patch.dict("os.environ", {"PRIOR_STATE_PATH": str(state_path), "PRIOR_SEED_PATH": str(seed_path)}):

        # Scenario A: Clean Boot
        print(">>> Testing Scenario A: Clean Boot")
        if state_path.exists(): state_path.unlink()
        mock_fetch.return_value = {"date": "2026-04-16", "price": 400.0}
        
        with patch("src.engine.v11.conductor.V11Conductor") as mock_cond_class:
            mock_cond = mock_cond_class.return_value
            mock_cond.prior_book = MagicMock()
            mock_cond.prior_book.last_observation_date = None
            
            try:
                main.run_v11_pipeline(MagicMock())
            except Exception as e:
                # print(f"Note: Ignoring intended function exit/error in mock: {e}")
                pass

        # Scenario B: Warm Start
        print(">>> Testing Scenario B: Warm Start")
        state_path.write_text(seed_data_json)
        with patch("src.engine.v11.conductor.V11Conductor") as mock_cond_class:
            mock_cond = mock_cond_class.return_value
            mock_cond.prior_book = MagicMock()
            mock_cond.prior_book.last_observation_date = "2026-04-15"
            
            try:
                main.run_v11_pipeline(MagicMock())
            except Exception as e:
                pass

        # Scenario C: Corrupted Cache
        print(">>> Testing Scenario C: Corrupted Cache")
        state_path.write_text("NOT_JSON")
        with patch("src.engine.v11.conductor.V11Conductor") as mock_cond_class:
            # First call to V11Conductor fails (simulating corruption)
            # Second call (recovery) succeeds
            mock_cond_recovered = MagicMock()
            mock_cond_recovered.prior_book = MagicMock()
            mock_cond_recovered.prior_book.last_observation_date = None
            mock_cond_class.side_effect = [Exception("JSON CORRUPTION"), mock_cond_recovered]
            
            try:
                main.run_v11_pipeline(MagicMock())
            except Exception as e:
                pass

    print("\n--- CAPTURED LOGS ---")
    logs = log_stream.getvalue()
    print(logs)
    print("----------------------")
    
    success_a = "未检测到历史状态，执行冷启动" in logs
    success_b = "检测到昨日状态，执行暖启动" in logs
    success_c = "缓存损坏，强制执行冷启动" in logs
    
    if success_a: print("✅ Scenario A confirmed.")
    else: print("❌ Scenario A failed.")
    
    if success_b: print("✅ Scenario B confirmed.")
    else: print("❌ Scenario B failed.")
    
    if success_c: print("✅ Scenario C confirmed.")
    else: print("❌ Scenario C failed.")
    
    if seed_path.exists(): seed_path.unlink()
    if state_path.exists(): state_path.unlink()
    
    if not (success_a and success_b and success_c):
        sys.exit(1)

if __name__ == "__main__":
    test_lifecycle_scenarios()
