from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _overlay_history(
    *,
    breadth_last: float = 0.55,
    concentration_last: float = 0.02,
    last_close: float = 120.0,
    last_volume: float = 1_000_000.0,
    periods: int = 80,
) -> pd.DataFrame:
    dates = pd.bdate_range("2025-12-01", periods=periods)
    close = pd.Series([100.0 + (i * 0.2) for i in range(periods)], index=dates)
    volume = pd.Series([1_000_000.0 + (i * 5_000.0) for i in range(periods)], index=dates)
    breadth = pd.Series([0.55 for _ in range(periods)], index=dates)
    concentration = pd.Series([0.01 for _ in range(periods)], index=dates)

    close.iloc[-1] = last_close
    volume.iloc[-1] = last_volume
    breadth.iloc[-1] = breadth_last
    concentration.iloc[-1] = concentration_last

    return pd.DataFrame(
        {
            "observation_date": dates,
            "adv_dec_ratio": breadth.values,
            "source_breadth_proxy": ["observed:^ADD"] * periods,
            "breadth_quality_score": [1.0] * periods,
            "ndx_concentration": concentration.values,
            "source_ndx_concentration": ["derived:qqq-qqew"] * periods,
            "ndx_concentration_quality_score": [1.0] * periods,
            "qqq_close": close.values,
            "source_qqq_close": ["direct:yfinance"] * periods,
            "qqq_close_quality_score": [1.0] * periods,
            "qqq_volume": volume.values,
            "source_qqq_volume": ["direct:yfinance"] * periods,
            "qqq_volume_quality_score": [1.0] * periods,
        }
    )


def test_v13_overlay_audit_artifact_exists_and_has_required_keys():
    audit_path = Path("src/engine/v13/resources/execution_overlay_audit.json")
    assert audit_path.exists(), "v13 audit artifact missing"

    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert payload["version"] == "v13.9"
    assert "beta_overlay" in payload
    assert "deployment_overlay" in payload
    assert "signal_weights" in payload
    assert "source_policy" in payload
    assert "lambda_beta_pos" in payload["beta_overlay"]
    assert "beta_ceiling" in payload["beta_overlay"]


def test_execution_overlay_returns_neutral_multipliers_when_inputs_are_missing():
    from src.engine.v13.execution_overlay import ExecutionOverlayEngine

    engine = ExecutionOverlayEngine()
    context = pd.DataFrame({"observation_date": pd.bdate_range("2026-01-01", periods=5)})

    result = engine.evaluate(context)

    assert result["beta_overlay_multiplier"] == 1.0
    assert result["deployment_overlay_multiplier"] == 1.0
    assert result["overlay_state"] == "NEUTRAL"
    assert result["neutral_fallback_triggered"] is True


def test_execution_overlay_monotone_worsening_cannot_increase_beta():
    from src.engine.v13.execution_overlay import ExecutionOverlayEngine

    engine = ExecutionOverlayEngine()
    benign = _overlay_history(
        breadth_last=0.62,
        concentration_last=0.01,
        last_close=121.0,
        last_volume=1_400_000.0,
    )
    stressed = _overlay_history(
        breadth_last=0.18,
        concentration_last=0.12,
        last_close=124.0,
        last_volume=700_000.0,
    )

    benign_result = engine.evaluate(benign)
    stressed_result = engine.evaluate(stressed)

    assert stressed_result["negative_score"] >= benign_result["negative_score"]
    assert stressed_result["beta_overlay_multiplier"] <= benign_result["beta_overlay_multiplier"]
    assert 0.5 <= stressed_result["beta_overlay_multiplier"] <= 1.2


def test_execution_overlay_rejects_repurposed_proxy_fields_as_production_evidence():
    from src.engine.v13.execution_overlay import ExecutionOverlayEngine

    engine = ExecutionOverlayEngine()
    context = _overlay_history()
    context = context.drop(columns=["adv_dec_ratio"])
    context["pct_above_50d"] = [0.95] * len(context)

    result = engine.evaluate(context)

    assert result["admission_decisions"]["breadth_proxy"]["admitted"] is False
    assert "pct_above_50d" in result["admission_decisions"]["breadth_proxy"]["reason"]
    assert result["derived_features"]["breadth_stress"] is None


def test_execution_overlay_constant_inputs_do_not_create_phantom_penalties():
    from src.engine.v13.execution_overlay import ExecutionOverlayEngine

    engine = ExecutionOverlayEngine()
    neutral = _overlay_history(
        breadth_last=0.55,
        concentration_last=0.01,
        last_close=115.8,
        last_volume=1_395_000.0,
    )

    result = engine.evaluate(neutral)

    assert result["negative_score"] == 0.0
    assert result["positive_score"] == 0.0
    assert result["beta_overlay_multiplier"] == 1.0
    assert result["deployment_overlay_multiplier"] == 1.0
    assert result["overlay_state"] == "NEUTRAL"


def test_execution_overlay_modes_keep_diagnostics_but_gate_effective_multipliers():
    from src.engine.v13.execution_overlay import ExecutionOverlayEngine

    stressed = _overlay_history(
        breadth_last=0.18,
        concentration_last=0.12,
        last_close=124.0,
        last_volume=700_000.0,
    )
    engine = ExecutionOverlayEngine()

    disabled = engine.evaluate(stressed, mode="DISABLED")
    shadow = engine.evaluate(stressed, mode="SHADOW")
    negative_only = engine.evaluate(stressed, mode="NEGATIVE_ONLY")
    full = engine.evaluate(stressed, mode="FULL")

    assert disabled["overlay_mode"] == "DISABLED"
    assert disabled["beta_overlay_multiplier"] == 1.0
    assert disabled["deployment_overlay_multiplier"] == 1.0
    assert disabled["diagnostic_beta_overlay_multiplier"] < 1.0

    assert shadow["overlay_mode"] == "SHADOW"
    assert shadow["beta_overlay_multiplier"] == 1.0
    assert shadow["deployment_overlay_multiplier"] == 1.0
    assert shadow["diagnostic_beta_overlay_multiplier"] == full["beta_overlay_multiplier"]

    assert negative_only["overlay_mode"] == "NEGATIVE_ONLY"
    assert negative_only["beta_overlay_multiplier"] == full["beta_overlay_multiplier"]
    assert negative_only["deployment_overlay_multiplier"] <= 1.0
    assert full["deployment_overlay_multiplier"] >= negative_only["deployment_overlay_multiplier"]


def test_execution_overlay_positive_signal_can_boost_beta_above_one():
    """volume_repair 信号活跃时，FULL 模式的 Beta 乘子允许超过 1.0。"""
    from src.engine.v13.execution_overlay import ExecutionOverlayEngine

    engine = ExecutionOverlayEngine()
    # 构造场景：20d 下跌 + 近 5d 反弹 + 成交量放大 → volume_repair 信号
    periods = 80
    dates = pd.bdate_range("2025-12-01", periods=periods)
    close_vals = [120.0 - (i * 0.5) for i in range(periods)]  # 20d 持续下跌
    close_vals[-5:] = [close_vals[-6] + j * 1.0 for j in range(1, 6)]  # 近 5d 反弹
    volume_vals = [1_000_000.0] * periods
    volume_vals[-5:] = [3_000_000.0] * 5  # 放量

    context = pd.DataFrame({
        "observation_date": dates,
        "adv_dec_ratio": [0.55] * periods,
        "source_breadth_proxy": ["observed:^ADD"] * periods,
        "breadth_quality_score": [1.0] * periods,
        "ndx_concentration": [0.01] * periods,
        "source_ndx_concentration": ["derived:qqq-qqew"] * periods,
        "ndx_concentration_quality_score": [1.0] * periods,
        "qqq_close": close_vals,
        "source_qqq_close": ["direct:yfinance"] * periods,
        "qqq_close_quality_score": [1.0] * periods,
        "qqq_volume": volume_vals,
        "source_qqq_volume": ["direct:yfinance"] * periods,
        "qqq_volume_quality_score": [1.0] * periods,
    })

    result = engine.evaluate(context, mode="FULL")

    assert result["positive_score"] > 0.0, "volume_repair 信号应被激活"
    assert result["diagnostic_beta_overlay_multiplier"] > 1.0, (
        f"正向信号应将 Beta 乘子推过 1.0，实际={result['diagnostic_beta_overlay_multiplier']}"
    )
    assert result["diagnostic_beta_overlay_multiplier"] <= 1.2, "不得超过 beta_ceiling"


def test_execution_overlay_asymmetric_sensitivity():
    """负向灵敏度 (0.65) 远大于正向灵敏度 (0.15)，验证非对称设计。"""
    from src.engine.v13.execution_overlay import ExecutionOverlayEngine
    import json
    from pathlib import Path

    config = json.loads(
        Path("src/engine/v13/resources/execution_overlay_audit.json").read_text()
    )
    lambda_neg = config["beta_overlay"]["lambda_beta"]
    lambda_pos = config["beta_overlay"]["lambda_beta_pos"]

    # 防御灵敏度至少是进攻灵敏度的 3 倍
    assert lambda_neg >= 3.0 * lambda_pos, (
        f"非对称断裂：lambda_neg={lambda_neg} 应 >= 3 * lambda_pos={lambda_pos}"
    )


def test_execution_overlay_negative_only_mode_blocks_positive_beta_boost():
    """NEGATIVE_ONLY 模式下，正向信号不得提升 Beta 乘子超过 1.0。"""
    from src.engine.v13.execution_overlay import ExecutionOverlayEngine

    engine = ExecutionOverlayEngine()
    periods = 80
    dates = pd.bdate_range("2025-12-01", periods=periods)
    close_vals = [120.0 - (i * 0.5) for i in range(periods)]
    close_vals[-5:] = [close_vals[-6] + j * 1.0 for j in range(1, 6)]
    volume_vals = [1_000_000.0] * periods
    volume_vals[-5:] = [3_000_000.0] * 5

    context = pd.DataFrame({
        "observation_date": dates,
        "adv_dec_ratio": [0.55] * periods,
        "source_breadth_proxy": ["observed:^ADD"] * periods,
        "breadth_quality_score": [1.0] * periods,
        "ndx_concentration": [0.01] * periods,
        "source_ndx_concentration": ["derived:qqq-qqew"] * periods,
        "ndx_concentration_quality_score": [1.0] * periods,
        "qqq_close": close_vals,
        "source_qqq_close": ["direct:yfinance"] * periods,
        "qqq_close_quality_score": [1.0] * periods,
        "qqq_volume": volume_vals,
        "source_qqq_volume": ["direct:yfinance"] * periods,
        "qqq_volume_quality_score": [1.0] * periods,
    })

    full_result = engine.evaluate(context, mode="FULL")
    neg_only_result = engine.evaluate(context, mode="NEGATIVE_ONLY")

    # FULL 模式可以超过 1.0
    assert full_result["diagnostic_beta_overlay_multiplier"] > 1.0

    # NEGATIVE_ONLY 模式 Beta 乘子不得超过 1.0
    assert neg_only_result["beta_overlay_multiplier"] <= 1.0, (
        f"NEGATIVE_ONLY 不应允许 Beta > 1.0，实际={neg_only_result['beta_overlay_multiplier']}"
    )
