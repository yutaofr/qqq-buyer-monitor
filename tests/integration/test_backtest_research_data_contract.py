from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from src.backtest import Backtester, run_backtest, run_signal_audits
from src.collector.historical_macro_seeder import HistoricalMacroSeeder


def _canonical_macro_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "observation_date": ["2024-01-02", "2024-01-03"],
            "effective_date": ["2024-01-03", "2024-01-04"],
            "credit_spread_bps": [350.0, 360.0],
            "credit_acceleration_pct_10d": [0.0, 0.8],
            "real_yield_10y_pct": [1.25, 1.20],
            "net_liquidity_usd_bn": [250.0, 249.0],
            "liquidity_roc_pct_4w": [0.0, -0.4],
            "funding_stress_flag": [0, 1],
            "source_credit_spread": ["fred:BAMLH0A0HYM2", "fred:BAMLH0A0HYM2"],
            "source_real_yield": ["fred:DFII10", "fred:DFII10"],
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
            "is_funding_stressed": [True, True],
        }
    )


def test_backtester_can_use_canonical_macro_seeder(tmp_path):
    prices = pd.Series(
        [100.0, 101.0, 102.0],
        index=pd.date_range("2024-01-02", periods=3, freq="B"),
    )
    ohlcv = pd.DataFrame({"Close": prices}, index=prices.index)
    csv_path = tmp_path / "canonical_macro.csv"
    _canonical_macro_frame().to_csv(csv_path, index=False)
    seeder = HistoricalMacroSeeder(csv_path=str(csv_path))

    summary = Backtester(initial_capital=10000).simulate_portfolio(ohlcv, macro_seeder=seeder)

    assert len(summary.daily_timeseries) == 3
    assert summary.daily_timeseries["nav"].notna().all()
    assert summary.daily_timeseries["state"].notna().all()


def test_legacy_macro_file_is_rejected_by_seeder(tmp_path):
    csv_path = tmp_path / "legacy_macro.csv"
    _legacy_macro_frame().to_csv(csv_path, index=False)

    with pytest.raises(ValueError, match="credit_spread_bps"):
        HistoricalMacroSeeder(csv_path=str(csv_path))


def test_run_backtest_prints_macro_coverage_before_summary(monkeypatch, capsys):
    qqq = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [101.0, 102.0],
            "Low": [99.0, 100.0],
            "Close": [100.5, 101.5],
            "Volume": [1_000_000, 1_100_000],
        },
        index=pd.Index(["2024-01-02", "2024-01-03"], name="date"),
    )
    macro = _canonical_macro_frame()
    events: list[str] = []

    def fake_exists(path):
        return True

    def fake_macro_exists(self):
        return True

    def fake_read_csv(path, *args, **kwargs):
        if str(path) == "data/qqq_history_cache.csv":
            return qqq.copy()
        if str(path) == "data/macro_historical_dump.csv":
            return macro.copy()
        raise AssertionError(f"unexpected path: {path}")

    def fake_simulate(self, *args, **kwargs):
        events.append("simulate")
        return SimpleNamespace(
            events=(),
            tactical_mdd=-0.10,
            baseline_mdd=-0.20,
            signal_beta=0.50,
            realized_beta=0.50,
            turnover=1.0,
            nav_integrity=1.0,
            interval_beta_audit=[],
            mean_interval_beta_deviation=0.01,
            forward_returns_by_horizon={5: 0.01, 20: 0.02, 60: 0.03},
            max_adverse_excursion=-0.05,
            average_cost_improvement_vs_baseline_dca=0.0,
        )

    def fake_build_signal_timeseries(self, *args, **kwargs):
        events.append("signal-timeseries")
        return pd.DataFrame(
            {
                "close": [100.5, 101.5],
                "signal_target_beta": [0.5, 0.5],
            },
            index=pd.to_datetime(["2024-01-02", "2024-01-03"], utc=True),
        )

    def fake_save_beta_backtest_figure(*args, **kwargs):
        events.append("save-figure")
        return []

    monkeypatch.setattr("src.backtest.os.path.exists", fake_exists)
    monkeypatch.setattr("src.backtest.Path.exists", fake_macro_exists)
    monkeypatch.setattr("src.backtest.pd.read_csv", fake_read_csv)
    monkeypatch.setattr("src.backtest.Backtester.simulate_portfolio", fake_simulate)
    monkeypatch.setattr("src.backtest.Backtester.build_signal_timeseries", fake_build_signal_timeseries)
    monkeypatch.setattr("src.backtest.save_beta_backtest_figure", fake_save_beta_backtest_figure)

    run_backtest()

    output = capsys.readouterr().out
    assert output.index("--- Canonical Macro Coverage ---") < output.index("--- v8.1 Linear Pipeline Backtest Summary")
    assert events == ["simulate", "signal-timeseries", "save-figure"]


def test_run_backtest_reports_authorized_and_unauthorized_crisis_metrics(monkeypatch, capsys):
    qqq = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [101.0, 102.0],
            "Low": [99.0, 100.0],
            "Close": [100.5, 101.5],
            "Volume": [1_000_000, 1_100_000],
        },
        index=pd.Index(["2024-01-02", "2024-01-03"], name="date"),
    )
    macro = _canonical_macro_frame()

    def fake_exists(path):
        return True

    def fake_macro_exists(self):
        return True

    def fake_read_csv(path, *args, **kwargs):
        if str(path) == "data/qqq_history_cache.csv":
            return qqq.copy()
        if str(path) == "data/macro_historical_dump.csv":
            return macro.copy()
        raise AssertionError(f"unexpected path: {path}")

    def fake_simulate(self, *args, **kwargs):
        daily_ts = pd.DataFrame(
            {
                "tier0_regime": ["CRISIS", "CRISIS", "NEUTRAL"],
                "deployment_state": ["DEPLOY_FAST", "DEPLOY_PAUSE", "DEPLOY_BASE"],
                "blood_chip_override_active": [True, False, False],
                "nav": [10_000.0, 10_050.0, 10_100.0],
                "close": [100.5, 101.0, 101.5],
                "state": ["BASE_DCA", "BASE_DCA", "BASE_DCA"],
            },
            index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
        )
        return SimpleNamespace(
            events=(),
            tactical_mdd=-0.10,
            baseline_mdd=-0.20,
            signal_beta=0.50,
            realized_beta=0.50,
            turnover=1.0,
            raw_turnover=1.5,
            estimated_cost_drag=0.01,
            nav_integrity=1.0,
            interval_beta_audit=[],
            mean_interval_beta_deviation=0.01,
            forward_returns_by_horizon={5: 0.01, 20: 0.02, 60: 0.03},
            max_adverse_excursion=-0.05,
            average_cost_improvement_vs_baseline_dca=0.0,
            daily_timeseries=daily_ts,
        )

    def fake_build_signal_timeseries(self, *args, **kwargs):
        return pd.DataFrame(
            {
                "close": [100.5, 101.5],
                "signal_target_beta": [0.5, 0.5],
            },
            index=pd.to_datetime(["2024-01-02", "2024-01-03"], utc=True),
        )

    def fake_save_beta_backtest_figure(*args, **kwargs):
        return []

    monkeypatch.setattr("src.backtest.os.path.exists", fake_exists)
    monkeypatch.setattr("src.backtest.Path.exists", fake_macro_exists)
    monkeypatch.setattr("src.backtest.pd.read_csv", fake_read_csv)
    monkeypatch.setattr("src.backtest.Backtester.simulate_portfolio", fake_simulate)
    monkeypatch.setattr("src.backtest.Backtester.build_signal_timeseries", fake_build_signal_timeseries)
    monkeypatch.setattr("src.backtest.save_beta_backtest_figure", fake_save_beta_backtest_figure)

    run_backtest()

    output = capsys.readouterr().out
    assert "CRISIS blood-chip overrides: 1" in output
    assert "CRISIS unauthorized breaches: 0" in output


def test_run_signal_audits_returns_dual_alignment_summaries(tmp_path, capsys):
    dates = pd.date_range("2024-01-02", periods=9, freq="B")
    qqq = pd.DataFrame({"Close": [100.0, 89.0, 79.0, 75.0, 70.0, 68.0, 67.0, 66.0, 65.0]}, index=dates)
    cache_path = tmp_path / "qqq_history_cache.csv"
    qqq.to_csv(cache_path)

    macro = pd.DataFrame(
        {
            "observation_date": [d.strftime("%Y-%m-%d") for d in dates],
            "effective_date": [d.strftime("%Y-%m-%d") for d in dates],
            "credit_spread_bps": [260.0, 260.0, 260.0, 320.0, 320.0, 680.0, 680.0, 680.0, 680.0],
            "credit_acceleration_pct_10d": [0.0] * len(dates),
            "real_yield_10y_pct": [1.25] * len(dates),
            "net_liquidity_usd_bn": [250.0] * len(dates),
            "liquidity_roc_pct_4w": [0.0] * len(dates),
            "funding_stress_flag": [0] * len(dates),
            "source_credit_spread": ["fred:BAMLH0A0HYM2"] * len(dates),
            "source_real_yield": ["fred:DFII10"] * len(dates),
            "source_net_liquidity": ["derived:WALCL-WDTGAL-RRPONTSYD"] * len(dates),
            "source_funding_stress": ["fred:NFCI"] * len(dates),
            "build_version": ["v7.0-class-a-research-r1"] * len(dates),
        }
    )
    macro_path = tmp_path / "macro_historical_dump.csv"
    macro.to_csv(macro_path, index=False)

    expectations = pd.DataFrame(
        {
            "date": dates,
            "expected_target_beta": [1.2, 1.2, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
            "expected_deployment_state": [
                "DEPLOY_BASE",
                "DEPLOY_FAST",
                "DEPLOY_SLOW",
                "DEPLOY_PAUSE",
                "DEPLOY_PAUSE",
                "DEPLOY_PAUSE",
                "DEPLOY_PAUSE",
                "DEPLOY_PAUSE",
                "DEPLOY_PAUSE",
            ],
        }
    )
    expectation_path = tmp_path / "expectations.csv"
    expectations.to_csv(expectation_path, index=False)

    results = run_signal_audits(
        str(expectation_path),
        cache_path=str(cache_path),
        macro_path=str(macro_path),
        registry_path="data/candidate_registry_v7.json",
    )

    output = capsys.readouterr().out
    assert "--- Target Beta Alignment Audit ---" in output
    assert "--- Deployment Alignment Audit ---" in output
    assert set(results) == {"beta", "deployment"}
    assert results["beta"].mean_absolute_error == pytest.approx(0.0)
    assert results["deployment"].exact_match_ratio == pytest.approx(1.0)


def test_run_signal_audits_rejects_synthetic_macro_dataset_for_acceptance(tmp_path):
    dates = pd.date_range("2024-01-02", periods=2, freq="B")
    qqq = pd.DataFrame({"Close": [100.0, 99.0]}, index=dates)
    cache_path = tmp_path / "qqq_history_cache.csv"
    qqq.to_csv(cache_path)

    macro = pd.DataFrame(
        {
            "observation_date": [d.strftime("%Y-%m-%d") for d in dates],
            "effective_date": [d.strftime("%Y-%m-%d") for d in dates],
            "credit_spread_bps": [350.0, 350.0],
            "credit_acceleration_pct_10d": [0.0, 0.0],
            "real_yield_10y_pct": [1.5, 1.5],
            "net_liquidity_usd_bn": [250.0, 250.0],
            "liquidity_roc_pct_4w": [0.0, 0.0],
            "funding_stress_flag": [0, 0],
            "source_credit_spread": ["synthetic_fixture", "synthetic_fixture"],
            "source_real_yield": ["synthetic_fixture", "synthetic_fixture"],
            "source_net_liquidity": ["synthetic_fixture", "synthetic_fixture"],
            "source_funding_stress": ["synthetic_fixture", "synthetic_fixture"],
            "build_version": ["dev-fixture", "dev-fixture"],
        }
    )
    macro_path = tmp_path / "macro_historical_dump.csv"
    macro.to_csv(macro_path, index=False)

    expectations = pd.DataFrame(
        {
            "date": dates,
            "expected_target_beta": [0.5, 0.5],
        }
    )
    expectation_path = tmp_path / "expectations.csv"
    expectations.to_csv(expectation_path, index=False)

    with pytest.raises(ValueError, match="non-synthetic macro dataset"):
        run_signal_audits(
            str(expectation_path),
            mode="beta",
            cache_path=str(cache_path),
            macro_path=str(macro_path),
            registry_path="data/candidate_registry_v7.json",
        )


def test_run_backtest_rejects_synthetic_macro_dataset_for_acceptance(monkeypatch):
    qqq_cache_frame = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [101.0, 102.0],
            "Low": [99.0, 100.0],
            "Close": [100.5, 101.5],
            "Volume": [1_000_000, 1_100_000],
        },
        index=pd.Index(["2024-01-02", "2024-01-03"], name="date"),
    )
    synthetic_macro = pd.DataFrame(
        {
            "observation_date": ["2024-01-02", "2024-01-03"],
            "effective_date": ["2024-01-03", "2024-01-04"],
            "credit_spread_bps": [350.0, 350.0],
            "credit_acceleration_pct_10d": [0.0, 0.0],
            "real_yield_10y_pct": [1.5, 1.5],
            "net_liquidity_usd_bn": [250.0, 250.0],
            "liquidity_roc_pct_4w": [0.0, 0.0],
            "funding_stress_flag": [0, 0],
            "source_credit_spread": ["synthetic_fixture", "synthetic_fixture"],
            "source_real_yield": ["synthetic_fixture", "synthetic_fixture"],
            "source_net_liquidity": ["synthetic_fixture", "synthetic_fixture"],
            "source_funding_stress": ["synthetic_fixture", "synthetic_fixture"],
            "build_version": ["dev-fixture", "dev-fixture"],
        }
    )

    def fake_exists(path):
        return True

    def fake_macro_exists(self):
        return True

    def fake_read_csv(path, *args, **kwargs):
        if str(path) == "data/qqq_history_cache.csv":
            return qqq_cache_frame.copy()
        if str(path) == "data/macro_historical_dump.csv":
            return synthetic_macro.copy()
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr("src.backtest.os.path.exists", fake_exists)
    monkeypatch.setattr("src.backtest.Path.exists", fake_macro_exists)
    monkeypatch.setattr("src.backtest.pd.read_csv", fake_read_csv)

    with pytest.raises(ValueError, match="non-synthetic macro dataset"):
        run_backtest()
