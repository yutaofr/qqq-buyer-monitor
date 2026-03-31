"""Unit tests for the v11.5 Bayesian web exporter."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime

from src.models import SignalResult, TargetAllocationState
from src.output.web_exporter import MarketCursor, export_web_snapshot


def _v11_result() -> SignalResult:
    return SignalResult(
        date=date(2026, 3, 27),
        price=562.58,
        target_beta=0.91,
        probabilities={"MID_CYCLE": 0.82, "LATE_CYCLE": 0.15},
        entropy=0.17,
        stable_regime="MID_CYCLE",
        target_allocation=TargetAllocationState(0.10, 0.90, 0.0, 0.90),
        logic_trace=[{"step": "inference", "result": "MID_CYCLE"}],
        explanation="v11.5 placeholder",
        metadata={"feature_values": {"vix": 20.0}}
    )


def test_export_web_snapshot_v11_contract(tmp_path, monkeypatch):
    result = _v11_result()
    output_path = tmp_path / "status.json"

    # Mock market cursor to avoid mcal dependency issues in unit tests
    monkeypatch.setattr(MarketCursor, "get_market_state", lambda self, now: "FROZEN")
    monkeypatch.setattr(MarketCursor, "get_expires_at_utc", lambda self, now: datetime(2026, 3, 30, 17, 30, tzinfo=UTC))

    ok = export_web_snapshot(result, output_path=output_path)

    assert ok is True
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["meta"]["version"] == "v11.5"
    assert payload["signal"]["regime"] == "中期平稳 (MID_CYCLE)"
    assert payload["signal"]["target_beta"] == 0.91
    assert payload["signal"]["entropy"] == 0.17
    assert payload["signal"]["probabilities"]["MID_CYCLE"] == 0.82
    assert payload["evidence"]["feature_values"]["vix"] == 20.0
