from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.liquidity.data.price_loader import (
    _build_liquidity_mask,
    _build_listing_age_mask,
    _build_roster_mask,
    _fetch_price_history_ensemble,
    _fetch_price_history_ensemble_with_diagnostics,
    load_constituent_returns,
    load_constituent_returns_with_diagnostics,
    load_proxy_vintage_roster,
    select_active_proxy_tickers,
)


def test_load_proxy_vintage_roster_has_required_columns():
    roster = load_proxy_vintage_roster()

    assert {"effective_from", "effective_to", "ticker"} == set(roster.columns)
    assert pd.api.types.is_datetime64_any_dtype(roster["effective_from"])
    assert pd.api.types.is_datetime64_any_dtype(roster["effective_to"])
    assert not roster.empty


def test_select_active_proxy_tickers_filters_by_overlap():
    roster = pd.DataFrame(
        {
            "effective_from": pd.to_datetime(["2004-01-01", "2010-01-01"]),
            "effective_to": pd.to_datetime(["2009-12-31", "2099-12-31"]),
            "ticker": ["OLD", "NEW"],
        }
    )

    tickers = select_active_proxy_tickers(roster, "2008-01-01", "2008-12-31")

    assert tickers == ["OLD"]


def test_build_roster_mask_applies_time_bounded_membership():
    idx = pd.bdate_range("2020-01-01", periods=5)
    roster = pd.DataFrame(
        {
            "effective_from": pd.to_datetime(["2020-01-02"]),
            "effective_to": pd.to_datetime(["2020-01-03"]),
            "ticker": ["AAA"],
        }
    )

    mask = _build_roster_mask(idx, ["AAA", "BBB"], roster)

    assert bool(mask.loc["2020-01-01", "AAA"]) is False
    assert bool(mask.loc["2020-01-02", "AAA"]) is True
    assert bool(mask.loc["2020-01-03", "AAA"]) is True
    assert bool(mask.loc["2020-01-06", "AAA"]) is False
    assert mask["BBB"].sum() == 0


def test_build_listing_age_mask_requires_min_valid_history():
    idx = pd.bdate_range("2020-01-01", periods=5)
    closes = pd.DataFrame(
        {
            "AAA": [np.nan, 10.0, 10.5, 11.0, 11.5],
        },
        index=idx,
    )

    mask = _build_listing_age_mask(closes, min_listing_days=3)

    assert bool(mask.loc[idx[1], "AAA"]) is False
    assert bool(mask.loc[idx[2], "AAA"]) is False
    assert bool(mask.loc[idx[3], "AAA"]) is True
    assert bool(mask.loc[idx[4], "AAA"]) is True


def test_build_liquidity_mask_keeps_top_n_by_trailing_dollar_volume():
    idx = pd.bdate_range("2020-01-01", periods=4)
    closes = pd.DataFrame(
        {
            "AAA": [10.0, 10.0, 10.0, 10.0],
            "BBB": [10.0, 10.0, 10.0, 10.0],
        },
        index=idx,
    )
    volumes = pd.DataFrame(
        {
            "AAA": [100.0, 100.0, 100.0, 100.0],
            "BBB": [200.0, 200.0, 200.0, 200.0],
        },
        index=idx,
    )

    mask = _build_liquidity_mask(closes, volumes, liquidity_lookback=2, top_n=1)

    assert mask.loc[idx[0]].sum() == 0
    assert bool(mask.loc[idx[1], "AAA"]) is False
    assert bool(mask.loc[idx[1], "BBB"]) is True
    assert bool(mask.loc[idx[-1], "BBB"]) is True


def test_load_constituent_returns_applies_all_three_universe_filters(monkeypatch):
    idx = pd.bdate_range("2020-01-01", periods=5)
    columns = pd.MultiIndex.from_product(
        [["AAA", "BBB", "CCC"], ["Close", "Volume"]],
        names=["ticker", "field"],
    )
    data = pd.DataFrame(index=idx, columns=columns, dtype=float)

    data[("AAA", "Close")] = [10.0, 10.5, 11.0, 11.5, 12.0]
    data[("AAA", "Volume")] = [500.0, 500.0, 500.0, 500.0, 500.0]
    data[("BBB", "Close")] = [20.0, 20.5, 21.0, 21.5, 22.0]
    data[("BBB", "Volume")] = [1000.0, 1000.0, 1000.0, 1000.0, 1000.0]
    data[("CCC", "Close")] = [np.nan, np.nan, 30.0, 30.5, 31.0]
    data[("CCC", "Volume")] = [0.0, 0.0, 50.0, 50.0, 50.0]

    roster = pd.DataFrame(
        {
            "effective_from": pd.to_datetime(["2020-01-01", "2020-01-01", "2020-01-03"]),
            "effective_to": pd.to_datetime(["2020-12-31", "2020-12-31", "2020-12-31"]),
            "ticker": ["AAA", "BBB", "CCC"],
        }
    )

    monkeypatch.setattr("src.liquidity.data.price_loader.yf.download", lambda *args, **kwargs: data.copy())
    monkeypatch.setattr("src.liquidity.data.price_loader._read_ticker_cache", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.liquidity.data.price_loader._write_ticker_cache", lambda *args, **kwargs: None)

    returns = load_constituent_returns(
        "2020-01-01",
        "2020-01-31",
        tickers=["AAA", "BBB", "CCC"],
        top_n=1,
        roster=roster,
        min_listing_days=2,
        liquidity_lookback=2,
    )

    # BBB is the only liquid top-1 name after warm-up; AAA is filtered by liquidity.
    assert returns["AAA"].isna().all()
    assert returns.loc[idx[1], "BBB"] == pytest.approx((20.5 / 20.0) - 1.0)
    # CCC fails listing-age gate initially and then fails liquidity gate.
    assert returns["CCC"].isna().all()


def test_fetch_price_history_ensemble_uses_single_ticker_cache(tmp_path, monkeypatch):
    idx = pd.bdate_range("2020-01-01", periods=3)
    cached = pd.DataFrame(
        {
            "AAA_Open": [10.0, 10.1, 10.2],
            "AAA_Close": [10.0, 10.1, 10.2],
            "AAA_Volume": [100.0, 100.0, 100.0],
        },
        index=idx,
    )
    cache_dir = tmp_path / "yf"
    cache_dir.mkdir()
    cached.to_pickle(cache_dir / "AAA_2020-01-01_2020-01-31.pkl")

    columns = pd.MultiIndex.from_product([["BBB"], ["Open", "Close", "Volume"]])
    network = pd.DataFrame(index=idx, columns=columns, dtype=float)
    network[("BBB", "Open")] = [20.0, 20.1, 20.2]
    network[("BBB", "Close")] = [20.0, 20.1, 20.2]
    network[("BBB", "Volume")] = [200.0, 200.0, 200.0]

    calls = []

    def fake_download(tickers, **kwargs):
        calls.append(tuple(tickers))
        return network.copy()

    monkeypatch.setattr("src.liquidity.data.price_loader.yf.download", fake_download)

    out = _fetch_price_history_ensemble(
        ["AAA", "BBB"],
        "2020-01-01",
        "2020-01-31",
        chunk_size=10,
        max_retries=1,
        base_delay_seconds=0.0,
        jitter_seconds=0.0,
        cache_dir=cache_dir,
    )

    assert calls == [("BBB",)]
    assert {"AAA", "BBB"} == set(out.keys())
    assert out["AAA"].equals(cached)
    assert (cache_dir / "BBB_2020-01-01_2020-01-31.pkl").exists()


def test_fetch_price_history_ensemble_retries_then_succeeds(tmp_path, monkeypatch):
    idx = pd.bdate_range("2020-01-01", periods=3)
    columns = pd.MultiIndex.from_product([["AAA"], ["Open", "Close", "Volume"]])
    payload = pd.DataFrame(index=idx, columns=columns, dtype=float)
    payload[("AAA", "Open")] = [10.0, 10.1, 10.2]
    payload[("AAA", "Close")] = [10.0, 10.1, 10.2]
    payload[("AAA", "Volume")] = [100.0, 100.0, 100.0]

    calls = {"count": 0}
    sleeps = []

    def fake_download(tickers, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("429")
        return payload.copy()

    monkeypatch.setattr("src.liquidity.data.price_loader.yf.download", fake_download)
    monkeypatch.setattr("src.liquidity.data.price_loader.time.sleep", lambda x: sleeps.append(x))
    monkeypatch.setattr("src.liquidity.data.price_loader.random.uniform", lambda a, b: 0.0)

    out = _fetch_price_history_ensemble(
        ["AAA"],
        "2020-01-01",
        "2020-01-31",
        chunk_size=1,
        max_retries=2,
        base_delay_seconds=1.0,
        jitter_seconds=0.5,
        cache_dir=tmp_path / "yf",
    )

    assert calls["count"] == 2
    assert sleeps == [1.0]
    assert "AAA" in out


def test_fetch_price_history_ensemble_reports_failed_tickers(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.liquidity.data.price_loader.yf.download",
        lambda tickers, **kwargs: pd.DataFrame(),
    )

    _, diagnostics = _fetch_price_history_ensemble_with_diagnostics(
        ["AAA", "BBB"],
        "2020-01-01",
        "2020-01-31",
        chunk_size=2,
        max_retries=0,
        base_delay_seconds=0.0,
        jitter_seconds=0.0,
        cache_dir=tmp_path / "yf",
    )

    assert diagnostics["failed_tickers"] == ["AAA", "BBB"]
    assert diagnostics["downloaded_tickers"] == []


def test_fetch_price_history_ensemble_falls_back_to_single_ticker_download(tmp_path, monkeypatch):
    idx = pd.bdate_range("2020-01-01", periods=3)
    chunk_payload = pd.DataFrame()
    single_columns = pd.MultiIndex.from_product([["BBB"], ["Open", "Close", "Volume"]])
    single_payload = pd.DataFrame(index=idx, columns=single_columns, dtype=float)
    single_payload[("BBB", "Open")] = [20.0, 20.1, 20.2]
    single_payload[("BBB", "Close")] = [20.0, 20.1, 20.2]
    single_payload[("BBB", "Volume")] = [200.0, 200.0, 200.0]
    calls = []

    def fake_download(tickers, **kwargs):
        calls.append(tuple(tickers))
        if list(tickers) == ["AAA", "BBB"]:
            return chunk_payload
        if list(tickers) == ["BBB"]:
            return single_payload.copy()
        return pd.DataFrame()

    monkeypatch.setattr("src.liquidity.data.price_loader.yf.download", fake_download)

    out, diagnostics = _fetch_price_history_ensemble_with_diagnostics(
        ["AAA", "BBB"],
        "2020-01-01",
        "2020-01-31",
        chunk_size=2,
        max_retries=0,
        base_delay_seconds=0.0,
        jitter_seconds=0.0,
        cache_dir=tmp_path / "yf",
    )

    assert calls == [("AAA", "BBB"), ("AAA",), ("BBB",)]
    assert set(out) == {"BBB"}
    assert diagnostics["failed_tickers"] == ["AAA"]
    assert diagnostics["downloaded_tickers"] == ["BBB"]
    assert (tmp_path / "yf" / "BBB_2020-01-01_2020-01-31.pkl").exists()


def test_load_constituent_returns_with_diagnostics_reports_valid_names(monkeypatch):
    idx = pd.bdate_range("2020-01-01", periods=5)
    columns = pd.MultiIndex.from_product(
        [["AAA", "BBB"], ["Close", "Volume"]],
        names=["ticker", "field"],
    )
    data = pd.DataFrame(index=idx, columns=columns, dtype=float)
    data[("AAA", "Close")] = [10.0, 10.5, 11.0, 11.5, 12.0]
    data[("AAA", "Volume")] = [100.0, 100.0, 100.0, 100.0, 100.0]
    data[("BBB", "Close")] = [20.0, 20.5, 21.0, np.nan, np.nan]
    data[("BBB", "Volume")] = [100.0, 100.0, 100.0, np.nan, np.nan]

    roster = pd.DataFrame(
        {
            "effective_from": pd.to_datetime(["2020-01-01", "2020-01-01"]),
            "effective_to": pd.to_datetime(["2020-12-31", "2020-12-31"]),
            "ticker": ["AAA", "BBB"],
        }
    )
    monkeypatch.setattr("src.liquidity.data.price_loader.yf.download", lambda *args, **kwargs: data.copy())
    monkeypatch.setattr("src.liquidity.data.price_loader._read_ticker_cache", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.liquidity.data.price_loader._write_ticker_cache", lambda *args, **kwargs: None)

    returns, diagnostics = load_constituent_returns_with_diagnostics(
        "2020-01-01",
        "2020-01-31",
        tickers=["AAA", "BBB"],
        top_n=2,
        roster=roster,
        min_listing_days=1,
        liquidity_lookback=1,
    )

    assert list(diagnostics["valid_names"].index) == list(returns.index)
    assert diagnostics["valid_names"].iloc[0] == 2
    assert diagnostics["valid_names"].iloc[-1] == 1
