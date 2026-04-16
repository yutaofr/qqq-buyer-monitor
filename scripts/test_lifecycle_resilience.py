import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def run_test(name, description):
    print(f"\n{'='*20}")
    print(f"RUNNING TEST: {name}")
    print(f"DESCRIPTION: {description}")
    print(f"{'='*20}\n")

def main():
    # Use a temporary directory for test state
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Copy necessary artifacts for the run
        shutil.copytree("src/engine/v11/resources", tmp_path / "src/engine/v11/resources")
        # Ensure we have the seed at the expected relative path
        (tmp_path / "src/engine/v11/resources/v13_6_cold_start_seed.json").touch()
        # Wait, the main.py looks for seeds relative to current working directory or absolute.
        # It's better to just run from the workspace root but point data paths to the tmp_dir.

        # Mock environment variables
        env = os.environ.copy()
        env["V11_REFERENCE_CAPITAL"] = "100000"
        env["V11_CURRENT_NAV"] = "100000"
        prior_state_path = data_dir / "v11_prior_state.json"
        db_path = data_dir / "signals.db"
        macro_path = data_dir / "macro_historical_dump.csv"

        env["PRIOR_STATE_PATH"] = str(prior_state_path)
        env["PRIOR_SEED_PATH"] = "mock_seed.json"
        env["QQQ_DB_PATH"] = str(db_path)
        env["MACRO_DUMP_PATH"] = str(macro_path)
        env["VERCEL_BLOB_READ_WRITE_TOKEN"] = ""
        env["ALERT_WEBHOOK_URL"] = ""

        # TEST A: Clean Boot
        run_test("A", "Clean Boot (No existing state)")
        # We need to make sure src/main.py uses the PRIOR_STATE_PATH env var.

        result = subprocess.run(
            ["python3", "src/main.py"],
            env=env,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print(result.stderr)

        if "未检测到历史状态，执行冷启动。" in result.stderr or "未检测到历史状态，执行冷启动。" in result.stdout:
            print("Test A SUCCESS: Cold start triggered correctly.")
        else:
            print("Test A FAILED: Cold start log not found.")

        # TEST B: Warm Reload
        run_test("B", "Warm Reload (Existing state from Test A)")
        # Note: We need to see if it detects yesterday's state.
        # Since we just ran it, it should be the same day -> Idempotency.
        result = subprocess.run(
            ["python3", "src/main.py"],
            env=env,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print(result.stderr)

        if "Idempotency Protection Active" in result.stderr or "Idempotency Protection Active" in result.stdout:
            print("Test B SUCCESS: Idempotency triggered correctly.")
        else:
            print("Test B FAILED: Idempotency log not found.")

        # TEST C: Corrupted Cache
        run_test("C", "Corrupted Cache (Invalid JSON)")
        prior_state_path.write_text("THIS IS NOT JSON { { {")

        result = subprocess.run(
            ["python3", "src/main.py"],
            env=env,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print(result.stderr)

        if "缓存损坏，强制执行冷启动" in result.stderr or "缓存损坏，强制执行冷启动" in result.stdout:
            print("Test C SUCCESS: Recovery triggered correctly.")
        else:
            print("Test C FAILED: Recovery log not found.")

if __name__ == "__main__":
    main()
