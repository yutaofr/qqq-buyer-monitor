"""Integration test: full pipeline with mocked external data sources."""
from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.engine.aggregator import aggregate
from src.engine.data_quality import build_data_quality
from src.engine.tier1 import calculate_tier1
from src.engine.tier2 import calculate_tier2
from src.models import AllocationState, MarketData, Signal
from src.output.cli import print_signal
from src.output.report import to_json


# ── Shared mock data ──────────────────────────────────────────────────────────

MOCK_PRICE = 412.0
MOCK_DATE = date(2026, 3, 8)

MOCK_OPTIONS = pd.DataFrame([
    {"strike": 400.0, "expiration": "2026-03-21", "option_type": "put",
     "openInterest": 9000, "impliedVolatility": 0.25, "gamma": 0.018, "gamma_source": "yfinance"},
    {"strike": 390.0, "expiration": "2026-03-21", "option_type": "put",
     "openInterest": 3000, "impliedVolatility": 0.28, "gamma": 0.01, "gamma_source": "yfinance"},
    {"strike": 440.0, "expiration": "2026-03-21", "option_type": "call",
     "openInterest": 8000, "impliedVolatility": 0.18, "gamma": 0.015, "gamma_source": "yfinance"},
    {"strike": 420.0, "expiration": "2026-03-21", "option_type": "call",
     "openInterest": 2000, "impliedVolatility": 0.20, "gamma": 0.012, "gamma_source": "yfinance"},
])


def _build_market_data(
    price: float = MOCK_PRICE,
    ma200: float = 450.0,      # deep below MA200 → high score
    high_52w: float = 490.0,   # big drawdown → high score
    vix: float = 35.0,          # panic vix
    fear_greed: int = 15,       # extreme fear
    adv_dec_ratio: float = 0.3,
    pct_above_50d: float = 0.20,
    options_df=MOCK_OPTIONS,
    ohlcv_history: pd.DataFrame | None = None
) -> MarketData:
    return MarketData(
        date=MOCK_DATE,
        price=price,
        ma200=ma200,
        high_52w=high_52w,
        vix=vix,
        fear_greed=fear_greed,
        adv_dec_ratio=adv_dec_ratio,
        pct_above_50d=pct_above_50d,
        options_df=options_df,
        ohlcv_history=ohlcv_history
    )


# ── Pipeline integration tests ────────────────────────────────────────────────

class TestFullPipeline:
    def test_bullish_scenario_produces_triggered(self):
        """Full-score scenario: all Tier-1 signals max, price above put wall."""
        data = _build_market_data()  # all extreme bullish + price 412 above put wall 400
        t1 = calculate_tier1(data)
        t2 = calculate_tier2(data.price, data.options_df, ohlcv_history=data.ohlcv_history)
        result = aggregate(data.date, data.price, t1, t2)

        assert t1.score >= 100, f"Expected Tier-1 score>=100, got {t1.score}"
        assert not t2.support_broken
        assert result.signal in (Signal.TRIGGERED, Signal.WATCH)

    def test_broken_support_softens_to_watch(self):
        """Weak support should soften the compatibility signal to WATCH."""
        data = _build_market_data(price=395.0)  # below put wall at 400
        t1 = calculate_tier1(data)
        t2 = calculate_tier2(data.price, data.options_df, ohlcv_history=data.ohlcv_history)
        result = aggregate(data.date, data.price, t1, t2)

        assert t2.support_broken is True
        assert result.signal == Signal.WATCH

    def test_neutral_scenario_produces_no_signal(self):
        """Neutral markets should produce NO_SIGNAL."""
        data = _build_market_data(
            price=415.0,
            ma200=410.0,    # +1.2% → 0 pts
            high_52w=430.0, # 3.5% drawdown → 0 pts
            vix=16.0,       # 0 pts
            fear_greed=55,  # 0 pts
            adv_dec_ratio=0.8,  # 0 pts
            pct_above_50d=0.6,  # 0 pts
        )
        t1 = calculate_tier1(data)
        t2 = calculate_tier2(data.price, data.options_df, ohlcv_history=data.ohlcv_history)
        result = aggregate(data.date, data.price, t1, t2)

        assert result.signal == Signal.NO_SIGNAL

    def test_result_has_all_required_fields(self):
        data = _build_market_data()
        t1 = calculate_tier1(data)
        t2 = calculate_tier2(data.price, data.options_df, ohlcv_history=data.ohlcv_history)
        result = aggregate(data.date, data.price, t1, t2)

        assert result.date == MOCK_DATE
        assert result.price == MOCK_PRICE
        assert result.signal in Signal.__members__.values()
        assert result.tier1.score >= 0
        assert isinstance(result.explanation, str) and len(result.explanation) > 0


class TestJSONSerialisation:
    def test_result_serialises_to_valid_json(self):
        from src.store.db import _to_json_dict

        data = _build_market_data()
        t1 = calculate_tier1(data)
        t2 = calculate_tier2(data.price, data.options_df, ohlcv_history=data.ohlcv_history)
        result = aggregate(data.date, data.price, t1, t2)

        d = _to_json_dict(result)
        json_str = json.dumps(d)
        parsed = json.loads(json_str)

        assert parsed["signal"] in ("TRIGGERED", "WATCH", "NO_SIGNAL")
        assert "tier1" in parsed
        assert "tier2" in parsed
        assert "explanation" in parsed
        assert "name" in parsed["tier1"]["details"]["drawdown_52w"]  # SignalDetail has 'name' not 'date'

    def test_json_contains_options_wall_data(self):
        from src.store.db import _to_json_dict

        data = _build_market_data()
        t1 = calculate_tier1(data)
        t2 = calculate_tier2(data.price, data.options_df, ohlcv_history=data.ohlcv_history)
        result = aggregate(data.date, data.price, t1, t2)

        d = _to_json_dict(result)
        t2_data = d["tier2"]

        assert t2_data["put_wall"] is not None
        assert t2_data["call_wall"] is not None
        assert "support_broken" in t2_data
        assert "support_confirmed" in t2_data

    def test_json_contains_allocation_fields(self):
        data = _build_market_data()
        data.credit_spread = 410.0
        data.forward_pe = 24.5
        data.real_yield = 1.8
        data.fcf_yield = 5.1
        data.earnings_revisions_breadth = 0.6
        data.short_vol_ratio = 0.7
        t1 = calculate_tier1(data)
        t2 = calculate_tier2(data.price, data.options_df, ohlcv_history=data.ohlcv_history)
        result = aggregate(data.date, data.price, t1, t2)
        result.data_quality = build_data_quality(data)

        d = json.loads(to_json(result))

        assert d["allocation_state"] == AllocationState.FAST_ACCUMULATE.value
        assert d["daily_tranche_pct"] == 0.75
        assert d["max_total_add_pct"] == 2.0
        assert d["cooldown_days"] == 2
        assert d["required_persistence_days"] == 2
        assert d["confidence"] == "high"
        assert d["data_quality_summary"] == "6/6 可用"
        assert isinstance(d["data_quality"], dict)
        assert d["data_quality"]["credit_spread"]["usable"] is True
        assert d["tier1"]["stress_score"] == result.tier1.stress_score
        assert d["tier1"]["capitulation_score"] == result.tier1.capitulation_score
        assert d["tier1"]["persistence_score"] == result.tier1.persistence_score
        assert d["tier1"]["short_flow_bonus"] == result.tier1.short_flow_bonus

    def test_cli_snapshot_shows_allocation_guidance_and_quality_summary(self, capsys):
        data = _build_market_data()
        data.credit_spread = 410.0
        data.forward_pe = 24.5
        data.real_yield = 1.8
        data.fcf_yield = 5.1
        data.earnings_revisions_breadth = 0.6
        data.short_vol_ratio = 0.7
        t1 = calculate_tier1(data)
        t2 = calculate_tier2(data.price, data.options_df, ohlcv_history=data.ohlcv_history)
        result = aggregate(data.date, data.price, t1, t2)
        result.data_quality = build_data_quality(data)

        print_signal(result, use_color=False, compact=False)

        out = capsys.readouterr().out
        assert "允许提高加仓速度" in out
        assert "Policy:" in out
        assert "FAST" in out
        assert "单日加仓: 75%" in out
        assert "置信度: high" in out
        assert "数据质量: 6/6 可用" in out
        assert "强烈买入" not in out
        assert "分批加仓区间" not in out
        assert "百年一遇" not in out


class TestDegradedMode:
    def test_none_options_df_gives_neutral_tier2(self):
        """If options data is unavailable, Tier-2 should return neutral (adjustment=0)."""
        data = _build_market_data(options_df=None)
        t2 = calculate_tier2(data.price, data.options_df, ohlcv_history=data.ohlcv_history)

        assert t2.adjustment == 0
        assert t2.put_wall is None
        assert t2.support_broken is False

    def test_cli_action_line_stays_with_allocation_state(self, capsys):
        data = _build_market_data()
        pause_result = aggregate(
            MOCK_DATE,
            402.0,
            calculate_tier1(data),
            calculate_tier2(402.0, MOCK_OPTIONS, ohlcv_history=data.ohlcv_history),
        )
        pause_result.allocation_state = AllocationState.PAUSE_CHASING
        pause_result.signal = Signal.TRIGGERED
        pause_result.explanation = "暂停追高。"

        risk_result = aggregate(
            MOCK_DATE,
            402.0,
            calculate_tier1(data),
            calculate_tier2(402.0, MOCK_OPTIONS, ohlcv_history=data.ohlcv_history),
        )
        risk_result.allocation_state = AllocationState.RISK_CONTAINMENT
        risk_result.signal = Signal.TRIGGERED
        risk_result.explanation = "进入风险控制。"

        print_signal(pause_result, use_color=False, compact=False)
        pause_out = capsys.readouterr().out

        print_signal(risk_result, use_color=False, compact=False)
        risk_out = capsys.readouterr().out

        assert "暂停追高" in pause_out
        assert "进入风险控制" in risk_out
        assert "允许提高加仓速度" not in pause_out
        assert "允许提高加仓速度" not in risk_out
