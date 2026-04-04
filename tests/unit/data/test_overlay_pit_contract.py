from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd


def _context_with_provenance() -> pd.DataFrame:
    dates = pd.bdate_range("2026-01-01", periods=50)
    return pd.DataFrame(
        {
            "observation_date": dates,
            "adv_dec_ratio": [0.55] * len(dates),
            "source_breadth_proxy": ["observed:^ADD"] * len(dates),
            "breadth_quality_score": [1.0] * len(dates),
            "qqq_close": [100.0 + i for i in range(len(dates))],
            "source_qqq_close": ["direct:yfinance"] * len(dates),
            "qqq_close_quality_score": [1.0] * len(dates),
            "qqq_volume": [1_000_000.0 + (i * 1000.0) for i in range(len(dates))],
            "source_qqq_volume": ["direct:yfinance"] * len(dates),
            "qqq_volume_quality_score": [1.0] * len(dates),
        }
    )


def test_weekly_overlay_source_is_visible_only_after_release_timestamp():
    from src.engine.v13.execution_overlay import is_weekly_release_visible

    release_ts = datetime(2026, 4, 3, 19, 30, tzinfo=UTC)

    assert (
        is_weekly_release_visible(
            observation_ts=datetime(2026, 4, 3, 19, 29, tzinfo=UTC),
            release_ts=release_ts,
        )
        is False
    )
    assert (
        is_weekly_release_visible(
            observation_ts=datetime(2026, 4, 3, 19, 30, tzinfo=UTC),
            release_ts=release_ts,
        )
        is True
    )


def test_execution_overlay_emits_provenance_and_quality_for_admitted_inputs():
    from src.engine.v13.execution_overlay import ExecutionOverlayEngine

    result = ExecutionOverlayEngine().evaluate(_context_with_provenance())

    assert "breadth_proxy" in result["input_quality"]
    assert "qqq_close" in result["input_quality"]
    assert "qqq_volume" in result["input_quality"]
    assert "breadth_proxy" in result["admission_decisions"]
    assert "qqq_tape" in result["admission_decisions"]


def test_execution_overlay_rejects_repurposed_proxy_fields_even_if_numeric():
    from src.engine.v13.execution_overlay import ExecutionOverlayEngine

    context = _context_with_provenance().drop(columns=["adv_dec_ratio"])
    context["pct_above_50d"] = [0.92] * len(context)

    result = ExecutionOverlayEngine().evaluate(context)

    assert result["admission_decisions"]["breadth_proxy"]["admitted"] is False
    assert "repurposed proxy field" in result["admission_decisions"]["breadth_proxy"]["reason"]
