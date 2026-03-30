from types import SimpleNamespace

import pandas as pd
import pytest

from scripts import generate_historical_macro
from src.collector import macro, macro_v3
from src.collector.historical_macro_seeder import HistoricalMacroSeeder
from src.research import historical_macro_builder as builder
from src.research.data_contracts import (
    REQUIRED_HISTORICAL_MACRO_COLUMNS,
    validate_historical_macro_frame,
)
from src.research.valuation_history import parse_damodaran_histimpl_html


def _primary_series_frame(series_id: str, values: list[float], dates: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "observation_date": dates,
            series_id: values,
        }
    )


def _canonical_macro_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "observation_date": ["2024-01-02", "2024-01-03"],
            "effective_date": ["2024-01-03", "2024-01-04"],
            "credit_spread_bps": [350.0, 355.0],
            "credit_acceleration_pct_10d": [0.0, 0.5],
            "forward_pe": [24.0, 23.5],
            "erp_pct": [3.8, 3.9],
            "real_yield_10y_pct": [1.25, 1.20],
            "nfci_raw": [-0.1, -0.2],
            "net_liquidity_usd_bn": [250.0, 249.0],
            "liquidity_roc_pct_4w": [0.0, -0.4],
            "funding_stress_flag": [0, 1],
            "source_credit_spread": ["fred:BAMLH0A0HYM2", "fred:BAMLH0A0HYM2"],
            "source_forward_pe": ["damodaran:histimpl", "damodaran:histimpl"],
            "source_erp": ["damodaran:histimpl", "damodaran:histimpl"],
            "source_real_yield": ["fred:DFII10", "fred:DFII10"],
            "source_nfci": ["fred:NFCI", "fred:NFCI"],
            "source_net_liquidity": ["derived:WALCL-WDTGAL-RRPONTSYD", "derived:WALCL-WDTGAL-RRPONTSYD"],
            "source_funding_stress": ["fred:NFCI", "fred:NFCI"],
            "build_version": ["v7.0-class-a-research-r1", "v7.0-class-a-research-r1"],
        }
    )


def _legacy_macro_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "observation_date": ["2024-01-02", "2024-01-03"],
            "BAMLH0A0HYM2": [3.5, 3.6],
            "liquidity_roc": [-3.0, -2.5],
            "is_funding_stressed": [False, True],
        }
    )


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


def test_fetch_fred_csv_limits_historical_window(monkeypatch):
    requested_urls: list[str] = []

    class _Response:
        text = "observation_date,DFII10\n2024-01-03,1.40\n"

        def raise_for_status(self):
            return None

    def fake_get(url: str, timeout: int = 15, headers: dict | None = None):
        requested_urls.append(url)
        return _Response()

    monkeypatch.setattr(macro.requests, "get", fake_get)

    frame = macro.fetch_fred_csv("DFII10", timeout=3, retries=0)

    assert frame is not None
    assert requested_urls
    assert "cosd=1990-01-01" in requested_urls[0]


def test_fetch_fred_csv_falls_back_to_curl_after_requests_timeout(monkeypatch):
    class _Completed:
        stdout = "observation_date,DFII10\n2024-01-03,1.40\n"

    def fake_get(url: str, timeout: int = 15, headers: dict | None = None):
        raise macro.requests.Timeout("timed out")

    def fake_run(cmd: list[str], capture_output: bool, text: bool, check: bool, timeout: int):
        assert cmd[0] == "curl"
        return _Completed()

    monkeypatch.setattr(macro.requests, "get", fake_get)
    monkeypatch.setattr(macro, "subprocess", SimpleNamespace(run=fake_run), raising=False)
    monkeypatch.setattr(macro.time, "sleep", lambda *_args, **_kwargs: None)

    frame = macro.fetch_fred_csv("DFII10", timeout=3, retries=0)

    assert frame is not None
    assert frame.iloc[0]["DFII10"] == 1.4


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


def test_parse_damodaran_histimpl_html_derives_forward_pe_and_erp():
    html = """
    <table>
      <tr>
        <th>Year</th><th>Earnings Yield</th><th>Dividend Yield</th><th>S&amp;P 500</th>
        <th>Earnings*</th><th>Dividends*</th><th>T.Bond Rate</th><th>Smoothed Growth</th><th>Implied ERP (FCFE)</th>
      </tr>
      <tr>
        <td>2023</td><td>4.64%</td><td>1.47%</td><td>4769.83</td><td>221.36</td><td>70.07</td><td>3.88%</td><td>3.68%</td><td>4.60%</td>
      </tr>
      <tr>
        <td>2024</td><td>4.14%</td><td>1.25%</td><td>5881.63</td><td>243.32</td><td>73.40</td><td>4.58%</td><td>4.61%</td><td>4.33%</td>
      </tr>
    </table>
    """

    frame = parse_damodaran_histimpl_html(html)

    assert list(frame.columns) == [
        "observation_date",
        "effective_date",
        "forward_pe",
        "erp_pct",
        "source_forward_pe",
        "source_erp",
    ]
    assert frame["observation_date"].tolist() == [
        pd.Timestamp("2023-12-31"),
        pd.Timestamp("2024-12-31"),
    ]
    assert frame["effective_date"].tolist() == [
        pd.Timestamp("2024-01-01"),
        pd.Timestamp("2025-01-01"),
    ]
    assert frame["forward_pe"].iloc[0] == pytest.approx(100.0 / 4.64, rel=1e-4)
    assert frame["erp_pct"].iloc[1] == pytest.approx(4.33)
    assert frame["source_forward_pe"].eq("damodaran:histimpl").all()
    assert frame["source_erp"].eq("damodaran:histimpl").all()


def test_build_historical_macro_dataset_derives_canonical_fields(monkeypatch, tmp_path):
    dates = pd.date_range("2024-01-01", periods=15, freq="B")
    walcl_dates = pd.date_range("2023-12-27", periods=6, freq="W-WED")
    bundle = {
        "BAMLH0A0HYM2": _primary_series_frame(
            "BAMLH0A0HYM2",
            [1.00, 1.01, 1.02, 1.03, 1.05, 1.07, 1.08, 1.09, 1.10, 1.11, 1.13, 1.14, 1.15, 1.16, 1.18],
            dates,
        ),
        "DFII10": _primary_series_frame(
            "DFII10",
            [2.10 + i * 0.01 for i in range(15)],
            dates,
        ),
        "WALCL": _primary_series_frame(
            "WALCL",
            [8000000.0, 8001000.0, 8002500.0, 8004000.0, 8005200.0, 8007000.0],
            walcl_dates,
        ),
        "WDTGAL": _primary_series_frame(
            "WDTGAL",
            [500000.0, 500100.0, 500150.0, 500200.0, 500250.0, 500300.0],
            walcl_dates,
        ),
        "RRPONTSYD": _primary_series_frame(
            "RRPONTSYD",
            [1000.0, 1010.0, 1020.0, 1030.0, 1040.0, 1050.0],
            walcl_dates,
        ),
        "NFCI": _primary_series_frame(
            "NFCI",
            [-0.10, -0.08, -0.05, 0.05, 0.12, 0.15, 0.09, 0.02, -0.01, -0.03, -0.05, -0.06, -0.04, -0.02, 0.01],
            dates,
        ),
    }
    monkeypatch.setattr(
        macro_v3,
        "fetch_research_historical_primary_series",
        lambda: bundle,
    )
    monkeypatch.setattr(
        builder,
        "fetch_historical_valuation_proxy",
        lambda: pd.DataFrame(
            {
                "observation_date": [pd.Timestamp("2023-12-31"), pd.Timestamp("2024-12-31")],
                "effective_date": [pd.Timestamp("2024-01-01"), pd.Timestamp("2025-01-01")],
                "forward_pe": [24.0, 20.0],
                "erp_pct": [3.8, 4.4],
                "source_forward_pe": ["damodaran:histimpl", "damodaran:histimpl"],
                "source_erp": ["damodaran:histimpl", "damodaran:histimpl"],
            }
        ),
    )

    output_path = tmp_path / "macro_historical_dump.csv"
    df = builder.build_historical_macro_dataset(output_path=str(output_path))

    assert output_path.exists()
    assert list(df.columns) == [
        "observation_date",
        "effective_date",
        "credit_spread_bps",
        "credit_acceleration_pct_10d",
        "forward_pe",
        "erp_pct",
        "real_yield_10y_pct",
        "nfci_raw",
        "net_liquidity_usd_bn",
        "liquidity_roc_pct_4w",
        "funding_stress_flag",
        "source_credit_spread",
        "source_forward_pe",
        "source_erp",
        "source_real_yield",
        "source_nfci",
        "source_net_liquidity",
        "source_funding_stress",
        "build_version",
    ]
    assert (df["effective_date"] > df["observation_date"]).all()
    assert df["effective_date"].tolist()[0] == pd.Timestamp("2023-12-28")
    assert df["credit_spread_bps"].iloc[-1] == pytest.approx(118.0)
    assert pd.isna(df["credit_acceleration_pct_10d"].iloc[9])
    assert df["credit_acceleration_pct_10d"].iloc[-1] > 0
    assert df["forward_pe"].iloc[-1] == pytest.approx(24.0)
    assert df["erp_pct"].iloc[-1] == pytest.approx(3.8)
    assert df["liquidity_roc_pct_4w"].notna().any()
    assert df["funding_stress_flag"].isin([0, 1]).all()
    assert df["funding_stress_flag"].max() == 1
    assert df["source_forward_pe"].iloc[0] == "damodaran:histimpl"
    assert df["source_erp"].iloc[0] == "damodaran:histimpl"
    assert df["source_funding_stress"].iloc[0] == "fred:NFCI"
    assert df["build_version"].nunique() == 1


def test_build_historical_macro_dataset_raises_on_missing_core_series(monkeypatch):
    bundle = {
        "BAMLH0A0HYM2": _primary_series_frame("BAMLH0A0HYM2", [1.0, 1.1], pd.date_range("2024-01-01", periods=2, freq="B")),
        "DFII10": _primary_series_frame("DFII10", [2.0, 2.1], pd.date_range("2024-01-01", periods=2, freq="B")),
        "WALCL": _primary_series_frame("WALCL", [8000000.0, 8001000.0], pd.date_range("2023-12-27", periods=2, freq="W-WED")),
        "WDTGAL": _primary_series_frame("WDTGAL", [500000.0, 500100.0], pd.date_range("2023-12-27", periods=2, freq="W-WED")),
        "RRPONTSYD": _primary_series_frame("RRPONTSYD", [1000.0, 1005.0], pd.date_range("2023-12-27", periods=2, freq="W-WED")),
    }
    monkeypatch.setattr(
        macro_v3,
        "fetch_research_historical_primary_series",
        lambda: bundle,
    )
    monkeypatch.setattr(
        builder,
        "fetch_historical_valuation_proxy",
        lambda: pd.DataFrame(
            {
                "observation_date": [pd.Timestamp("2024-12-31")],
                "effective_date": [pd.Timestamp("2025-01-01")],
                "forward_pe": [20.0],
                "erp_pct": [4.4],
                "source_forward_pe": ["damodaran:histimpl"],
                "source_erp": ["damodaran:histimpl"],
            }
        ),
    )

    with pytest.raises(ValueError, match="NFCI"):
        builder.build_historical_macro_dataset()


def test_build_historical_macro_dataset_collapses_weekend_observations_to_unique_effective_dates(monkeypatch):
    daily_dates = pd.DatetimeIndex(
        [
            "2024-05-30",
            "2024-05-31",
            "2024-06-02",
            "2024-06-03",
            "2024-06-04",
        ]
    )
    weekly_dates = pd.date_range("2024-05-29", periods=2, freq="W-WED")
    bundle = {
        "BAMLH0A0HYM2": _primary_series_frame("BAMLH0A0HYM2", [3.0, 3.1, 3.2, 3.3, 3.4], daily_dates),
        "DFII10": _primary_series_frame("DFII10", [1.8, 1.7, 1.6, 1.5, 1.4], daily_dates),
        "WALCL": _primary_series_frame("WALCL", [8000000.0, 8001000.0], weekly_dates),
        "WDTGAL": _primary_series_frame("WDTGAL", [500000.0, 500500.0], weekly_dates),
        "RRPONTSYD": _primary_series_frame("RRPONTSYD", [1000.0, 1001.0], weekly_dates),
        "NFCI": _primary_series_frame("NFCI", [-0.2, -0.1, -0.1, 0.0, 0.1], daily_dates),
    }
    monkeypatch.setattr(
        macro_v3,
        "fetch_research_historical_primary_series",
        lambda: bundle,
    )
    monkeypatch.setattr(
        builder,
        "fetch_historical_valuation_proxy",
        lambda: pd.DataFrame(
            {
                "observation_date": [pd.Timestamp("2023-12-31")],
                "effective_date": [pd.Timestamp("2024-01-01")],
                "forward_pe": [22.0],
                "erp_pct": [4.0],
                "source_forward_pe": ["damodaran:histimpl"],
                "source_erp": ["damodaran:histimpl"],
            }
        ),
    )

    df = builder.build_historical_macro_dataset()

    effective_dates = pd.to_datetime(df["effective_date"])
    assert effective_dates.is_unique

    monday_row = df.loc[effective_dates == pd.Timestamp("2024-06-03")].iloc[0]
    assert pd.Timestamp(monday_row["observation_date"]) == pd.Timestamp("2024-06-02")


def test_historical_macro_seeder_uses_effective_date_visibility():
    seeder = HistoricalMacroSeeder(mock_df=_canonical_macro_frame())

    before_visible = seeder.get_features_for_date(pd.Timestamp("2024-01-02").date())
    assert before_visible["credit_spread"] is None
    assert before_visible["is_funding_stressed"] is False

    visible = seeder.get_features_for_date(pd.Timestamp("2024-01-03").date())
    assert visible["credit_spread"] == 350.0
    assert visible["credit_accel"] == 0.0
    assert visible["forward_pe"] == 24.0
    assert visible["erp"] == 3.8
    assert visible["real_yield"] == 1.25
    assert visible["liquidity_roc"] == 0.0
    assert visible["is_funding_stressed"] is False


def test_historical_macro_seeder_preserves_legacy_mock_df_path():
    seeder = HistoricalMacroSeeder(mock_df=_legacy_macro_frame())

    visible = seeder.get_features_for_date(pd.Timestamp("2024-01-03").date())
    assert visible["credit_spread"] == 3.6
    assert visible["credit_accel"] == 0.0
    assert visible["real_yield"] is None
    assert visible["liquidity_roc"] == -2.5
    assert visible["is_funding_stressed"] is True


def test_generate_dev_fixture_historical_macro_dataset_emits_canonical_schema(tmp_path):
    output_path = tmp_path / "macro_historical_dump.csv"

    frame = generate_historical_macro.build_dev_fixture_historical_macro_dataset(output_path=output_path)

    assert output_path.exists()
    assert list(frame.columns) == list(REQUIRED_HISTORICAL_MACRO_COLUMNS)
    assert frame["build_version"].nunique() == 1
    assert frame["build_version"].iat[0] == "dev-fixture"
    assert frame["source_credit_spread"].nunique() == 1
    assert frame["source_credit_spread"].iat[0] == "synthetic_fixture"
    assert frame["source_real_yield"].nunique() == 1
    assert frame["source_real_yield"].iat[0] == "synthetic_fixture"
    assert frame["source_net_liquidity"].nunique() == 1
    assert frame["source_net_liquidity"].iat[0] == "synthetic_fixture"
    assert frame["source_funding_stress"].nunique() == 1
    assert frame["source_funding_stress"].iat[0] == "synthetic_fixture"
    assert (pd.to_datetime(frame["effective_date"]) > pd.to_datetime(frame["observation_date"])).all()
    validate_historical_macro_frame(frame)


def test_generate_dev_fixture_historical_macro_dataset_writes_smokeable_rows(tmp_path):
    output_path = tmp_path / "macro_historical_dump.csv"

    frame = generate_historical_macro.build_dev_fixture_historical_macro_dataset(output_path=output_path)
    written = pd.read_csv(output_path)

    assert len(frame) == len(written)
    assert written["build_version"].eq("dev-fixture").all()
    assert written["source_credit_spread"].eq("synthetic_fixture").all()
    assert written["funding_stress_flag"].isin([0, 1]).all()
