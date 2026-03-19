from __future__ import annotations

from datetime import date

from src.engine.data_quality import assess_feature_quality, build_data_quality
from src.models import MarketData


def test_assess_feature_quality_marks_missing_values_unusable():
    quality = assess_feature_quality(
        None,
        source="unavailable",
        category="macro",
    )

    assert quality == {
        "value": None,
        "source": "unavailable",
        "usable": False,
        "stale_days": 0,
        "category": "macro",
    }


def test_assess_feature_quality_preserves_present_values():
    quality = assess_feature_quality(
        24.5,
        source="yfinance",
        category="fundamental",
        stale_days=2,
    )

    assert quality == {
        "value": 24.5,
        "source": "yfinance",
        "usable": True,
        "stale_days": 2,
        "category": "fundamental",
    }


def test_build_data_quality_emits_feature_metadata():
    data = MarketData(
        date=date(2026, 3, 19),
        price=402.0,
        ma200=395.0,
        high_52w=450.0,
        vix=25.0,
        fear_greed=28,
        adv_dec_ratio=0.45,
        pct_above_50d=0.30,
        credit_spread=410.0,
        forward_pe=24.5,
        real_yield=1.8,
        fcf_yield=None,
        earnings_revisions_breadth=None,
        short_vol_ratio=None,
        pe_source="test",
    )

    quality = build_data_quality(data)

    assert quality["credit_spread"]["usable"] is True
    assert quality["credit_spread"]["source"] == "live"
    assert quality["credit_spread"]["stale_days"] == 0
    assert quality["forward_pe"]["usable"] is True
    assert quality["forward_pe"]["source"] == "live:test"
    assert quality["forward_pe"]["stale_days"] == 0
    assert quality["real_yield"]["usable"] is True
    assert quality["real_yield"]["source"] == "live"
    assert quality["real_yield"]["stale_days"] == 0
    assert quality["fcf_yield"]["usable"] is False
    assert quality["fcf_yield"]["source"] == "missing"
    assert quality["earnings_revisions_breadth"]["usable"] is False
    assert quality["earnings_revisions_breadth"]["source"] == "missing"
    assert quality["short_vol_ratio"]["usable"] is False
    for meta in quality.values():
        assert set(meta) == {"value", "source", "usable", "stale_days", "category"}


def test_build_data_quality_marks_cached_macro_values_stale():
    data = MarketData(
        date=date(2026, 3, 19),
        price=402.0,
        ma200=395.0,
        high_52w=450.0,
        vix=25.0,
        fear_greed=28,
        adv_dec_ratio=0.45,
        pct_above_50d=0.30,
        credit_spread=410.0,
        forward_pe=24.5,
        real_yield=1.8,
        fcf_yield=4.9,
        earnings_revisions_breadth=55.0,
        short_vol_ratio=None,
        pe_source="test",
    )

    quality = build_data_quality(
        data,
        feature_meta={
            "credit_spread": {"source": "cache:macro_state", "stale_days": 2},
            "forward_pe": {"source": "cache:macro_state", "stale_days": 2},
            "real_yield": {"source": "cache:macro_state", "stale_days": 2},
            "fcf_yield": {"source": "cache:macro_state", "stale_days": 2},
            "earnings_revisions_breadth": {"source": "cache:macro_state", "stale_days": 2},
        },
    )

    assert quality["credit_spread"]["source"] == "cache:macro_state"
    assert quality["credit_spread"]["stale_days"] == 2
    assert quality["forward_pe"]["source"] == "cache:macro_state"
    assert quality["forward_pe"]["stale_days"] == 2
    assert quality["real_yield"]["source"] == "cache:macro_state"
    assert quality["real_yield"]["stale_days"] == 2
    assert quality["fcf_yield"]["source"] == "cache:macro_state"
    assert quality["fcf_yield"]["stale_days"] == 2
    assert quality["earnings_revisions_breadth"]["source"] == "cache:macro_state"
    assert quality["earnings_revisions_breadth"]["stale_days"] == 2
