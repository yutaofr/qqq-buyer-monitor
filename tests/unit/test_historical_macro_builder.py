from types import SimpleNamespace

import pandas as pd
import pytest

from scripts import generate_historical_macro
from src.collector import global_macro, macro, macro_v3
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


def _v12_frame(value_column: str, values: list[float], observation_dates: list[str], effective_dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "observation_date": pd.to_datetime(observation_dates),
            "effective_date": pd.to_datetime(effective_dates),
            value_column: values,
        }
    )


def _canonical_macro_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "observation_date": ["2024-01-02", "2024-01-03"],
            "effective_date": ["2024-01-03", "2024-01-04"],
            "credit_spread_bps": [350.0, 355.0],
            "real_yield_10y_pct": [0.0125, 0.0120],
            "net_liquidity_usd_bn": [250.0, 249.0],
            "treasury_vol_21d": [0.0060, 0.0062],
            "copper_gold_ratio": [0.180, 0.181],
            "breakeven_10y": [0.021, 0.020],
            "core_capex_mm": [12.0, 12.0],
            "usdjpy": [148.0, 147.5],
            "erp_ttm_pct": [0.038, 0.038],
            "source_credit_spread": ["fred:BAMLH0A0HYM2", "fred:BAMLH0A0HYM2"],
            "source_real_yield": ["fred:DFII10", "fred:DFII10"],
            "source_net_liquidity": ["derived:WALCL-WDTGAL-RRPONTSYD"] * 2,
            "source_treasury_vol": ["direct:fred_dgs10"] * 2,
            "source_copper_gold": ["direct:yfinance"] * 2,
            "source_breakeven": ["direct:fred_t10yie"] * 2,
            "source_core_capex": ["direct:fred_neworder"] * 2,
            "source_usdjpy": ["direct:yfinance"] * 2,
            "source_erp_ttm": ["direct:shiller"] * 2,
            "build_version": ["v12.0-orthogonal-factor-r1"] * 2,
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
    assert frame["forward_pe"].iloc[0] == pytest.approx(100.0 / 4.64, rel=1e-4)
    assert frame["erp_pct"].iloc[1] == pytest.approx(4.33)


def test_build_historical_macro_dataset_derives_v12_canonical_fields(monkeypatch, tmp_path):
    weekly_dates = pd.date_range("2023-12-27", periods=6, freq="W-WED")
    monkeypatch.setattr(
        macro_v3,
        "fetch_research_historical_primary_series",
        lambda series_ids=builder._LIQUIDITY_SERIES: {
            "WALCL": _primary_series_frame("WALCL", [8000000.0, 8001000.0, 8002500.0, 8004000.0, 8005200.0, 8007000.0], weekly_dates),
            "WDTGAL": _primary_series_frame("WDTGAL", [500000.0, 500100.0, 500150.0, 500200.0, 500250.0, 500300.0], weekly_dates),
            "RRPONTSYD": _primary_series_frame("RRPONTSYD", [1000.0, 1010.0, 1020.0, 1030.0, 1040.0, 1050.0], weekly_dates),
        },
    )
    monkeypatch.setattr(
        global_macro,
        "fetch_v12_historical_series_bundle",
        lambda timeout=20: {
            "credit_spread": _primary_series_frame("BAMLH0A0HYM2", [1.00, 1.02, 1.04], pd.date_range("2024-01-01", periods=3, freq="B")),
            "real_yield": _primary_series_frame("real_yield_10y_pct", [0.012, 0.011, 0.010], pd.date_range("2024-01-01", periods=3, freq="B")),
            "treasury_vol": _v12_frame("treasury_vol_21d", [0.006, 0.007], ["2024-01-01", "2024-01-02"], ["2024-01-02", "2024-01-03"]),
            "breakeven": _v12_frame("breakeven_10y", [0.021, 0.020], ["2024-01-01", "2024-01-02"], ["2024-01-02", "2024-01-03"]),
            "capex": _v12_frame("core_capex_mm", [11.0, 15.0], ["2023-11-30", "2023-12-31"], ["2024-01-12", "2024-02-12"]),
            "copper_gold": _v12_frame("copper_gold_ratio", [0.18, 0.181], ["2024-01-01", "2024-01-02"], ["2024-01-02", "2024-01-03"]),
            "usdjpy": _v12_frame("usdjpy", [145.0, 146.0], ["2024-01-01", "2024-01-02"], ["2024-01-02", "2024-01-03"]),
            "erp_ttm": _v12_frame("erp_ttm_pct", [0.037, 0.038], ["2023-11-30", "2023-12-31"], ["2024-01-12", "2024-02-12"]),
        },
    )

    output_path = tmp_path / "macro_historical_dump.csv"
    df = builder.build_historical_macro_dataset(output_path=str(output_path))

    assert output_path.exists()
    validate_historical_macro_frame(df)
    assert all(column in df.columns for column in REQUIRED_HISTORICAL_MACRO_COLUMNS)
    assert df["build_version"].eq("v12.0-orthogonal-factor-r1").all()
    assert df["source_erp_ttm"].eq("direct:shiller").all()
    assert df["source_treasury_vol"].eq("direct:fred_dgs10").all()
    assert df["source_core_capex"].eq("direct:fred_neworder").all()
    assert df["source_usdjpy"].eq("direct:yfinance").all()
    jan_15 = df.loc[df["observation_date"] == pd.Timestamp("2024-01-15")].iloc[0]
    assert jan_15["core_capex_mm"] == pytest.approx(11.0)
    assert jan_15["erp_ttm_pct"] == pytest.approx(0.037)
    assert pd.isna(jan_15["forward_pe"])
    assert jan_15["source_forward_pe"] == "deprecated:v12"


def test_build_historical_macro_dataset_collapses_to_business_calendar(monkeypatch):
    weekly_dates = pd.date_range("2024-05-29", periods=2, freq="W-WED")
    monkeypatch.setattr(
        macro_v3,
        "fetch_research_historical_primary_series",
        lambda series_ids=builder._LIQUIDITY_SERIES: {
            "WALCL": _primary_series_frame("WALCL", [8000000.0, 8001000.0], weekly_dates),
            "WDTGAL": _primary_series_frame("WDTGAL", [500000.0, 500500.0], weekly_dates),
            "RRPONTSYD": _primary_series_frame("RRPONTSYD", [1000.0, 1001.0], weekly_dates),
        },
    )
    monkeypatch.setattr(
        global_macro,
        "fetch_v12_historical_series_bundle",
        lambda timeout=20: {
            "credit_spread": _primary_series_frame("BAMLH0A0HYM2", [3.0, 3.1, 3.2, 3.3, 3.4], pd.DatetimeIndex(["2024-05-30", "2024-05-31", "2024-06-02", "2024-06-03", "2024-06-04"])),
            "real_yield": _primary_series_frame("real_yield_10y_pct", [0.018, 0.017, 0.016, 0.015, 0.014], pd.DatetimeIndex(["2024-05-30", "2024-05-31", "2024-06-02", "2024-06-03", "2024-06-04"])),
            "treasury_vol": _v12_frame("treasury_vol_21d", [0.006], ["2024-05-31"], ["2024-06-03"]),
            "breakeven": _v12_frame("breakeven_10y", [0.021], ["2024-05-31"], ["2024-06-03"]),
            "capex": _v12_frame("core_capex_mm", [10.0], ["2024-04-30"], ["2024-06-03"]),
            "copper_gold": _v12_frame("copper_gold_ratio", [0.19], ["2024-05-31"], ["2024-06-03"]),
            "usdjpy": _v12_frame("usdjpy", [157.0], ["2024-05-31"], ["2024-06-03"]),
            "erp_ttm": _v12_frame("erp_ttm_pct", [0.031], ["2024-04-30"], ["2024-06-03"]),
        },
    )

    df = builder.build_historical_macro_dataset()

    observation_dates = pd.to_datetime(df["observation_date"])
    assert observation_dates.is_monotonic_increasing
    assert all(date.weekday() < 5 for date in observation_dates)


def test_historical_macro_seeder_uses_effective_date_visibility():
    seeder = HistoricalMacroSeeder(mock_df=_canonical_macro_frame())

    before_visible = seeder.get_features_for_date(pd.Timestamp("2024-01-02").date())
    assert before_visible["credit_spread"] is None
    assert before_visible["erp"] is None

    visible = seeder.get_features_for_date(pd.Timestamp("2024-01-03").date())
    assert visible["credit_spread"] == 350.0
    assert visible["erp"] == 0.038
    assert visible["treasury_vol"] == 0.006
    assert visible["core_capex"] == 12.0
    assert visible["usdjpy"] == 148.0


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
    assert frame["source_credit_spread"].eq("synthetic_fixture").all()
    assert frame["source_treasury_vol"].eq("synthetic_fixture").all()
    assert frame["source_erp_ttm"].eq("synthetic_fixture").all()
    validate_historical_macro_frame(frame)


def test_generate_dev_fixture_historical_macro_dataset_writes_smokeable_rows(tmp_path):
    output_path = tmp_path / "macro_historical_dump.csv"

    frame = generate_historical_macro.build_dev_fixture_historical_macro_dataset(output_path=output_path)
    written = pd.read_csv(output_path)

    assert len(frame) == len(written)
    assert written["build_version"].eq("dev-fixture").all()
    assert written["source_credit_spread"].eq("synthetic_fixture").all()
    assert written["source_erp_ttm"].eq("synthetic_fixture").all()
