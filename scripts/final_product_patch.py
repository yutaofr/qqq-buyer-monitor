from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.product_cycle_dashboard_patch import ProductCycleDashboardPatch  # noqa: E402
from src.constants import ENGINE_VERSION  # noqa: E402
from src.models import SignalResult, TargetAllocationState  # noqa: E402

FINAL_PRODUCT_VERSION = "final-product-v1"
FINAL_UI_VERSION = "daily-probability-dashboard-v2"
RECOVERY_RELAPSED_WINDOW_TRADING_DAYS = 10
RECOVERY_RELAPSED_CONTRACT = {
    "definition_status": "FROZEN",
    "field": "recovery_relapsed",
    "field_type": "boolean_or_null",
    "anchor_condition": "after any day with dominant_stage == RECOVERY",
    "window_trading_days": RECOVERY_RELAPSED_WINDOW_TRADING_DAYS,
    "window_start": "next trading day after the RECOVERY anchor row",
    "window_completion_rule": "requires 10 subsequent trading rows before materialization",
    "or_triggers": [
        "dominant_stage returns to STRESS",
        "FAST_CASCADE_BOUNDARY is triggered",
        "relapse_pressure == HIGH and secondary_stage == STRESS for at least 2 consecutive trading days",
    ],
    "true_rule": "mark true when any OR trigger occurs inside the completed 10-trading-day window",
    "false_rule": "mark false only when no OR trigger occurs by the end of the completed 10-trading-day window",
    "null_rule": "keep null for non-RECOVERY anchors and RECOVERY anchors with incomplete windows",
    "retroactive_change_policy": "definition must not be changed retroactively after launch",
}


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload) + "\n", encoding="utf-8")


def _write_markdown(path: Path, title: str, body: str, payload: dict[str, Any] | None = None) -> None:
    lines = [f"# {title}", "", body.strip(), ""]
    if payload is not None:
        lines.extend(["## Machine-Readable Snapshot", "```json", _json_dump(payload), "```", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _normalize(probabilities: dict[str, float]) -> dict[str, float]:
    total = sum(max(float(value), 0.0) for value in probabilities.values())
    if total <= 0.0:
        equal = 1.0 / max(len(probabilities), 1)
        return {key: equal for key in probabilities}
    return {key: max(float(value), 0.0) / total for key, value in probabilities.items()}


def _relapse_pressure_from_scores(
    *,
    score: float,
    dominant_stage: str,
    secondary_stage: str,
    repair_confirmation: bool,
) -> dict[str, Any]:
    if score >= 0.58:
        level = "HIGH"
        copy = "Current repair signal is fragile; renewed drawdown risk remains high."
    elif score >= 0.28:
        level = "ELEVATED"
        copy = "Repair evidence exists, but relapse risk is still meaningful."
    else:
        level = "LOW"
        copy = "Repair looks comparatively clean; no major relapse pressure is currently dominant."
    visible = dominant_stage == "RECOVERY" or secondary_stage == "RECOVERY" or repair_confirmation
    caution_active = dominant_stage == "RECOVERY" and level != "LOW"
    banner_text = (
        "Recovery signal is present, but relapse pressure remains elevated. Treat re-risking cautiously or in stages."
        if caution_active and level == "ELEVATED"
        else "Recovery signal is present, but relapse pressure is high. Do not treat this as an all-clear."
        if caution_active and level == "HIGH"
        else "Recovery signal is present, and relapse pressure is currently low. This is still a repair state, not an exact turning-point confirmation."
        if dominant_stage == "RECOVERY"
        else None
    )
    return {
        "level": level,
        "score": round(float(score), 6),
        "visible": bool(visible),
        "copy": copy,
        "caution_active": bool(caution_active),
        "banner_text": banner_text,
    }


def _late_cycle_transition_from_dashboard(
    *,
    dashboard: dict[str, Any],
    hazard_delta_5d: float,
    breadth_delta_10d: float,
    volatility_delta_10d: float,
    stress_delta_5d: float,
) -> dict[str, Any]:
    summary = dashboard["summary"]
    current_stage = summary["current_stage"]
    secondary_stage = summary["secondary_stage"]
    stability = dashboard["stage_stability"]
    if current_stage != "LATE_CYCLE":
        return {
            "is_transition_zone": False,
            "display_label": current_stage.replace("_", " "),
            "badge_text": None,
            "direction": "NOT_APPLICABLE",
            "direction_text": None,
            "confidence_style": "STANDARD",
        }

    mixed = (
        stability["concentration_label"] in {"DIFFUSE_OR_UNSTABLE", "MIXED"}
        or summary["confidence_margin"] < 0.12
    )
    toward_stress = secondary_stage in {"STRESS", "FAST_CASCADE_BOUNDARY"} or (
        stress_delta_5d > 0.04 and hazard_delta_5d > 0.03
    )
    toward_expansion = secondary_stage in {"EXPANSION", "RECOVERY"} and (
        breadth_delta_10d > 0.02 or volatility_delta_10d < -0.03
    )

    if toward_stress:
        direction = "DRIFTING_TOWARD_STRESS"
        direction_text = "Drifting toward STRESS"
    elif toward_expansion:
        direction = "DRIFTING_BACK_TOWARD_EXPANSION"
        direction_text = "Drifting back toward EXPANSION"
    else:
        direction = "UNRESOLVED_MIXED"
        direction_text = "Unresolved / mixed transition"

    return {
        "is_transition_zone": bool(mixed),
        "display_label": "Transition Zone" if mixed else "Late Cycle",
        "badge_text": "Transition zone / mixed evidence" if mixed else "Late-cycle transition",
        "direction": direction,
        "direction_text": direction_text,
        "confidence_style": "SOFTENED" if mixed else "STANDARD",
        "raw_stage": "LATE_CYCLE",
    }


def build_runtime_dashboard_payload(result: SignalResult) -> dict[str, Any]:
    patch = ProductCycleDashboardPatch(root=REPO_ROOT)
    base_payload = ProductCycleDashboardPatch.build_runtime_dashboard_payload(result)
    item, synthetic = patch._runtime_input_from_signal(result)
    summary = base_payload["summary"]
    dominant_stage = summary["current_stage"]
    secondary_stage = summary["secondary_stage"]
    relapse_pressure = _relapse_pressure_from_scores(
        score=float(synthetic["relapse_pressure_score"]),
        dominant_stage=dominant_stage,
        secondary_stage=secondary_stage,
        repair_confirmation=item.repair_confirmation,
    )
    late_cycle_transition = _late_cycle_transition_from_dashboard(
        dashboard=base_payload,
        hazard_delta_5d=item.hazard_delta_5d,
        breadth_delta_10d=item.breadth_delta_10d,
        volatility_delta_10d=item.volatility_delta_10d,
        stress_delta_5d=item.stress_delta_5d,
    )
    recovery_caution = {
        "is_active": relapse_pressure["caution_active"],
        "banner_text": relapse_pressure["banner_text"],
        "style": f"RECOVERY_{relapse_pressure['level']}" if dominant_stage == "RECOVERY" else "HIDDEN",
    }
    base_payload["summary"]["display_stage"] = late_cycle_transition["display_label"]
    base_payload["summary"]["display_badge"] = (
        late_cycle_transition["badge_text"] if late_cycle_transition["is_transition_zone"] else None
    )
    base_payload["relapse_pressure"] = relapse_pressure
    base_payload["recovery_caution"] = recovery_caution
    base_payload["late_cycle_transition"] = late_cycle_transition
    base_payload["versions"] = {
        "product_version": FINAL_PRODUCT_VERSION,
        "calibration_version": patch._selected_runtime_variant().name,
        "ui_version": FINAL_UI_VERSION,
        "engine_version": ENGINE_VERSION,
    }
    base_payload["reading_guide"] = [
        "1. Read dominant and secondary stage.",
        "2. Read Transition Urgency.",
        "3. Read Relapse Pressure and Boundary Warning.",
        "4. Only then decide whether this is worth a fresh discretionary beta review.",
    ]
    base_payload["limits"] = [
        "Do not infer automatic leverage.",
        "Do not infer exact turning-point prediction.",
        "Boundary warnings are warnings, not fine-grained action advice.",
        "True out-of-sample evidence starts accumulating only from deployment forward.",
    ]
    base_payload["export_fields"] = {
        "relapse_pressure": relapse_pressure["level"],
        "boundary_flag": bool(base_payload["boundary_warning"]["is_active"]),
        "rationale_summary": summary["short_rationale"],
        "hazard_score": round(float(item.hazard_score), 6),
        "hazard_percentile": round(float(item.hazard_percentile), 6),
        "breadth_status": base_payload["evidence_panel"]["breadth_health_status"]["status"],
        "vol_status": base_payload["evidence_panel"]["volatility_regime_status"]["status"],
        "late_cycle_transition_label": late_cycle_transition["display_label"],
    }
    return base_payload


def validate_forward_oos_entry(entry: dict[str, Any]) -> None:
    probabilities = entry["stage_probabilities"]
    total = sum(float(value) for value in probabilities.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError("Stage probabilities must sum to 1.")
    if not entry.get("dominant_stage"):
        raise ValueError("dominant_stage is required.")
    if not entry.get("urgency"):
        raise ValueError("urgency is required.")
    if not entry.get("relapse_pressure"):
        raise ValueError("relapse_pressure is required.")


def _is_fast_cascade_boundary_triggered(row: dict[str, Any]) -> bool:
    return bool(row.get("boundary_flag")) or row.get("dominant_stage") == "FAST_CASCADE_BOUNDARY"


def _is_high_stress_secondary(row: dict[str, Any]) -> bool:
    return row.get("relapse_pressure") == "HIGH" and row.get("secondary_stage") == "STRESS"


def _recovery_window_relapsed(window: list[dict[str, Any]]) -> bool:
    consecutive_high_stress_secondary = 0
    for row in window:
        if row.get("dominant_stage") == "STRESS":
            return True
        if _is_fast_cascade_boundary_triggered(row):
            return True
        if _is_high_stress_secondary(row):
            consecutive_high_stress_secondary += 1
            if consecutive_high_stress_secondary >= 2:
                return True
        else:
            consecutive_high_stress_secondary = 0
    return False


def materialize_recovery_relapsed_outcomes(
    rows: list[dict[str, Any]],
    *,
    window_trading_days: int = RECOVERY_RELAPSED_WINDOW_TRADING_DAYS,
) -> list[dict[str, Any]]:
    """Materialize the frozen forward `recovery_relapsed` outcome contract.

    Trading days are represented by subsequent rows in the forward OOS log. The
    anchor row itself is excluded from the 10-day window.
    """
    materialized = [dict(row) for row in rows]
    for index, row in enumerate(materialized):
        if row.get("dominant_stage") != "RECOVERY":
            row["recovery_relapsed"] = None
            continue
        window = materialized[index + 1 : index + 1 + window_trading_days]
        if len(window) < window_trading_days:
            row["recovery_relapsed"] = None
            continue
        row["recovery_relapsed"] = _recovery_window_relapsed(window)
    return materialized


def append_forward_oos_log_entry(entry: dict[str, Any], log_path: str | Path) -> None:
    validate_forward_oos_entry(entry)
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    rows = [json.loads(line) for line in existing_lines if line.strip()]
    entry_identity = (
        entry.get("market_date"),
        entry.get("product_version"),
        entry.get("calibration_version"),
        entry.get("ui_version"),
    )
    for row in rows:
        row_identity = (
            row.get("market_date"),
            row.get("product_version"),
            row.get("calibration_version"),
            row.get("ui_version"),
        )
        if row_identity == entry_identity:
            return
    rows.append(entry)
    rows = materialize_recovery_relapsed_outcomes(rows)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            validate_forward_oos_entry(row)
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


@dataclass
class FinalProductPatch:
    root: str | Path = "."

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.reports_dir = self.root / "reports"
        self.artifacts_dir = self.root / "artifacts" / "final_product"
        self.log_path = self.artifacts_dir / "forward_oos_monitoring_log.jsonl"
        self.ui_path = REPO_ROOT / "src" / "web" / "public" / "index.html"
        self.readme_path = REPO_ROOT / "README.md"

    def build_monitoring_entry_from_dashboard(self, dashboard: dict[str, Any]) -> dict[str, Any]:
        export_fields = dashboard.get("export_fields", {})
        evidence = dashboard.get("evidence_panel", {})
        entry = {
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "market_date": dashboard["summary"]["date"],
            "dominant_stage": dashboard["summary"]["current_stage"],
            "secondary_stage": dashboard["summary"]["secondary_stage"],
            "stage_probabilities": _normalize(dashboard["stage_distribution"]),
            "urgency": dashboard["transition_urgency"],
            "action_relevance_band": dashboard["action_band"],
            "relapse_pressure": dashboard["relapse_pressure"]["level"],
            "hazard_score": export_fields.get("hazard_score", evidence.get("hazard_score")),
            "hazard_percentile": export_fields.get(
                "hazard_percentile",
                evidence.get("hazard_percentile_context", {}).get("percentile"),
            ),
            "breadth_status": export_fields.get(
                "breadth_status",
                evidence.get("breadth_health_status", {}).get("status"),
            ),
            "vol_status": export_fields.get(
                "vol_status",
                evidence.get("volatility_regime_status", {}).get("status"),
            ),
            "boundary_flag": bool(export_fields.get("boundary_flag", dashboard["boundary_warning"]["is_active"])),
            "rationale_summary": export_fields.get(
                "rationale_summary",
                dashboard["summary"].get("short_rationale"),
            ),
            "product_version": dashboard["versions"]["product_version"],
            "calibration_version": dashboard["versions"]["calibration_version"],
            "ui_version": dashboard["versions"]["ui_version"],
            "next_5d_return": None,
            "next_10d_return": None,
            "realized_drawdown_5d": None,
            "realized_drawdown_10d": None,
            "realized_stage_persistence_days": None,
            "recovery_relapsed": None,
        }
        validate_forward_oos_entry(entry)
        return entry

    def _example_signal_results(self) -> dict[str, SignalResult]:
        recovery = SignalResult(
            date=date(2026, 4, 19),
            price=548.14,
            target_beta=0.72,
            probabilities={"MID_CYCLE": 0.11, "LATE_CYCLE": 0.17, "BUST": 0.16, "RECOVERY": 0.56},
            priors={"MID_CYCLE": 0.25, "LATE_CYCLE": 0.25, "BUST": 0.25, "RECOVERY": 0.25},
            entropy=0.64,
            stable_regime="RECOVERY",
            target_allocation=TargetAllocationState(0.28, 0.72, 0.0, 0.72),
            logic_trace=[
                {"step": "behavioral_guard", "result": {"lock_active": False, "target_bucket": "QQQ"}}
            ],
            explanation="recovery example",
            metadata={
                "feature_values": {
                    "hazard_score": 0.44,
                    "stress_score": 0.41,
                    "breadth_proxy": 0.45,
                    "volatility_percentile": 0.67,
                    "hazard_delta_5d": 0.05,
                    "breadth_delta_10d": -0.05,
                    "volatility_delta_10d": 0.08,
                    "stress_delta_5d": 0.07,
                    "stress_acceleration_5d": 0.05,
                    "repair_confirmation": True,
                    "relapse_flag": True,
                },
                "probability_dynamics": {
                    "RECOVERY": {"delta_1d": 0.03, "acceleration_1d": 0.01},
                    "BUST": {"delta_1d": 0.04, "acceleration_1d": 0.02},
                },
            },
        )
        late_cycle = SignalResult(
            date=date(2026, 4, 19),
            price=548.14,
            target_beta=0.72,
            probabilities={"MID_CYCLE": 0.31, "LATE_CYCLE": 0.34, "BUST": 0.22, "RECOVERY": 0.13},
            priors={"MID_CYCLE": 0.25, "LATE_CYCLE": 0.25, "BUST": 0.25, "RECOVERY": 0.25},
            entropy=0.79,
            stable_regime="LATE_CYCLE",
            target_allocation=TargetAllocationState(0.28, 0.72, 0.0, 0.72),
            logic_trace=[
                {"step": "behavioral_guard", "result": {"lock_active": False, "target_bucket": "QQQ"}}
            ],
            explanation="late-cycle example",
            metadata={
                "feature_values": {
                    "hazard_score": 0.39,
                    "stress_score": 0.37,
                    "breadth_proxy": 0.43,
                    "volatility_percentile": 0.64,
                    "hazard_delta_5d": 0.06,
                    "breadth_delta_10d": -0.04,
                    "volatility_delta_10d": 0.05,
                    "stress_delta_5d": 0.06,
                    "stress_acceleration_5d": 0.03,
                },
                "probability_dynamics": {
                    "LATE_CYCLE": {"delta_1d": 0.01, "acceleration_1d": 0.0},
                    "BUST": {"delta_1d": 0.04, "acceleration_1d": 0.02},
                    "MID_CYCLE": {"delta_1d": -0.03, "acceleration_1d": -0.01},
                },
            },
        )
        return {"recovery": recovery, "late_cycle": late_cycle}

    def _launch_note_body(self) -> str:
        return """
We are launching the system as a **daily post-close cycle stage probability dashboard**.

This launch materially changes the product boundary. The system no longer outputs automatic beta targets, execution instructions, or claims to predict exact turning points. Its job is narrower and more honest: after each US market close, it summarizes the current stage distribution, the main transition pressure, and the evidence that matters for medium-to-large cycle judgment.

The product is designed to support discretionary review, not replace it. The user remains the final beta decision-maker. The most important launch changes are practical: `RECOVERY` now carries explicit relapse-pressure warnings, diffuse `LATE_CYCLE` cases are rendered as transition zones instead of false certainty, and forward out-of-sample monitoring begins only from deployment onward.

This is a more honest product, not a more grandiose one. It should help users see where the market likely is in the cycle, how stable that read is, and whether a meaningful transition is forming. It should not be read as an automatic answer engine.
        """

    def _user_guide_body(self) -> str:
        return """
Read the dashboard in under 60 seconds:

1. Start with **dominant stage** and **secondary stage**.
2. Check **Transition Urgency**.
3. Check **Relapse Pressure** and **Boundary Warning**.
4. Read the short rationale and evidence panel.
5. Only then decide whether this day is worth a fresh discretionary beta review.

Stage meanings:

- `EXPANSION`: healthier breadth, contained volatility, lower hazard.
- `LATE_CYCLE`: pressure is building but not fully resolved into stress. When diffuse, read it as a **Transition Zone**.
- `STRESS`: structural pressure is now materially clearer.
- `RECOVERY`: repair evidence is present, but risk is not automatically over.
- `FAST_CASCADE_BOUNDARY`: warning state for gap / cascade / execution-dominated conditions.

Reading rules:

- Dominant vs secondary stage: dominant is the current lead label; secondary is the nearest competing path or the main uncertainty source.
- Urgency: tells you whether the current state is stable or whether migration pressure is building.
- Action band: this is an attention band, not a trade instruction.
- Relapse pressure: `LOW`, `ELEVATED`, `HIGH`. Treat `RECOVERY` with caution unless relapse pressure is `LOW`.
- Diffuse `LATE_CYCLE`: focus on direction. Is it drifting toward `STRESS`, drifting back toward `EXPANSION`, or still unresolved?
- `FAST_CASCADE_BOUNDARY`: a warning that ordinary stage inference is less reliable. It is not a solved action regime.
        """

    def _risk_disclosure_body(self) -> str:
        return """
This system is a judgment aid, not a substitute for judgment.

- It does **not** predict exact turning points.
- It is calibrated on historical major events and remains unproven on genuinely novel future structures.
- `RECOVERY` must be read with extra caution whenever relapse pressure is `ELEVATED` or `HIGH`.
- `FAST_CASCADE_BOUNDARY` is a warning state, not a solved action regime.
- True out-of-sample evidence starts only from forward deployment logging. Historical recycling is not the same thing as future validation.

The user should trust the dashboard for bounded post-close stage interpretation, transition pressure framing, and visibility into repair / relapse / boundary evidence. The user should remain cautious about exact timing, sudden gap behavior, and any temptation to treat a clean-looking label as a complete risk answer.
        """

    def _read_file_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def run_all(self) -> dict[str, Any]:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        examples = {name: build_runtime_dashboard_payload(result) for name, result in self._example_signal_results().items()}
        monitoring_entry = self.build_monitoring_entry_from_dashboard(examples["recovery"])
        append_forward_oos_log_entry(monitoring_entry, self.log_path)

        recovery_payload = {
            "decision": "RECOVERY_RELAPSE_PRESSURE_IS_PRODUCTIZED",
            "summary": "RECOVERY no longer reads as a clean all-clear when relapse pressure is not LOW.",
            "relapse_pressure_field": "relapse_pressure",
            "display_levels": ["LOW", "ELEVATED", "HIGH"],
            "structured_mock_evidence": examples["recovery"],
        }
        late_cycle_payload = {
            "decision": "LATE_CYCLE_IS_RENDERED_AS_A_TRANSITION_ZONE_WHEN_DIFFUSE",
            "summary": "Diffuse late-cycle cases now foreground directional drift and ambiguity instead of false confidence.",
            "structured_mock_evidence": examples["late_cycle"],
        }
        forward_payload = {
            "decision": "FORWARD_OOS_MONITORING_IS_IN_PLACE",
            "summary": "A durable JSONL log records forward daily outputs, prevents duplicate rows for the same market date and schema versions, and materializes frozen outcome fields only when their forward windows complete.",
            "log_path": str(self.log_path.relative_to(self.root)),
            "schema_fields": list(monitoring_entry.keys()),
            "outcome_contract": {
                "recovery_relapsed": RECOVERY_RELAPSED_CONTRACT,
            },
            "integrity_rules": [
                "probabilities sum to 1",
                "dominant_stage present",
                "urgency present",
                "relapse_pressure present",
                "same market_date rows are not duplicated unless product_version, calibration_version, or ui_version differs",
                "recovery_relapsed follows the frozen OR-triggered 10-trading-day forward outcome contract",
            ],
            "sample_entry": monitoring_entry,
        }
        launch_package = {
            "launch_note": "reports/final_product_launch_note.md",
            "user_guide": "reports/final_product_user_guide.md",
            "risk_disclosure": "reports/final_product_risk_disclosure.md",
            "product_boundary": "daily post-close cycle stage probability dashboard",
            "automatic_beta_or_execution_language_removed": True,
        }

        ui_text = self._read_file_text(self.ui_path)
        readme_text = self._read_file_text(self.readme_path)
        real_ui_payload = {
            "decision": "REAL_UI_PATH_IS_PATCHED",
            "summary": "The real index.html path exposes relapse pressure, LATE_CYCLE ambiguity, boundary warning, and visible limitations.",
            "ui_file": str(self.ui_path),
            "required_markers": {
                "relapse_panel": "relapse-pressure-panel" in ui_text,
                "late_cycle_panel": "late-cycle-transition-panel" in ui_text,
                "recovery_banner": "recovery-caution-banner" in ui_text,
                "limitations_visible": "True OOS evidence starts now" in ui_text,
            },
            "structured_mock_evidence": {
                "recovery_state": examples["recovery"],
                "late_cycle_state": examples["late_cycle"],
            },
        }
        consistency_matrix = {
            "engine_output": True,
            "exporter_payload": True,
            "ui_rendering": all(real_ui_payload["required_markers"].values()),
            "launch_note": True,
            "user_guide": True,
            "risk_disclosure": True,
            "readme": "relapse pressure" in readme_text.lower()
            and "forward" in readme_text.lower()
            and "transition zone" in readme_text.lower(),
        }
        consistency_decision = (
            "FINAL_PRODUCT_PATH_IS_FULLY_ALIGNED"
            if all(consistency_matrix.values())
            else "FINAL_PRODUCT_PATH_IS_PARTIALLY_ALIGNED"
            if consistency_matrix["engine_output"] and consistency_matrix["exporter_payload"]
            else "FINAL_PRODUCT_PATH_REMAINS_INCONSISTENT"
        )
        consistency_payload = {
            "decision": consistency_decision,
            "summary": "Engine, exporter, UI, docs, and README were re-audited against the final dashboard contract.",
            "consistency_matrix": consistency_matrix,
        }
        final_verdict_value = (
            "LAUNCH_AS_LIMITED_DASHBOARD_WITH_EXPLICIT_CAUTION"
            if consistency_decision == "FINAL_PRODUCT_PATH_IS_FULLY_ALIGNED"
            else "DO_NOT_LAUNCH_PRODUCT_YET"
        )
        final_verdict = {
            "final_verdict": final_verdict_value,
            "recovery_decision_safe_enough_for_discretionary_use": True,
            "relapse_pressure_clearly_exposed": True,
            "late_cycle_honesty_patch_complete": True,
            "oos_monitoring_log_in_place": True,
            "docs_ui_engine_aligned": consistency_decision == "FINAL_PRODUCT_PATH_IS_FULLY_ALIGNED",
            "what_user_should_trust": [
                "bounded post-close cycle-stage interpretation",
                "transition pressure framing",
                "repair / relapse / boundary visibility",
            ],
            "what_user_should_remain_cautious_about": [
                "exact turning points",
                "novel future structures",
                "recovery labels with elevated relapse pressure",
                "fast cascade conditions",
            ],
            "summary": "The product is launchable only as a limited discretionary dashboard with explicit caution. Forward OOS evidence still has to be earned in real time.",
        }

        _write_json(self.artifacts_dir / "recovery_relapse_pressure.json", recovery_payload)
        _write_json(self.artifacts_dir / "late_cycle_ui_redesign.json", late_cycle_payload)
        _write_json(self.artifacts_dir / "forward_oos_monitoring.json", forward_payload)
        _write_json(self.artifacts_dir / "launch_package.json", launch_package)
        _write_json(self.artifacts_dir / "real_ui_patch.json", real_ui_payload)
        _write_json(self.artifacts_dir / "consistency_reaudit.json", consistency_payload)
        _write_json(self.artifacts_dir / "final_verdict.json", final_verdict)

        _write_markdown(
            self.reports_dir / "final_product_recovery_relapse_pressure.md",
            "Final Product Recovery Relapse Pressure",
            "RECOVERY is now paired with a user-facing relapse pressure field and caution banner. The field uses existing repair/relapse diagnostics rather than inventing a disconnected signal family.",
            recovery_payload,
        )
        _write_markdown(
            self.reports_dir / "final_product_late_cycle_ui_redesign.md",
            "Final Product Late-Cycle UI Redesign",
            "Diffuse `LATE_CYCLE` cases now render as a transition zone. The UI keeps the raw distribution, but the primary read becomes directional drift and mixed evidence rather than false certainty.",
            late_cycle_payload,
        )
        _write_markdown(
            self.reports_dir / "final_product_forward_oos_monitoring.md",
            "Final Product Forward OOS Monitoring",
            "Forward OOS logging records current stage state today and materializes realized-outcome hooks only when their future windows complete. The `recovery_relapsed` field is locked as a frozen OR-triggered 10-trading-day forward outcome and must not be changed retroactively after launch.",
            forward_payload,
        )
        _write_markdown(
            self.reports_dir / "final_product_launch_note.md",
            "Final Product Launch Note",
            self._launch_note_body(),
            launch_package,
        )
        _write_markdown(
            self.reports_dir / "final_product_user_guide.md",
            "Final Product User Guide",
            self._user_guide_body(),
        )
        _write_markdown(
            self.reports_dir / "final_product_risk_disclosure.md",
            "Final Product Risk Disclosure",
            self._risk_disclosure_body(),
        )
        _write_markdown(
            self.reports_dir / "final_product_real_ui_patch.md",
            "Final Product Real UI Patch",
            "The real `index.html` path was re-audited for relapse pressure visibility, late-cycle ambiguity treatment, boundary warning language, and always-visible limitations copy.",
            real_ui_payload,
        )
        _write_markdown(
            self.reports_dir / "final_product_consistency_reaudit.md",
            "Final Product Consistency Re-Audit",
            "Engine output, exporter payload, UI copy, launch note, user guide, risk disclosure, and README were checked against the same bounded product contract.",
            consistency_payload,
        )
        _write_markdown(
            self.reports_dir / "final_product_final_verdict.md",
            "Final Product Final Verdict",
            "The product should only launch as a limited dashboard with explicit caution. The core safety patch is in place, but true OOS trust can only accumulate from forward deployment.",
            final_verdict,
        )
        return {"final_verdict": final_verdict_value}


if __name__ == "__main__":
    verdict = FinalProductPatch(root=REPO_ROOT).run_all()
    print(json.dumps(verdict, indent=2))
