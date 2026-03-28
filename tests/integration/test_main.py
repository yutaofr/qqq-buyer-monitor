from __future__ import annotations

import json
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from src.main import _history, run_pipeline
from src.models import (
    AllocationState,
    OptionsOverlay,
    Signal,
    SignalDetail,
    SignalResult,
    Tier1Result,
    Tier2Result,
)


def _detail(name: str, points: int = 0) -> SignalDetail:
    return SignalDetail(
        name=name,
        value=0.0,
        points=points,
        thresholds=(0.0, 0.0),
        triggered_half=False,
        triggered_full=False,
    )


def _fake_result(*, allocation_state: AllocationState, signal: Signal) -> SignalResult:
    tier1 = Tier1Result(
        score=20,
        drawdown_52w=_detail("drawdown_52w"),
        ma200_deviation=_detail("ma200_deviation"),
        vix=_detail("vix"),
        fear_greed=_detail("fear_greed"),
        breadth=_detail("breadth"),
        market_regime="NORMAL",
    )
    tier2 = Tier2Result(
        adjustment=0,
        put_wall=None,
        call_wall=None,
        gamma_flip=None,
        support_confirmed=False,
        support_broken=False,
        upside_open=False,
        gamma_positive=False,
        gamma_source="yfinance",
        put_wall_distance_pct=None,
        call_wall_distance_pct=None,
        overlay=OptionsOverlay(),
    )
    return SignalResult(
        date=date(2026, 3, 19),
        price=402.0,
        signal=signal,
        final_score=20,
        tier1=tier1,
        tier2=tier2,
        explanation="维持基础定投。",
        allocation_state=allocation_state,
        data_quality={},
    )


def test_main_json_reports_missing_live_features(monkeypatch, capsys):
    price_history = pd.DataFrame(
        {
            "Open": [400.0, 401.0],
            "High": [402.0, 403.0],
            "Low": [399.0, 400.0],
            "Close": [401.0, 402.0],
            "Volume": [1_000_000, 1_100_000],
        }
    )

    monkeypatch.setattr(
        "src.collector.price.fetch_price_data",
        lambda: {
            "date": date(2026, 3, 19),
            "price": 402.0,
            "ma200": 395.0,
            "high_52w": 450.0,
            "days_since_high": 30,
            "history": price_history,
        },
    )
    monkeypatch.setattr("src.collector.vix.fetch_vix", lambda: 25.0)
    monkeypatch.setattr("src.collector.fear_greed.fetch_fear_greed", lambda: 28)
    monkeypatch.setattr("src.collector.options.fetch_options_chain", lambda spot_price: None)
    monkeypatch.setattr(
        "src.collector.breadth.fetch_breadth",
        lambda: {"adv_dec_ratio": 0.45, "pct_above_50d": 0.3, "ndx_concentration": 0.0},
    )
    monkeypatch.setattr("src.collector.macro.fetch_credit_spread", lambda: 410.0)
    monkeypatch.setattr(
        "src.collector.fundamentals.fetch_forward_pe",
        lambda: {"trailing_pe": 28.0, "forward_pe": 24.5, "source": "test"},
    )
    monkeypatch.setattr("src.collector.macro_v3.fetch_real_yield", lambda: 1.8)
    monkeypatch.setattr("src.collector.macro_v3.fetch_fcf_yield", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_earnings_revisions_breadth", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_net_liquidity", lambda: (None, None))
    monkeypatch.setattr("src.collector.macro_v3.fetch_move_index", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_sector_rotation", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_short_volume_proxy", lambda: None)
    monkeypatch.setattr("src.store.db.load_latest_macro_state", lambda: None)
    monkeypatch.setattr("src.store.db.get_historical_series", lambda days=120: None)
    monkeypatch.setattr("src.store.db.load_history", lambda n=5: [])

    run_pipeline(SimpleNamespace(json=True, no_save=True, no_color=True))

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["data_quality"]["credit_spread"]["usable"] is True
    assert payload["data_quality"]["credit_spread"]["source"] == "live"
    assert payload["data_quality"]["credit_spread"]["stale_days"] == 0
    assert payload["data_quality"]["forward_pe"]["usable"] is True
    assert payload["data_quality"]["forward_pe"]["source"] == "live:test"
    assert payload["data_quality"]["forward_pe"]["stale_days"] == 0
    assert payload["data_quality"]["real_yield"]["usable"] is True
    assert payload["data_quality"]["real_yield"]["source"] == "live"
    assert payload["data_quality"]["real_yield"]["stale_days"] == 0
    assert payload["data_quality"]["fcf_yield"]["usable"] is False
    assert payload["data_quality"]["fcf_yield"]["source"] == "missing"
    assert payload["data_quality"]["earnings_revisions_breadth"]["usable"] is False
    assert payload["data_quality"]["earnings_revisions_breadth"]["source"] == "missing"
    assert payload["data_quality"]["short_vol_ratio"]["usable"] is False
    for meta in payload["data_quality"].values():
        assert set(meta) == {"value", "source", "usable", "stale_days", "category"}


def test_main_json_marks_cached_macro_values_stale(monkeypatch, capsys):
    price_history = pd.DataFrame(
        {
            "Open": [400.0, 401.0],
            "High": [402.0, 403.0],
            "Low": [399.0, 400.0],
            "Close": [401.0, 402.0],
            "Volume": [1_000_000, 1_100_000],
        }
    )

    monkeypatch.setattr(
        "src.collector.price.fetch_price_data",
        lambda: {
            "date": date(2026, 3, 19),
            "price": 402.0,
            "ma200": 395.0,
            "high_52w": 450.0,
            "days_since_high": 30,
            "history": price_history,
        },
    )
    monkeypatch.setattr("src.collector.vix.fetch_vix", lambda: 25.0)
    monkeypatch.setattr("src.collector.fear_greed.fetch_fear_greed", lambda: 28)
    monkeypatch.setattr("src.collector.options.fetch_options_chain", lambda spot_price: None)
    monkeypatch.setattr(
        "src.collector.breadth.fetch_breadth",
        lambda: {"adv_dec_ratio": 0.45, "pct_above_50d": 0.3, "ndx_concentration": 0.0},
    )

    def _macro_fail():
        raise RuntimeError("macro offline")

    def _fundamentals_fail():
        raise RuntimeError("fundamentals offline")

    monkeypatch.setattr("src.collector.macro.fetch_credit_spread", _macro_fail)
    monkeypatch.setattr("src.collector.fundamentals.fetch_forward_pe", _fundamentals_fail)
    monkeypatch.setattr("src.collector.macro_v3.fetch_real_yield", _macro_fail)
    monkeypatch.setattr("src.collector.macro_v3.fetch_fcf_yield", _macro_fail)
    monkeypatch.setattr("src.collector.macro_v3.fetch_earnings_revisions_breadth", _macro_fail)
    monkeypatch.setattr("src.collector.macro_v3.fetch_net_liquidity", lambda: (None, None))
    monkeypatch.setattr("src.collector.macro_v3.fetch_move_index", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_sector_rotation", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_short_volume_proxy", lambda: None)
    monkeypatch.setattr(
        "src.store.db.load_latest_macro_state",
        lambda: {
            "date": "2026-03-14",
            "credit_spread": 410.0,
            "forward_pe": 24.5,
            "real_yield": 1.8,
            "fcf_yield": 5.1,
            "earnings_revisions_breadth": 0.6,
        },
    )
    monkeypatch.setattr("src.store.db.get_historical_series", lambda days=120: None)
    monkeypatch.setattr("src.store.db.load_history", lambda n=5: [])

    run_pipeline(SimpleNamespace(json=True, no_save=True, no_color=True))

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["data_quality"]["credit_spread"]["source"] == "cache:macro_state"
    assert payload["data_quality"]["credit_spread"]["stale_days"] == 5
    assert payload["data_quality"]["forward_pe"]["source"] == "cache:macro_state"
    assert payload["data_quality"]["forward_pe"]["stale_days"] == 5
    assert payload["data_quality"]["real_yield"]["source"] == "cache:macro_state"
    assert payload["data_quality"]["real_yield"]["stale_days"] == 5
    assert payload["data_quality"]["fcf_yield"]["source"] == "cache:macro_state"
    assert payload["data_quality"]["fcf_yield"]["stale_days"] == 5
    assert payload["data_quality"]["earnings_revisions_breadth"]["source"] == "cache:macro_state"
    assert payload["data_quality"]["earnings_revisions_breadth"]["stale_days"] == 5


def test_main_json_runtime_trace_uses_v9_decision_chain(monkeypatch, capsys):
    price_history = pd.DataFrame(
        {
            "Open": [400.0, 401.0],
            "High": [402.0, 403.0],
            "Low": [399.0, 400.0],
            "Close": [401.0, 402.0],
            "Volume": [1_000_000, 1_100_000],
        }
    )

    monkeypatch.setattr(
        "src.collector.price.fetch_price_data",
        lambda: {
            "date": date(2026, 3, 19),
            "price": 402.0,
            "ma200": 395.0,
            "high_52w": 450.0,
            "days_since_high": 30,
            "history": price_history,
        },
    )
    monkeypatch.setattr("src.collector.vix.fetch_vix", lambda: 25.0)
    monkeypatch.setattr("src.collector.fear_greed.fetch_fear_greed", lambda: 28)
    monkeypatch.setattr("src.collector.options.fetch_options_chain", lambda spot_price: None)
    monkeypatch.setattr(
        "src.collector.breadth.fetch_breadth",
        lambda: {"adv_dec_ratio": 0.45, "pct_above_50d": 0.3, "ndx_concentration": 0.0},
    )
    monkeypatch.setattr("src.collector.macro.fetch_credit_spread", lambda: 470.0)
    monkeypatch.setattr(
        "src.collector.fundamentals.fetch_forward_pe",
        lambda: {"trailing_pe": 28.0, "forward_pe": 24.5, "source": "test"},
    )
    monkeypatch.setattr("src.collector.macro_v3.fetch_real_yield", lambda: 1.8)
    monkeypatch.setattr("src.collector.macro_v3.fetch_fcf_yield", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_earnings_revisions_breadth", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_net_liquidity", lambda: (None, None))
    monkeypatch.setattr("src.collector.macro_v3.fetch_move_index", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_sector_rotation", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_short_volume_proxy", lambda: None)
    monkeypatch.setattr("src.store.db.load_latest_macro_state", lambda: None)
    monkeypatch.setattr("src.store.db.get_historical_series", lambda days=120: None)
    monkeypatch.setattr("src.store.db.load_history", lambda n=5: [])

    run_pipeline(SimpleNamespace(json=True, no_save=True, no_color=True))

    payload = json.loads(capsys.readouterr().out)

    assert payload["explanation"].startswith("v9.0 target-beta-first")
    assert payload["tier0_regime"] == "RICH_TIGHTENING"
    assert payload["risk_state"] == "RISK_REDUCED"
    assert payload["target_exposure_ceiling"] == pytest.approx(0.8)
    assert payload["qld_share_ceiling"] == pytest.approx(0.1)
    steps = [step["step"] for step in payload["logic_trace"]]
    assert steps == [
        "tier0_regime",
        "risk_controller",
        "candidate_selection",
        "beta_advisory",
        "deployment_controller",
        "reference_path",
    ]
    assert "allocation_policy" not in steps
    assert "strategic_allocation" not in steps


def test_main_persists_runtime_inputs_when_saving(monkeypatch):
    price_history = pd.DataFrame(
        {
            "Open": [400.0, 401.0],
            "High": [402.0, 403.0],
            "Low": [399.0, 400.0],
            "Close": [401.0, 402.0],
            "Volume": [1_000_000, 1_100_000],
        }
    )
    persisted: dict[str, object] = {}

    monkeypatch.setattr(
        "src.collector.price.fetch_price_data",
        lambda: {
            "date": date(2026, 3, 19),
            "price": 402.0,
            "ma200": 395.0,
            "high_52w": 450.0,
            "days_since_high": 30,
            "history": price_history,
        },
    )
    monkeypatch.setenv("AVAILABLE_NEW_CASH", "1200")
    monkeypatch.setenv("PORTFOLIO_ROLLING_DRAWDOWN", "0.18")
    monkeypatch.setattr("src.collector.vix.fetch_vix", lambda: 25.0)
    monkeypatch.setattr("src.collector.fear_greed.fetch_fear_greed", lambda: 28)
    monkeypatch.setattr("src.collector.options.fetch_options_chain", lambda spot_price: None)
    monkeypatch.setattr(
        "src.collector.breadth.fetch_breadth",
        lambda: {"adv_dec_ratio": 0.45, "pct_above_50d": 0.3, "ndx_concentration": 0.0},
    )
    monkeypatch.setattr("src.collector.macro.fetch_credit_spread", lambda: 410.0)
    monkeypatch.setattr(
        "src.collector.fundamentals.fetch_forward_pe",
        lambda: {"trailing_pe": 28.0, "forward_pe": 24.5, "source": "test"},
    )
    monkeypatch.setattr("src.collector.macro_v3.fetch_real_yield", lambda: 1.8)
    monkeypatch.setattr("src.collector.macro_v3.fetch_fcf_yield", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_earnings_revisions_breadth", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_net_liquidity", lambda: (None, None))
    monkeypatch.setattr("src.collector.macro_v3.fetch_move_index", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_sector_rotation", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_short_volume_proxy", lambda: None)
    monkeypatch.setattr("src.store.db.load_latest_macro_state", lambda: None)
    monkeypatch.setattr("src.store.db.get_historical_series", lambda days=120: None)
    monkeypatch.setattr("src.store.db.load_history", lambda n=5: [])
    monkeypatch.setattr("src.store.db.load_runtime_inputs", lambda record_date, path="data/signals.db": None)
    monkeypatch.setattr("src.store.db.save_signal", lambda result: None)
    monkeypatch.setattr("src.store.db.save_macro_state", lambda **kwargs: None)
    monkeypatch.setattr(
        "src.store.db.save_runtime_inputs",
        lambda **kwargs: persisted.update(kwargs),
    )

    run_pipeline(SimpleNamespace(json=True, no_save=False, no_color=True))

    assert persisted["record_date"] == date(2026, 3, 19)
    assert persisted["available_new_cash"] == 1200.0
    assert persisted["rolling_drawdown"] == 0.18


def test_main_json_marks_cached_macro_state_with_cache_source_and_staleness(monkeypatch, capsys):
    price_history = pd.DataFrame(
        {
            "Open": [400.0, 401.0],
            "High": [402.0, 403.0],
            "Low": [399.0, 400.0],
            "Close": [401.0, 402.0],
            "Volume": [1_000_000, 1_100_000],
        }
    )

    monkeypatch.setattr(
        "src.collector.price.fetch_price_data",
        lambda: {
            "date": date(2026, 3, 19),
            "price": 402.0,
            "ma200": 395.0,
            "high_52w": 450.0,
            "days_since_high": 30,
            "history": price_history,
        },
    )
    monkeypatch.setattr("src.collector.vix.fetch_vix", lambda: 25.0)
    monkeypatch.setattr("src.collector.fear_greed.fetch_fear_greed", lambda: 28)
    monkeypatch.setattr("src.collector.options.fetch_options_chain", lambda spot_price: None)
    monkeypatch.setattr(
        "src.collector.breadth.fetch_breadth",
        lambda: {"adv_dec_ratio": 0.45, "pct_above_50d": 0.3, "ndx_concentration": 0.0},
    )
    monkeypatch.setattr("src.collector.macro.fetch_credit_spread", lambda: None)
    monkeypatch.setattr(
        "src.collector.fundamentals.fetch_forward_pe",
        lambda: {"trailing_pe": None, "forward_pe": None, "source": "test"},
    )
    monkeypatch.setattr("src.collector.macro_v3.fetch_real_yield", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_fcf_yield", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_earnings_revisions_breadth", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_net_liquidity", lambda: (None, None))
    monkeypatch.setattr("src.collector.macro_v3.fetch_move_index", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_sector_rotation", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_short_volume_proxy", lambda: None)
    monkeypatch.setattr(
        "src.store.db.load_latest_macro_state",
        lambda: {
            "date": "2026-03-17",
            "credit_spread": 410.0,
            "trailing_pe": 28.0,
            "forward_pe": 24.5,
            "real_yield": 1.8,
            "fcf_yield": 4.9,
            "earnings_revisions_breadth": 55.0,
        },
    )
    monkeypatch.setattr("src.store.db.get_historical_series", lambda days=120: None)
    monkeypatch.setattr("src.store.db.load_history", lambda n=5: [])

    run_pipeline(SimpleNamespace(json=True, no_save=True, no_color=True))

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["data_quality"]["credit_spread"]["source"] == "cache:macro_state"
    assert payload["data_quality"]["credit_spread"]["stale_days"] == 2
    assert payload["data_quality"]["forward_pe"]["source"] == "cache:macro_state"
    assert payload["data_quality"]["forward_pe"]["stale_days"] == 2
    assert payload["data_quality"]["real_yield"]["source"] == "cache:macro_state"
    assert payload["data_quality"]["real_yield"]["stale_days"] == 2
    assert payload["data_quality"]["fcf_yield"]["source"] == "cache:macro_state"
    assert payload["data_quality"]["fcf_yield"]["stale_days"] == 2
    assert payload["data_quality"]["earnings_revisions_breadth"]["source"] == "cache:macro_state"
    assert payload["data_quality"]["earnings_revisions_breadth"]["stale_days"] == 2


def test_main_compact_mode_uses_allocation_state(monkeypatch, capsys):
    price_history = pd.DataFrame(
        {
            "Open": [400.0, 401.0],
            "High": [402.0, 403.0],
            "Low": [399.0, 400.0],
            "Close": [401.0, 402.0],
            "Volume": [1_000_000, 1_100_000],
        }
    )

    monkeypatch.setattr(
        "src.collector.price.fetch_price_data",
        lambda: {
            "date": date(2026, 3, 19),
            "price": 402.0,
            "ma200": 395.0,
            "high_52w": 450.0,
            "days_since_high": 30,
            "history": price_history,
        },
    )
    monkeypatch.setattr("src.collector.vix.fetch_vix", lambda: 25.0)
    monkeypatch.setattr("src.collector.fear_greed.fetch_fear_greed", lambda: 28)
    monkeypatch.setattr("src.collector.options.fetch_options_chain", lambda spot_price: None)
    monkeypatch.setattr(
        "src.collector.breadth.fetch_breadth",
        lambda: {"adv_dec_ratio": 0.45, "pct_above_50d": 0.3, "ndx_concentration": 0.0},
    )
    monkeypatch.setattr("src.collector.macro.fetch_credit_spread", lambda: 410.0)
    monkeypatch.setattr(
        "src.collector.fundamentals.fetch_forward_pe",
        lambda: {"trailing_pe": 28.0, "forward_pe": 24.5, "source": "test"},
    )
    monkeypatch.setattr("src.collector.macro_v3.fetch_real_yield", lambda: 1.8)
    monkeypatch.setattr("src.collector.macro_v3.fetch_fcf_yield", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_earnings_revisions_breadth", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_net_liquidity", lambda: (None, None))
    monkeypatch.setattr("src.collector.macro_v3.fetch_move_index", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_sector_rotation", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_short_volume_proxy", lambda: None)
    monkeypatch.setattr("src.store.db.load_latest_macro_state", lambda: None)
    monkeypatch.setattr("src.store.db.get_historical_series", lambda days=120: None)
    monkeypatch.setattr(
        "src.store.db.load_history",
        lambda n=5: [
            {"signal": "WATCH", "allocation_state": "BASE_DCA"},
            {"signal": "TRIGGERED", "allocation_state": "BASE_DCA"},
            {"signal": "WATCH", "allocation_state": "BASE_DCA"},
        ],
    )
    monkeypatch.setattr(
        "src.engine.aggregator.aggregate",
        lambda *args, **kwargs: _fake_result(
            allocation_state=AllocationState.BASE_DCA,
            signal=Signal.NO_SIGNAL,
        ),
    )

    run_pipeline(SimpleNamespace(json=False, no_save=True, no_color=True))

    captured = capsys.readouterr()
    assert "报告折叠" in captured.out
    assert "基础定投" in captured.out
    assert "TRIGGERED" not in captured.out


def test_history_output_shows_allocation_state(monkeypatch, capsys):
    monkeypatch.setattr(
        "src.store.db.load_history",
        lambda n=2: [
            {
                "date": "2026-03-19",
                "allocation_state": "RISK_CONTAINMENT",
                "signal": "WATCH",
                "final_score": 20,
                "price": 402.0,
            },
            {
                "date": "2026-03-18",
                "allocation_state": "BASE_DCA",
                "signal": "NO_SIGNAL",
                "final_score": 10,
                "price": 401.0,
            },
        ],
    )

    _history(SimpleNamespace(history=2))

    captured = capsys.readouterr()
    assert "RISK_CONTAINMENT" in captured.out
    assert "进入风险控制" in captured.out
    assert "signal=" not in captured.out


def test_history_output_prioritizes_allocation_state_action(monkeypatch, capsys):
    monkeypatch.setattr(
        "src.store.db.load_history",
        lambda n=1: [
            {
                "date": "2026-03-19",
                "allocation_state": "PAUSE_CHASING",
                "signal": "TRIGGERED",
                "final_score": 88,
                "price": 402.0,
            },
        ],
    )

    _history(SimpleNamespace(history=1))

    captured = capsys.readouterr()
    assert "action=暂停追高" in captured.out
    assert "signal=" not in captured.out
    assert "TRIGGERED" not in captured.out


def test_main_does_not_swallow_unexpected_v7_errors(monkeypatch):
    price_history = pd.DataFrame(
        {
            "Open": [400.0, 401.0],
            "High": [402.0, 403.0],
            "Low": [399.0, 400.0],
            "Close": [401.0, 402.0],
            "Volume": [1_000_000, 1_100_000],
        }
    )

    monkeypatch.setattr(
        "src.collector.price.fetch_price_data",
        lambda: {
            "date": date(2026, 3, 19),
            "price": 402.0,
            "ma200": 395.0,
            "high_52w": 450.0,
            "days_since_high": 30,
            "history": price_history,
        },
    )
    monkeypatch.setattr("src.collector.vix.fetch_vix", lambda: 25.0)
    monkeypatch.setattr("src.collector.fear_greed.fetch_fear_greed", lambda: 28)
    monkeypatch.setattr("src.collector.options.fetch_options_chain", lambda spot_price: None)
    monkeypatch.setattr(
        "src.collector.breadth.fetch_breadth",
        lambda: {"adv_dec_ratio": 0.45, "pct_above_50d": 0.3, "ndx_concentration": 0.0},
    )
    monkeypatch.setattr("src.collector.macro.fetch_credit_spread", lambda: 410.0)
    monkeypatch.setattr(
        "src.collector.fundamentals.fetch_forward_pe",
        lambda: {"trailing_pe": 28.0, "forward_pe": 24.5, "source": "test"},
    )
    monkeypatch.setattr("src.collector.macro_v3.fetch_real_yield", lambda: 1.8)
    monkeypatch.setattr("src.collector.macro_v3.fetch_fcf_yield", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_earnings_revisions_breadth", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_net_liquidity", lambda: (None, None))
    monkeypatch.setattr("src.collector.macro_v3.fetch_move_index", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_sector_rotation", lambda: None)
    monkeypatch.setattr("src.collector.macro_v3.fetch_short_volume_proxy", lambda: None)
    monkeypatch.setattr("src.store.db.load_latest_macro_state", lambda: None)
    monkeypatch.setattr("src.store.db.get_historical_series", lambda days=120: None)
    monkeypatch.setattr("src.store.db.load_history", lambda n=5: [])
    monkeypatch.setattr("src.store.db.save_signal", lambda result: None)
    monkeypatch.setattr("src.store.db.save_macro_state", lambda **kwargs: None)

    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("src.engine.feature_pipeline.build_feature_snapshot", _boom)

    with pytest.raises(RuntimeError, match="boom"):
        run_pipeline(SimpleNamespace(json=True, no_save=True, no_color=True))
