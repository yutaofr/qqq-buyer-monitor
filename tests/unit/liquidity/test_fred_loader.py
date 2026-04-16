from __future__ import annotations

import pandas as pd

from src.liquidity.data import fred_loader


def test_load_fred_series_normalizes_string_observation_dates(monkeypatch):
    raw = pd.DataFrame(
        {
            "observation_date": ["2020-01-01", "2020-01-02", "2020-01-03"],
            "WALCL": [1.0, 2.0, 3.0],
        }
    )
    monkeypatch.setattr(fred_loader, "fetch_fred_data", lambda _series_id: raw.copy())

    out = fred_loader.load_fred_series("WALCL", "2020-01-02", "2020-01-03")

    assert list(out["WALCL"]) == [2.0, 3.0]
    assert pd.api.types.is_datetime64_any_dtype(out["observation_date"])
    assert out["observation_date"].tolist() == [
        pd.Timestamp("2020-01-02"),
        pd.Timestamp("2020-01-03"),
    ]
