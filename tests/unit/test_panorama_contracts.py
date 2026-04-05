import json
from datetime import date

from src.engine.aggregator import FullPanoramaAggregator
from src.models import SignalResult, TargetAllocationState
from src.output.web_exporter import export_web_snapshot


def test_full_panorama_aggregator_emits_canonical_verdict_tokens():
    runtime = {
        "target_beta": 0.9,
        "is_floor_active": False,
    }
    baseline = {
        "tractor": {"prob": 0.32, "status": "success"},
        "sidecar": {"prob": 0.05, "status": "success"},
    }

    result = FullPanoramaAggregator.aggregate(runtime, baseline)

    assert result["ensemble_verdict"] == "PROTECTIVE"
    assert "PROTECT" in result["ensemble_verdict_label"]


def test_web_exporter_sets_shadow_mode_from_metadata(tmp_path):
    result = SignalResult(
        date=date(2026, 3, 30),
        price=100.0,
        target_beta=0.8,
        probabilities={"MID_CYCLE": 0.7, "LATE_CYCLE": 0.3},
        priors={"MID_CYCLE": 0.6, "LATE_CYCLE": 0.4},
        entropy=0.2,
        stable_regime="MID_CYCLE",
        target_allocation=TargetAllocationState(
            target_cash_pct=0.2,
            target_qqq_pct=0.8,
            target_qld_pct=0.0,
            target_beta=0.8,
        ),
        logic_trace=[
            {"step": "behavioral_guard", "result": {"lock_active": False, "target_bucket": "QQQ"}}
        ],
        explanation="test",
        metadata={
            "v14_baseline_prob": 0.1,
            "v14_sidecar_prob": 0.2,
            "v14_baseline_status": "success",
            "v14_sidecar_status": "success",
            "v14_ensemble_verdict": "PROTECTIVE",
            "v14_ensemble_verdict_label": "🚨 PROTECT (GUARD at 0.5)",
            "v14_shadow_mode": True,
        },
    )

    output_path = tmp_path / "status.json"
    assert export_web_snapshot(result, output_path=output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["diagnostics"]["shadow_mode"] is True
    assert payload["diagnostics"]["ensemble_options"]["verdict"] == "PROTECTIVE"
    assert payload["diagnostics"]["ensemble_options"]["verdict_label"].startswith("🚨")
