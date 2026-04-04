"""
Standardized On-Demand Integration Test for Vercel Blob Sync.
Usage: pytest tests/integration/test_cloud_sync_real.py -m external_service
"""

from __future__ import annotations

import os
import uuid

import pandas as pd
import pytest
import requests

from src.store.cloud_manager import CloudPersistenceBridge


@pytest.mark.external_service
def test_cloud_sync_full_lifecycle_real_api(tmp_path):
    """
    Validates Push -> Pull -> Integrity check using real Vercel credentials.
    Only runs manually or when explicitly targeted.
    """
    token = os.environ.get("VERCEL_BLOB_READ_WRITE_TOKEN")
    if not token:
        pytest.skip("VERCEL_BLOB_READ_WRITE_TOKEN not set in environment.")

    # 1. Setup - Create a unique test file using UUID to prevent edge cache collisions
    test_filename = f"integration_test_{uuid.uuid4().hex}.csv"
    local_path = tmp_path / test_filename
    df_out = pd.DataFrame({"test_val": [1.2345], "status": ["verified"]})
    df_out.to_csv(local_path, index=False)

    bridge = CloudPersistenceBridge(token=token)
    # Force CI mode to enable API execution
    bridge.is_ci = True
    # Force a unique test namespace
    bridge.namespace = "testing/integration"

    # 2. Act - Push
    push_ok = bridge.push_payload(local_path.read_bytes(), test_filename, is_binary=True)
    assert push_ok is True, "Cloud push failed."

    # 3. Act - Pull
    # Change local location to verify fresh download
    restore_path = tmp_path / f"restored_{test_filename}"
    # We must mock pull_state's target or use bridge internals
    # For simplicity, we leverage bridge._get_remote_path and requests directly
    list_resp = requests.get(
        f"{bridge.base_api_url}?limit=1000&prefix={bridge.namespace}/", headers=bridge.headers
    )
    list_resp.raise_for_status()
    blobs = list_resp.json().get("blobs", [])

    remote_path = f"testing/integration/{test_filename}"
    target_blob = next((b for b in blobs if b["pathname"] == remote_path), None)

    assert target_blob is not None, f"File {remote_path} not found in cloud after push."

    file_resp = requests.get(target_blob["downloadUrl"])
    file_resp.raise_for_status()
    with open(restore_path, "wb") as f:
        f.write(file_resp.content)

    # 4. Assert - Data Integrity
    df_in = pd.read_csv(restore_path)
    assert df_in["test_val"].iloc[0] == 1.2345
    assert df_in["status"].iloc[0] == "verified"

    print(f"\nCloud Sync Verified: {remote_path} -> Integrity Match.")


@pytest.mark.external_service
def test_discord_notification_real_api():
    """
    Sends a real integration test signal to Discord using ALERT_WEBHOOK_URL.
    Requires ENABLE_REAL_DISCORD_TEST=true to prevent accidental leakage.
    """
    from datetime import date

    from src.models import SignalResult, TargetAllocationState
    from src.output.discord_notifier import send_discord_signal

    webhook_url = os.environ.get("ALERT_WEBHOOK_URL")
    enable_real = os.environ.get("ENABLE_REAL_DISCORD_TEST") == "true"

    if not webhook_url:
        pytest.skip("ALERT_WEBHOOK_URL not set in environment.")
    if not enable_real:
        pytest.skip("ENABLE_REAL_DISCORD_TEST not set to 'true'; skipping real Discord push.")

    # Construct a high-fidelity test result
    result = SignalResult(
        date=date.today(),
        price=558.28,
        target_beta=0.80,
        probabilities={"LATE_CYCLE": 0.95, "MID_CYCLE": 0.05},
        priors={"LATE_CYCLE": 0.50, "MID_CYCLE": 0.50},
        entropy=0.042,
        stable_regime="LATE_CYCLE",
        target_allocation=TargetAllocationState(0.20, 0.80, 0.0, 0.80),
        logic_trace=[
            {"step": "integration_test", "result": {"source": "github_actions_simulation"}}
        ],
        explanation="[INTEGRATION TEST] v12.0 Architecture Convergence Audit.",
    )

    ok = send_discord_signal(result, webhook_url)
    assert ok is True, "Failed to send real Discord notification."
    print("\nDiscord Integration Verified: Notification dispatched successfully.")
