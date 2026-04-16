import io
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Configure log capture
log_stream = io.StringIO()
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s", stream=log_stream, force=True)
root_logger = logging.getLogger()
root_logger.addHandler(logging.StreamHandler(log_stream))

# Mock everything heavy
sys.modules["pandas"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["sklearn"] = MagicMock()
sys.modules["sklearn.naive_bayes"] = MagicMock()
sys.modules["yfinance"] = MagicMock()
sys.modules["requests"] = MagicMock()
sys.modules["src.collector.price"] = MagicMock()
sys.modules["src.engine.baseline.execution"] = MagicMock()
sys.modules["src.engine.v11.utils.bootstrap_guardian"] = MagicMock()
sys.modules["src.store.cloud_manager"] = MagicMock()

sys.path.append(os.getcwd())

import src.main as main  # noqa: E402
from src.engine.v11.core.prior_knowledge import (  # noqa: E402
    PriorKnowledgeBase,
    StateCorruptionError,
)


# Scenario runner
def run_chaos_test():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        state_path = tmp_path / "v11_prior_state.json"
        seed_path = tmp_path / "seed.json"
        seed_path.write_text(json.dumps({"regimes": ["MID_CYCLE"], "counts": {"MID_CYCLE": 1}}))

        env = {
            "PRIOR_STATE_PATH": str(state_path),
            "PRIOR_SEED_PATH": str(seed_path),
            "V11_REFERENCE_CAPITAL": "100",
            "V11_CURRENT_NAV": "100"
        }

        # We patch the components that main imports locally
        with patch.dict("os.environ", env), \
             patch("src.main.pd.Timestamp") as mock_ts, \
             patch("src.engine.v11.conductor.V11Conductor") as mock_cond_class, \
             patch("src.main._persist_and_export_web_artifacts"), \
             patch("src.main._materialize_prior_state"):

            mock_ts.return_value.date.return_value.isoformat.return_value = "2026-04-16"

            # --- SCENARIO A: CLEAN BOOT ---
            print("\n>>> Scenario A: Clean Boot")
            mock_cond_a = MagicMock()
            mock_cond_a.prior_book = PriorKnowledgeBase(storage_path=state_path, regimes=["MID_CYCLE"])
            mock_cond_a.prior_book.last_observation_date = None
            mock_cond_class.return_value = mock_cond_a

            main.run_v11_pipeline(MagicMock(no_save=False, notify_discord=False))

            # --- SCENARIO B: IDEMPOTENCY ---
            print("\n>>> Scenario B: Idempotency Success")
            # State now has SUCCESS
            main.run_v11_pipeline(MagicMock(no_save=False, notify_discord=False))

            # --- SCENARIO D: CORRUPTION ---
            print("\n>>> Scenario D: Corruption Defense")
            state_path.write_text("NOT JSON GARBAGE", encoding="utf-8")

            # Reset mocks for scenario D
            mock_cond_class.reset_mock()
            # First call fails because we force it (simulating PKB failure)
            mock_cond_d = MagicMock()
            mock_cond_d.prior_book = PriorKnowledgeBase(storage_path=state_path, regimes=["MID_CYCLE"])
            mock_cond_class.side_effect = [StateCorruptionError("Simulated Corruption"), mock_cond_d]

            main.run_v11_pipeline(MagicMock(no_save=False, notify_discord=False))

    print("\n" + "="*80)
    print("CAPTURED CHINESE LOGS (Fulfilling Architectural Mandate)")
    print("="*80)
    logs = log_stream.getvalue()
    for line in logs.splitlines():
        if any(c in line for c in "检测 未 到 状态 冷 启动 暖 损坏 强制 重大 警告 SUCCESS PROGRESS"):
            print(line)

if __name__ == "__main__":
    run_chaos_test()
