from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from src.collector import global_macro, macro, macro_v3


def test_fetch_real_yield_snapshot_uses_latest_non_null_observation(monkeypatch):
    frame = pd.DataFrame(
        {
            "observation_date": ["2026-04-02", "2026-04-03"],
            "DFII10": [1.97, np.nan],
        }
    )
    monkeypatch.setattr(macro_v3, "fetch_fred_data", lambda *_args, **_kwargs: frame.copy())

    snapshot = macro_v3.fetch_real_yield_snapshot()

    assert snapshot["value"] == 1.97
    assert snapshot["source"] == "fred:DFII10"
    assert snapshot["degraded"] is False


def test_fetch_fred_api_retries_transient_500_then_succeeds(monkeypatch):
    class _Response:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self._payload = payload

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"http {self.status_code}")

        def json(self):
            return self._payload

    calls = {"count": 0}

    def fake_get(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return _Response(500, {})
        return _Response(
            200,
            {
                "observations": [
                    {"date": "2026-04-03", "value": "1.99"},
                ]
            },
        )

    monkeypatch.setattr(macro.requests, "get", fake_get)
    monkeypatch.setenv("FRED_API_KEY", "test-key")

    frame = macro.fetch_fred_api("DFII10", timeout=1)

    assert calls["count"] == 2
    assert frame is not None
    assert frame.iloc[-1]["DFII10"] == 1.99


def test_fetch_shiller_ttm_eps_falls_back_to_cached_macro_history(monkeypatch, tmp_path, caplog):
    macro_path = tmp_path / "macro.csv"
    pd.DataFrame(
        {
            "observation_date": ["2026-04-01", "2026-04-02"],
            "erp_ttm_pct": [0.0265, 0.0268],
        }
    ).to_csv(macro_path, index=False)

    monkeypatch.setattr(
        global_macro,
        "_load_shiller_sheet",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(global_macro, "fetch_historical_fred_series", lambda *_args, **_kwargs: None)
    monkeypatch.setenv("MACRO_DATA_PATH", str(macro_path))

    with caplog.at_level(logging.INFO):
        snapshot = global_macro.fetch_shiller_ttm_eps()

    assert snapshot["erp"] == 0.0268
    assert snapshot["source"] == "derived:macro_history_cache"
    assert snapshot["degraded"] is True
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_fetch_net_liquidity_snapshot_normalizes_observation_date_dtype(monkeypatch):
    walcl = pd.DataFrame(
        {
            "observation_date": pd.to_datetime(["2026-04-02", "2026-04-09"]),
            "WALCL": [9000.0, 9100.0],
        }
    )
    tga = pd.DataFrame(
        {
            "observation_date": ["2026-04-02", "2026-04-09"],
            "WDTGAL": [500.0, 450.0],
        }
    )
    rrp = pd.DataFrame(
        {
            "observation_date": pd.to_datetime(["2026-04-02", "2026-04-09"]),
            "RRPONTSYD": [100.0, 90.0],
        }
    )

    def fake_fetch(series_id: str):
        if series_id == "WALCL":
            return walcl.copy()
        if series_id == "WDTGAL":
            return tga.copy()
        if series_id == "RRPONTSYD":
            return rrp.copy()
        raise AssertionError(series_id)

    monkeypatch.setattr(macro_v3, "fetch_fred_data", fake_fetch)

    snapshot = macro_v3.fetch_net_liquidity_snapshot()

    assert snapshot["degraded"] is False
    assert snapshot["source"] == "derived:fred:WALCL-WDTGAL-RRPONTSYD"
    assert snapshot["value"] == -81.35
    assert snapshot["roc"] == 0.0
