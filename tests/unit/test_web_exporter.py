"""Unit tests for the v12.0 Bayesian web exporter."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

from src.models import SignalResult, TargetAllocationState
from src.output.web_exporter import MarketCursor, export_web_snapshot


def _v11_result() -> SignalResult:
    return SignalResult(
        date=date(2026, 3, 27),
        price=562.58,
        target_beta=0.91,
        probabilities={"MID_CYCLE": 0.82, "LATE_CYCLE": 0.15},
        priors={"MID_CYCLE": 0.50, "LATE_CYCLE": 0.50},
        entropy=0.17,
        stable_regime="MID_CYCLE",
        target_allocation=TargetAllocationState(0.10, 0.90, 0.0, 0.90),
        logic_trace=[{"step": "inference", "result": "MID_CYCLE"}],
        explanation="v12.0 placeholder",
        metadata={
            "feature_values": {"vix": 20.0},
            "is_floor_active": True,
            "hydration_anchor": "2018-01-01",
            "raw_target_beta_pre_floor": 0.42,
            "protected_beta": 0.93,
            "overlay_beta": 0.91,
            "overlay_mode": "NEGATIVE_ONLY",
            "beta_overlay_multiplier": 0.98,
            "deployment_overlay_multiplier": 1.04,
            "overlay_state": "REWARD",
            "overlay_summary": "REWARD: neg=0.050 pos=0.220",
            "price_topology": {"regime": "LATE_CYCLE", "confidence": 0.62},
            "forensic_snapshot_path": "artifacts/runtime/snapshot_2026-03-27.json",
            "v13_4_diagnostics": {"penalties_applied": {"MID_CYCLE": 0.4}},
            "execution_overlay": {
                "overlay_mode": "NEGATIVE_ONLY",
                "negative_score": 0.05,
                "positive_score": 0.22,
                "diagnostic_beta_overlay_multiplier": 0.98,
                "diagnostic_deployment_overlay_multiplier": 1.04,
                "raw_inputs": {"qqq_volume": 1000000},
                "input_quality": {"qqq_volume": 1.0},
                "derived_features": {"volume_repair": 0.22},
                "signal_contributions": {"positive": {"volume_repair": 0.22}},
                "admission_decisions": {"qqq_tape": {"admitted": True, "reason": "admitted"}},
                "neutral_fallback_triggered": False,
            },
            "signal": {
                "qld_permission": {
                    "qld_allowed": True,
                    "allow_sub1x_qld": True,
                    "forced_bucket": "QLD",
                    "entry_mode": "LEFT_SIDE_PROBE",
                    "reason_code": "LEFT_SIDE_PROBE",
                    "reason": "Left-side probe opened on exhaustion plus stage-specific support.",
                    "relaxed_entry_signal": 0.72,
                    "left_side_kernel": {"active": True, "score": 0.78},
                    "regime_specific_override": {
                        "active": True,
                        "score": 0.40,
                        "clusters": {
                            "bubble_unwind_exhaustion": True,
                            "credit_crisis_repair": False,
                        },
                    },
                }
            },
            "canonical_decision": {
                "source": "v16_topology",
                "reason": "V16 topology process is clean.",
            },
        },
    )


def test_export_web_snapshot_v11_contract(tmp_path, monkeypatch):
    result = _v11_result()
    output_path = tmp_path / "status.json"

    # Mock market cursor to avoid mcal dependency issues in unit tests
    monkeypatch.setattr(MarketCursor, "get_market_state", lambda self, now: "FROZEN")
    monkeypatch.setattr(
        MarketCursor,
        "get_expires_at_utc",
        lambda self, now: datetime(2026, 3, 30, 17, 30, tzinfo=UTC),
    )

    ok = export_web_snapshot(result, output_path=output_path)

    assert ok is True
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["meta"]["version"] == "v14.0-ULTIMA"
    assert payload["signal"]["regime"] == "中期平稳 (MID_CYCLE)"
    assert payload["signal"]["target_beta"] == 0.91
    assert payload["signal"]["entropy"] == 0.17
    assert payload["signal"]["probabilities"]["MID_CYCLE"] == 0.82
    assert payload["signal"]["is_floor_active"] is True
    assert payload["signal"]["hydration_anchor"] == "2018-01-01"
    assert payload["signal"]["raw_target_beta_pre_floor"] == 0.42
    assert payload["signal"]["protected_beta"] == 0.93
    assert payload["signal"]["overlay_beta"] == 0.91
    assert payload["signal"]["overlay_mode"] == "NEGATIVE_ONLY"
    assert payload["signal"]["beta_overlay_multiplier"] == 0.98
    assert payload["signal"]["deployment_overlay_multiplier"] == 1.04
    assert payload["signal"]["price_topology"]["regime"] == "LATE_CYCLE"
    assert payload["signal"]["qld_permission"]["entry_mode"] == "LEFT_SIDE_PROBE"
    assert payload["signal"]["canonical_decision"]["source"] == "v16_topology"
    assert payload["signal"]["forensic_snapshot_path"].endswith(".json")
    assert payload["evidence"]["feature_values"]["vix"] == 20.0
    assert payload["evidence"]["execution_overlay"]["positive_score"] == 0.22
    assert payload["evidence"]["canonical_decision"]["reason"] == "V16 topology process is clean."
    assert payload["evidence"]["bayesian_diagnostics"]["penalties_applied"]["MID_CYCLE"] == 0.4
    assert (
        payload["evidence"]["qld_permission"]["regime_specific_override"]["clusters"][
            "bubble_unwind_exhaustion"
        ]
        is True
    )


def test_export_web_snapshot_preserves_dual_surface_semantics(tmp_path, monkeypatch):
    result = SignalResult(
        date=date(2026, 3, 27),
        price=562.58,
        target_beta=0.80,
        probabilities={"LATE_CYCLE": 0.62, "MID_CYCLE": 0.24, "BUST": 0.14},
        priors={"LATE_CYCLE": 0.55, "MID_CYCLE": 0.30, "BUST": 0.15},
        entropy=0.44,
        stable_regime="MID_CYCLE",
        target_allocation=TargetAllocationState(0.20, 0.80, 0.0, 0.80),
        logic_trace=[
            {"step": "behavioral_guard", "result": {"lock_active": False, "target_bucket": "QQQ"}}
        ],
        explanation="v12.0 semantic separation test",
        metadata={
            "posterior_regime": "LATE_CYCLE",
            "execution_regime": "MID_CYCLE",
            "raw_regime": "LATE_CYCLE",
            "deployment_state": "DEPLOY_SLOW",
            "deployment_state_key": "SLOW",
            "execution_bucket": "QQQ",
        },
    )
    output_path = tmp_path / "status.json"

    monkeypatch.setattr(MarketCursor, "get_market_state", lambda self, now: "FROZEN")
    monkeypatch.setattr(
        MarketCursor,
        "get_expires_at_utc",
        lambda self, now: datetime(2026, 3, 30, 17, 30, tzinfo=UTC),
    )

    ok = export_web_snapshot(result, output_path=output_path)

    assert ok is True
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["signal"]["regime"] == "末端 (LATE_CYCLE)"
    assert payload["signal"]["posterior_regime"] == "LATE_CYCLE"
    assert payload["signal"]["raw_regime"] == "LATE_CYCLE"
    assert payload["signal"]["stable_regime"] == "LATE_CYCLE"
    assert payload["signal"]["execution_regime"] == "MID_CYCLE"
    assert payload["signal"]["deployment_state"] == "DEPLOY_SLOW"
    assert payload["signal"]["deployment_state_key"] == "SLOW"
    assert payload["signal"]["execution_bucket"] == "QQQ"


def test_export_web_snapshot_uses_canonical_bucket_over_behavioral_guard(tmp_path, monkeypatch):
    result = SignalResult(
        date=date(2026, 4, 16),
        price=637.91,
        target_beta=1.599,
        probabilities={"LATE_CYCLE": 0.52, "BUST": 0.44, "RECOVERY": 0.04},
        priors={},
        entropy=0.58,
        stable_regime="LATE_CYCLE",
        target_allocation=TargetAllocationState(0.0, 0.401, 0.599, 1.599),
        logic_trace=[
            {"step": "behavioral_guard", "result": {"lock_active": False, "target_bucket": "QQQ"}}
        ],
        explanation="canonical bucket",
        metadata={
            "execution_bucket": "QLD",
            "canonical_decision": {
                "source": "v16_topology",
                "official_reference_path": {"qld_pct": 0.599, "qqq_pct": 0.401, "cash_pct": 0.0},
            },
        },
    )
    output_path = tmp_path / "status.json"

    monkeypatch.setattr(MarketCursor, "get_market_state", lambda self, now: "FROZEN")
    monkeypatch.setattr(
        MarketCursor,
        "get_expires_at_utc",
        lambda self, now: datetime(2026, 4, 17, 17, 30, tzinfo=UTC),
    )

    ok = export_web_snapshot(result, output_path=output_path)

    assert ok is True
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["signal"]["execution_bucket"] == "QLD"
    assert payload["signal"]["reference_path"]["qld_pct"] == 0.599


def test_export_web_snapshot_collapses_legacy_capitulation_into_recovery(tmp_path, monkeypatch):
    result = SignalResult(
        date=date(2026, 3, 27),
        price=562.58,
        target_beta=1.02,
        probabilities={"CAPITULATION": 0.35, "RECOVERY": 0.25, "BUST": 0.40},
        priors={"CAPITULATION": 0.10, "RECOVERY": 0.30, "MID_CYCLE": 0.60},
        entropy=0.29,
        stable_regime="CAPITULATION",
        target_allocation=TargetAllocationState(0.0, 1.0, 0.1, 1.02),
        logic_trace=[{"step": "inference", "result": "CAPITULATION"}],
        explanation="legacy topology compatibility",
        metadata={"raw_regime": "CAPITULATION"},
    )
    output_path = tmp_path / "status.json"

    monkeypatch.setattr(MarketCursor, "get_market_state", lambda self, now: "FROZEN")
    monkeypatch.setattr(
        MarketCursor,
        "get_expires_at_utc",
        lambda self, now: datetime(2026, 3, 30, 17, 30, tzinfo=UTC),
    )

    ok = export_web_snapshot(result, output_path=output_path)

    assert ok is True
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["signal"]["stable_regime"] == "RECOVERY"
    assert payload["signal"]["raw_regime"] == "RECOVERY"
    assert payload["signal"]["regime"] == "修复 (RECOVERY)"
    assert "CAPITULATION" not in payload["signal"]["probabilities"]
    assert payload["signal"]["probabilities"]["RECOVERY"] == 0.60


def test_export_web_snapshot_includes_probability_dynamics(tmp_path, monkeypatch):
    result = SignalResult(
        date=date(2026, 4, 6),
        price=500.0,
        target_beta=0.8,
        probabilities={"MID_CYCLE": 0.35, "LATE_CYCLE": 0.30, "BUST": 0.20, "RECOVERY": 0.15},
        priors={"MID_CYCLE": 0.25, "LATE_CYCLE": 0.25, "BUST": 0.25, "RECOVERY": 0.25},
        entropy=0.88,
        stable_regime="MID_CYCLE",
        target_allocation=TargetAllocationState(0.2, 0.8, 0.0, 0.8),
        logic_trace=[
            {"step": "behavioral_guard", "result": {"lock_active": False, "target_bucket": "QQQ"}}
        ],
        explanation="probability dynamics",
        metadata={
            "probability_dynamics": {
                "MID_CYCLE": {
                    "probability": 0.35,
                    "delta_1d": -0.05,
                    "acceleration_1d": 0.05,
                    "trend": "FALLING",
                }
            }
        },
    )
    output_path = tmp_path / "status.json"

    monkeypatch.setattr(MarketCursor, "get_market_state", lambda self, now: "FROZEN")
    monkeypatch.setattr(
        MarketCursor,
        "get_expires_at_utc",
        lambda self, now: datetime(2026, 4, 7, 17, 30, tzinfo=UTC),
    )

    ok = export_web_snapshot(result, output_path=output_path)

    assert ok is True
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["signal"]["probability_dynamics"]["MID_CYCLE"]["delta_1d"] == -0.05
    assert payload["signal"]["probability_dynamics"]["MID_CYCLE"]["trend"] == "FALLING"


def test_export_web_snapshot_preserves_resonance_payload(tmp_path, monkeypatch):
    result = SignalResult(
        date=date(2026, 4, 7),
        price=505.0,
        target_beta=1.1,
        probabilities={"MID_CYCLE": 0.61, "LATE_CYCLE": 0.15, "BUST": 0.09, "RECOVERY": 0.15},
        priors={"MID_CYCLE": 0.25, "LATE_CYCLE": 0.25, "BUST": 0.25, "RECOVERY": 0.25},
        entropy=0.56,
        stable_regime="MID_CYCLE",
        target_allocation=TargetAllocationState(0.0, 0.9, 0.1, 1.1),
        logic_trace=[
            {"step": "behavioral_guard", "result": {"lock_active": False, "target_bucket": "QLD"}}
        ],
        explanation="resonance payload",
        metadata={
            "signal": {
                "resonance": {
                    "action": "BUY_QLD",
                    "confidence": 0.91,
                    "reason_code": "TRIPLE_RESONANCE_BUY",
                    "reason": "Risk cliff + entropy waterfall + MID expansion",
                    "prompt": "三重共振成立，允许切入 QLD。",
                }
            }
        },
    )
    output_path = tmp_path / "status.json"

    monkeypatch.setattr(MarketCursor, "get_market_state", lambda self, now: "FROZEN")
    monkeypatch.setattr(
        MarketCursor,
        "get_expires_at_utc",
        lambda self, now: datetime(2026, 4, 8, 17, 30, tzinfo=UTC),
    )

    assert export_web_snapshot(result, output_path=output_path) is True
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["signal"]["resonance"]["action"] == "BUY_QLD"
    assert payload["signal"]["resonance"]["reason_code"] == "TRIPLE_RESONANCE_BUY"
    assert "QLD" in payload["signal"]["resonance"]["prompt"]


def test_export_web_snapshot_includes_recovery_hmm_shadow_diagnostics(tmp_path, monkeypatch):
    result = SignalResult(
        date=date(2026, 4, 8),
        price=510.0,
        target_beta=0.9,
        probabilities={"MID_CYCLE": 0.5, "RECOVERY": 0.2, "LATE_CYCLE": 0.2, "BUST": 0.1},
        priors={"MID_CYCLE": 0.25, "RECOVERY": 0.25, "LATE_CYCLE": 0.25, "BUST": 0.25},
        entropy=0.42,
        stable_regime="MID_CYCLE",
        target_allocation=TargetAllocationState(0.1, 0.9, 0.0, 0.9),
        logic_trace=[
            {"step": "behavioral_guard", "result": {"lock_active": False, "target_bucket": "QQQ"}}
        ],
        explanation="recovery hmm shadow diagnostics",
        metadata={
            "recovery_hmm_shadow": {
                "decision_gate": "CANDIDATE_FOR_INTEGRATION",
                "acceptance": {
                    "q1_2022_below_or_equal_0_5": True,
                    "q1_2023_above_or_equal_0_85": True,
                },
                "comparison": {
                    "rows_compared": 686,
                    "recovery_release_gap": 122,
                },
            }
        },
    )
    output_path = tmp_path / "status.json"

    monkeypatch.setattr(MarketCursor, "get_market_state", lambda self, now: "FROZEN")
    monkeypatch.setattr(
        MarketCursor,
        "get_expires_at_utc",
        lambda self, now: datetime(2026, 4, 9, 17, 30, tzinfo=UTC),
    )

    assert export_web_snapshot(result, output_path=output_path) is True
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    shadow = payload["diagnostics"]["recovery_hmm_shadow"]
    assert shadow["decision_gate"] == "CANDIDATE_FOR_INTEGRATION"
    assert shadow["acceptance"]["q1_2023_above_or_equal_0_85"] is True
    assert shadow["comparison"]["recovery_release_gap"] == 122

def test_export_web_snapshot_includes_kelly_fraction(tmp_path, monkeypatch):
    result = SignalResult(
        date=date(2026, 4, 12),
        price=550.0,
        target_beta=0.75,
        probabilities={"MID_CYCLE": 1.0},
        priors={"MID_CYCLE": 1.0},
        entropy=0.0,
        stable_regime="MID_CYCLE",
        target_allocation=TargetAllocationState(0.25, 0.75, 0.0, 0.75),
        logic_trace=[],
        explanation="kelly fraction test",
        metadata={"kelly_fraction": 0.42},
    )
    output_path = tmp_path / "status.json"

    monkeypatch.setattr(MarketCursor, "get_market_state", lambda self, now: "ACTIVE")
    monkeypatch.setattr(
        MarketCursor,
        "get_expires_at_utc",
        lambda self, now: datetime(2026, 4, 13, 17, 30, tzinfo=UTC),
    )

    assert export_web_snapshot(result, output_path=output_path) is True
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["signal"]["kelly_fraction"] == 0.42
