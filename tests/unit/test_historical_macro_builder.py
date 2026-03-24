import pandas as pd
import pytest

from src.collector import macro, macro_v3


def test_normalize_fred_history_frame_converts_dates_and_values():
    raw = pd.DataFrame(
        {
            "date": ["2024-01-03", "2024-01-01"],
            "DFII10": ["1.40", "1.20"],
        }
    )

    frame = macro.normalize_fred_history_frame(raw, "DFII10")

    assert list(frame.columns) == ["observation_date", "DFII10"]
    assert frame["observation_date"].tolist() == [
        pd.Timestamp("2024-01-01"),
        pd.Timestamp("2024-01-03"),
    ]
    assert frame["DFII10"].tolist() == [1.2, 1.4]


def test_normalize_fred_history_frame_accepts_uppercase_date_header():
    raw = pd.DataFrame(
        {
            "DATE": ["2024-01-03", "2024-01-01"],
            "DFII10": ["1.40", "1.20"],
        }
    )

    frame = macro.normalize_fred_history_frame(raw, "DFII10")

    assert frame["observation_date"].tolist() == [
        pd.Timestamp("2024-01-01"),
        pd.Timestamp("2024-01-03"),
    ]
    assert frame["DFII10"].tolist() == [1.2, 1.4]


def test_fetch_historical_fred_series_does_not_use_proxy_fallbacks(monkeypatch):
    raw = pd.DataFrame(
        {
            "observation_date": ["2024-01-03"],
            "BAMLH0A0HYM2": ["3.75"],
        }
    )

    monkeypatch.setattr(macro, "fetch_fred_data", lambda series_id, timeout=15: raw)
    monkeypatch.setattr(macro, "fetch_chicago_fed_nfci", lambda: (_ for _ in ()).throw(AssertionError("unexpected fallback")))
    monkeypatch.setattr(macro, "fetch_treasury_yields", lambda: (_ for _ in ()).throw(AssertionError("unexpected fallback")))
    monkeypatch.setattr(macro, "fetch_hyg_proxy", lambda: (_ for _ in ()).throw(AssertionError("unexpected fallback")))

    frame = macro.fetch_historical_fred_series("BAMLH0A0HYM2")

    assert frame is not None
    assert frame.iloc[0]["BAMLH0A0HYM2"] == 3.75
    assert frame.iloc[0]["observation_date"] == pd.Timestamp("2024-01-03")


def test_fetch_research_historical_primary_series_returns_all_required_frames(monkeypatch):
    calls: list[str] = []

    def fake_fetch(series_id: str, timeout: int = 15):
        calls.append(series_id)
        raw = pd.DataFrame(
            {
                "observation_date": ["2024-01-02", "2024-01-01"],
                series_id: ["2.0", "1.0"],
            }
        )
        return macro.normalize_fred_history_frame(raw, series_id)

    monkeypatch.setattr(macro_v3, "fetch_historical_fred_series", fake_fetch)

    frames = macro_v3.fetch_research_historical_primary_series()

    assert tuple(calls) == macro_v3.RESEARCH_PRIMARY_SERIES + macro_v3.RESEARCH_OPTIONAL_SERIES
    assert set(frames) == set(macro_v3.RESEARCH_PRIMARY_SERIES + macro_v3.RESEARCH_OPTIONAL_SERIES)
    for series_id, frame in frames.items():
        assert list(frame.columns) == ["observation_date", series_id]
        assert frame[series_id].tolist() == [1.0, 2.0]
        assert frame["observation_date"].tolist() == [
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-01-02"),
        ]


def test_fetch_research_historical_primary_series_raises_on_missing_series(monkeypatch):
    def fake_fetch(series_id: str, timeout: int = 15):
        if series_id == "DFII10":
            return None
        if series_id == "CPFF":
            return None
        return pd.DataFrame(
            {
                "observation_date": ["2024-01-01"],
                series_id: ["1.0"],
            }
        )

    monkeypatch.setattr(macro_v3, "fetch_historical_fred_series", fake_fetch)

    with pytest.raises(ValueError, match="DFII10"):
        macro_v3.fetch_research_historical_primary_series()


def test_fetch_research_historical_primary_series_ignores_missing_cpff(monkeypatch):
    def fake_fetch(series_id: str, timeout: int = 15):
        if series_id == "CPFF":
            return None
        return pd.DataFrame(
            {
                "observation_date": ["2024-01-01"],
                series_id: ["1.0"],
            }
        )

    monkeypatch.setattr(macro_v3, "fetch_historical_fred_series", fake_fetch)

    frames = macro_v3.fetch_research_historical_primary_series()

    assert "CPFF" not in frames
    assert set(frames) == set(macro_v3.RESEARCH_PRIMARY_SERIES)
