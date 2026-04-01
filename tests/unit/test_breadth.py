from __future__ import annotations

from datetime import date

import pandas as pd

from src.collector import breadth as breadth_module


class _TickerStub:
    def __init__(self, history_frame: pd.DataFrame):
        self._history_frame = history_frame

    def history(self, *args, **kwargs):
        return self._history_frame.copy()


def test_fetch_breadth_marks_unavailable_when_breadth_tickers_fail(monkeypatch):
    def fake_ticker(symbol: str):
        if symbol in {"^ADD", "^ADDN"}:
            return _TickerStub(pd.DataFrame())
        if symbol == "QQEW":
            idx = pd.date_range("2026-03-20", periods=60, freq="D")
            return _TickerStub(pd.DataFrame({"Close": [100.0] * len(idx)}, index=idx))
        if symbol == "QQQ":
            idx = pd.date_range("2026-03-20", periods=60, freq="D")
            return _TickerStub(pd.DataFrame({"Close": [100.0] * len(idx)}, index=idx))
        return _TickerStub(pd.DataFrame())

    monkeypatch.setattr(breadth_module.yf, "Ticker", fake_ticker)

    payload = breadth_module.fetch_breadth(as_of=date(2026, 3, 30))

    assert payload["source"] == "unavailable:breadth"
    assert payload["quality"] == 0.0
    assert payload["observed"] is False
    assert payload["adv_dec_ratio"] == 0.50
    assert payload["pct_above_50d"] == 0.50
