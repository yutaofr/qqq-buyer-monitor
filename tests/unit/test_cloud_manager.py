from __future__ import annotations

from pathlib import Path

import requests

import src.store.cloud_manager as cloud_module
from src.store.cloud_manager import CloudPersistenceBridge


class _FakeResponse:
    def __init__(self, *, json_data: dict | None = None, content: bytes = b"", status_code: int = 200):
        self._json_data = json_data or {}
        self.content = content
        self.status_code = status_code

    def json(self) -> dict:
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_cloud_bridge_calculates_prod_and_staging_namespaces(monkeypatch):
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    prod_bridge = CloudPersistenceBridge(token="token")
    assert prod_bridge.namespace == "prod"

    monkeypatch.setenv("GITHUB_REF_NAME", "feature/alpha beta")
    staging_bridge = CloudPersistenceBridge(token="token")
    assert staging_bridge.namespace == "staging/feature_alpha_beta"


def test_pull_state_keeps_404_cold_start_nonfatal(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REF_NAME", "feature/cold-start")
    bridge = CloudPersistenceBridge(token="token")

    def fake_get(url: str, *, headers=None, timeout=None):
        assert url == f"{bridge.base_api_url}?limit=1000"
        return _FakeResponse(json_data={"blobs": []})

    monkeypatch.setattr(cloud_module.requests, "get", fake_get)

    ok = bridge.pull_state(["data/v11_prior_state.json"])

    assert ok is True
    assert not Path("data/v11_prior_state.json").exists()


def test_pull_state_returns_false_when_blob_listing_fails(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REF_NAME", "feature/list-fail")
    bridge = CloudPersistenceBridge(token="token")

    def fake_get(url: str, *, headers=None, timeout=None):
        assert url == f"{bridge.base_api_url}?limit=1000"
        raise requests.ConnectionError("blob list unavailable")

    monkeypatch.setattr(cloud_module.requests, "get", fake_get)

    assert bridge.pull_state(["data/signals.db"]) is False


def test_pull_state_paginates_blob_listing_until_target_found(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REF_NAME", "feature/pagination")
    bridge = CloudPersistenceBridge(token="token")

    def fake_get(url: str, *, headers=None, timeout=None):
        if url == f"{bridge.base_api_url}?limit=1000":
            return _FakeResponse(
                json_data={
                    "blobs": [
                        {
                            "pathname": "staging/feature_pagination/data/other.csv",
                            "downloadUrl": "https://download.invalid/other",
                        }
                    ],
                    "cursor": "page-2",
                }
            )
        if url == f"{bridge.base_api_url}?limit=1000&cursor=page-2":
            return _FakeResponse(
                json_data={
                    "blobs": [
                        {
                            "pathname": "staging/feature_pagination/data/signals.db",
                            "downloadUrl": "https://download.invalid/signals",
                        }
                    ]
                }
            )
        if url == "https://download.invalid/signals":
            return _FakeResponse(content=b"signals-db")
        raise AssertionError(f"Unexpected URL requested: {url}")

    monkeypatch.setattr(cloud_module.requests, "get", fake_get)

    ok = bridge.pull_state(["data/signals.db"])

    assert ok is True
    assert Path("data/signals.db").read_bytes() == b"signals-db"


def test_pull_state_returns_false_when_existing_blob_download_fails(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REF_NAME", "feature/download-fail")
    bridge = CloudPersistenceBridge(token="token")

    def fake_get(url: str, *, headers=None, timeout=None):
        if url == f"{bridge.base_api_url}?limit=1000":
            return _FakeResponse(
                json_data={
                    "blobs": [
                        {
                            "pathname": "staging/feature_download-fail/data/signals.db",
                            "downloadUrl": "https://download.invalid/signals",
                        }
                    ]
                }
            )
        if url == "https://download.invalid/signals":
            raise requests.ConnectionError("network down")
        raise AssertionError(f"Unexpected URL requested: {url}")

    monkeypatch.setattr(cloud_module.requests, "get", fake_get)

    assert bridge.pull_state(["data/signals.db"]) is False
