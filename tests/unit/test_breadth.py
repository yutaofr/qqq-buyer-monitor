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


def test_fetch_breadth_tracks_ndx_concentration_provenance_independently(monkeypatch):
    idx = pd.date_range("2026-03-20", periods=60, freq="D")

    def fake_ticker(symbol: str):
        if symbol == "^ADD":
            return _TickerStub(pd.DataFrame({"Close": [250.0] * len(idx)}, index=idx))
        if symbol == "QQQ":
            qqq = pd.Series([100.0 + (i * 0.4) for i in range(len(idx))], index=idx)
            return _TickerStub(pd.DataFrame({"Close": qqq.values}, index=idx))
        if symbol == "QQEW":
            return _TickerStub(pd.DataFrame())
        return _TickerStub(pd.DataFrame())

    monkeypatch.setattr(breadth_module.yf, "Ticker", fake_ticker)

    payload = breadth_module.fetch_breadth(as_of=date(2026, 3, 30))

    assert payload["source"] == "observed:^ADD"
    assert payload["quality"] == 1.0
    assert payload["ndx_concentration"] is None
    assert payload["ndx_concentration_source"] == "unavailable:ndx_concentration"
    assert payload["ndx_concentration_quality"] == 0.0


def test_fetch_breadth_derives_proxy_ratio_from_qqq_qqew_when_add_tickers_fail(monkeypatch):
    idx = pd.date_range("2026-03-20", periods=60, freq="D")

    def fake_ticker(symbol: str):
        if symbol in {"^ADD", "^ADDN"}:
            return _TickerStub(pd.DataFrame())
        if symbol == "QQQ":
            qqq = pd.Series([100.0 + (i * 0.7) for i in range(len(idx))], index=idx)
            return _TickerStub(pd.DataFrame({"Close": qqq.values}, index=idx))
        if symbol == "QQEW":
            qqew = pd.Series([100.0 + (i * 0.15) for i in range(len(idx))], index=idx)
            return _TickerStub(pd.DataFrame({"Close": qqew.values}, index=idx))
        return _TickerStub(pd.DataFrame())

    monkeypatch.setattr(breadth_module.yf, "Ticker", fake_ticker)

    payload = breadth_module.fetch_breadth(as_of=date(2026, 3, 30))

    assert payload["source"] == "derived:qqq-qqew-breadth"
    assert payload["quality"] > 0.0
    assert payload["observed"] is True
    assert 0.0 < payload["adv_dec_ratio"] < 0.5
