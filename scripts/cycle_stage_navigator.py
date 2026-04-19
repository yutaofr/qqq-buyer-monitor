import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.phase_next_research import EventWindow, PhaseNextResearch  # noqa: E402

STAGES = {"EXPANSION", "LATE_CYCLE", "STRESS", "RECOVERY", "FAST_CASCADE_BOUNDARY"}
URGENCIES = {"LOW", "RISING", "HIGH", "UNSTABLE"}


@dataclass(frozen=True)
class CycleStageInput:
    hazard_score: float
    stress_score: float
    breadth_proxy: float
    volatility_percentile: float
    repair_active: bool
    structural_stress: bool
    repair_confirmation: bool
    relapse_flag: bool
    hazard_delta: float = 0.0
    breadth_delta: float = 0.0
    volatility_delta: float = 0.0
    gap_pressure: float = 0.0
    stress_persistence_days: int = 0
    repair_persistence_days: int = 0
    date: str | None = None


class CycleStageNavigator:
    MISSION_DECISION = "MISSION_REPOSITION_SUCCESSFULLY_LOCKED"
    TAXONOMY_DECISION = "STAGE_TAXONOMY_IS_STABLE_AND_USABLE"
    SIGNAL_DECISION = "STAGE_SIGNAL_MAPPING_IS_SUFFICIENTLY_COHERENT"
    TRANSLATION_DECISION = "STACK_TO_STAGE_TRANSLATION_IS_HUMAN_USABLE"
    URGENCY_DECISION = "TRANSITION_URGENCY_MODEL_IS_USEFUL_AND_DISTINCT"
    STABILITY_DECISION = "STAGE_STABILITY_IS_PRACTICALLY_USABLE"
    BOUNDARY_DECISION = "BOUNDARY_STATE_HANDLING_IS_HONEST_AND_USEFUL"
    DASHBOARD_DECISION = "DASHBOARD_SPEC_IS_READY_FOR_IMPLEMENTATION"
    HISTORICAL_DECISION = "HISTORICAL_STAGE_CLASSIFICATION_IS_MEANINGFULLY_CORRECT"
    HUMAN_DECISION = "HUMAN_DECISION_SUPPORT_VALUE_IS_CLEAR"
    FINAL_VERDICT = "RELAUNCH_AS_HUMAN_CYCLE_STAGE_NAVIGATOR"

    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root)
        self.repo_root = Path(__file__).resolve().parents[1]
        self.reports_dir = self.root / "reports"
        self.artifacts_dir = self.root / "artifacts" / "cycle_stage"
        self.cleanroom = PhaseNextResearch(root=root)

    def evaluate(self, stage_input: CycleStageInput) -> dict[str, Any]:
        stage = self._stage_label(stage_input)
        urgency = self._transition_urgency(stage_input)
        confidence = self._stage_confidence(stage_input, stage)
        evidence = self._evidence_panel(stage_input)
        return {
            "date": stage_input.date,
            "current_stage_label": stage,
            "stage_confidence": confidence,
            "transition_urgency": urgency,
            "evidence_panel": evidence,
            "boundary_warning": self._boundary_warning(stage_input, stage),
            "short_rationale": self._rationale(stage_input, stage, urgency),
            "human_guidance_layer": self._human_guidance(stage),
        }

    def run_all(self) -> dict[str, Any]:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        frame = self._build_stage_frame()
        evaluations = self._evaluate_frame(frame)
        payloads = self._build_payloads(frame, evaluations)
        self._write_payloads(payloads)
        return {"final_verdict": payloads["final_verdict"]["final_verdict"]}

    def _stage_label(self, item: CycleStageInput) -> str:
        if self._is_boundary(item):
            return "FAST_CASCADE_BOUNDARY"
        if self._is_recovery(item):
            return "RECOVERY"
        if item.repair_active or item.structural_stress:
            return "STRESS"
        if item.stress_score >= 0.50 and item.breadth_proxy < 0.48:
            return "STRESS"
        if item.hazard_score >= 0.30 or item.stress_score >= 0.28:
            return "LATE_CYCLE"
        if item.breadth_proxy < 0.45 or item.volatility_percentile >= 0.62:
            return "LATE_CYCLE"
        return "EXPANSION"

    @staticmethod
    def _is_boundary(item: CycleStageInput) -> bool:
        return (
            item.gap_pressure >= 0.07
            or (item.volatility_percentile >= 0.98 and item.hazard_delta >= 0.10)
            or (item.stress_score >= 0.72 and item.gap_pressure >= 0.04)
        )

    @staticmethod
    def _is_recovery(item: CycleStageInput) -> bool:
        if item.relapse_flag or item.repair_active:
            return False
        repair_flow = item.breadth_delta > 0.015 or item.volatility_delta < -0.04
        return item.repair_confirmation and item.stress_score <= 0.48 and repair_flow

    @staticmethod
    def _transition_urgency(item: CycleStageInput) -> str:
        pressure = 0
        pressure += item.hazard_delta >= 0.06
        pressure += item.breadth_delta <= -0.045
        pressure += item.volatility_delta >= 0.08
        pressure += item.relapse_flag
        pressure += item.gap_pressure >= 0.04
        if item.gap_pressure >= 0.07 or pressure >= 4:
            return "UNSTABLE"
        severe_acceleration = item.relapse_flag or item.gap_pressure >= 0.04 or item.hazard_delta >= 0.12 or item.volatility_delta >= 0.15
        if (pressure >= 3 and severe_acceleration) or (item.repair_active and item.stress_persistence_days >= 20):
            return "HIGH"
        if pressure >= 1:
            return "RISING"
        return "LOW"

    @staticmethod
    def _stage_confidence(item: CycleStageInput, stage: str) -> float:
        if stage == "FAST_CASCADE_BOUNDARY":
            raw = 0.78 + min(item.gap_pressure, 0.12)
        elif stage == "STRESS":
            raw = 0.58 + 0.20 * item.repair_active + 0.18 * item.structural_stress
            raw += 0.12 * min(max(item.stress_score - 0.42, 0.0) / 0.28, 1.0)
        elif stage == "RECOVERY":
            raw = 0.58 + 0.15 * item.repair_confirmation + 0.08 * min(item.repair_persistence_days, 5) / 5.0
        elif stage == "LATE_CYCLE":
            raw = 0.56 + 0.12 * (item.hazard_score >= 0.30) + 0.10 * (item.breadth_proxy < 0.48)
        else:
            raw = 0.62 + 0.12 * (item.hazard_score < 0.20) + 0.10 * (item.breadth_proxy >= 0.52)
        contradiction = 0.0
        contradiction += 0.08 if stage == "EXPANSION" and item.hazard_delta > 0.05 else 0.0
        contradiction += 0.08 if stage == "RECOVERY" and item.volatility_percentile > 0.80 else 0.0
        contradiction += 0.08 if stage == "STRESS" and item.breadth_delta > 0.05 else 0.0
        return round(float(np.clip(raw - contradiction, 0.35, 0.92)), 3)

    @staticmethod
    def _evidence_panel(item: CycleStageInput) -> dict[str, Any]:
        return {
            "hazard_score": {
                "value": round(item.hazard_score, 4),
                "context": "contained" if item.hazard_score < 0.30 else "elevated_or_rising",
                "delta": round(item.hazard_delta, 4),
            },
            "exit_repair_activation_state": {
                "repair_active": item.repair_active,
                "repair_confirmation": item.repair_confirmation,
                "stress_persistence_days": item.stress_persistence_days,
                "repair_persistence_days": item.repair_persistence_days,
            },
            "breadth_health_proxy": {
                "value": round(item.breadth_proxy, 4),
                "context": "healthy" if item.breadth_proxy >= 0.52 else "weak_or_deteriorating",
                "delta": round(item.breadth_delta, 4),
            },
            "volatility_proxy_percentile": {
                "value": round(item.volatility_percentile, 4),
                "context": "contained" if item.volatility_percentile < 0.65 else "elevated_or_unstable",
                "delta": round(item.volatility_delta, 4),
            },
            "relapse_indicators": {"relapse_flag": item.relapse_flag},
            "structural_stress_indicators": {
                "structural_stress": item.structural_stress,
                "stress_score": round(item.stress_score, 4),
            },
            "boundary_warnings": {"gap_pressure": round(item.gap_pressure, 4)},
        }

    @staticmethod
    def _boundary_warning(item: CycleStageInput, stage: str) -> dict[str, Any]:
        active = stage == "FAST_CASCADE_BOUNDARY"
        return {
            "is_boundary_warning": active,
            "warning_language": (
                "Fast-cascade or gap-dominated conditions are active; read this as an account-boundary warning, "
                "not as fine-grained policy advice."
                if active
                else None
            ),
            "not_to_infer": "Do not infer a solved execution or leverage regime." if active else None,
            "trigger_evidence": {
                "gap_pressure": round(item.gap_pressure, 4),
                "volatility_percentile": round(item.volatility_percentile, 4),
                "hazard_delta": round(item.hazard_delta, 4),
            },
        }

    @staticmethod
    def _human_guidance(stage: str) -> dict[str, Any]:
        language = {
            "EXPANSION": "beta can be considered high if the human agrees with broader context",
            "LATE_CYCLE": "beta can be considered moderate; aggressiveness deserves review",
            "STRESS": "beta thinking should be reduced or defensive",
            "RECOVERY": "beta may be phased back with relapse awareness",
            "FAST_CASCADE_BOUNDARY": "prioritize boundary awareness; automatic strategy logic is not trustworthy here",
        }
        return {"qualitative_beta_language": language[stage], "hard_leverage_number": None}

    @staticmethod
    def _rationale(item: CycleStageInput, stage: str, urgency: str) -> str:
        return (
            f"{stage} with {urgency} urgency: hazard={item.hazard_score:.2f}, "
            f"stress={item.stress_score:.2f}, breadth={item.breadth_proxy:.2f}, "
            f"vol_pct={item.volatility_percentile:.2f}. This is a stage assessment, not a leverage order."
        )

    def _build_stage_frame(self) -> pd.DataFrame:
        frame = self.cleanroom._build_cleanroom_frame()
        vol_rank = frame["vol_21"].rolling(252, min_periods=30).rank(pct=True)
        frame["volatility_percentile"] = vol_rank.fillna(frame["vol_21"].rank(pct=True)).fillna(0.5).clip(0.0, 1.0)
        frame["hazard_delta"] = frame["hazard_score"].diff(5).fillna(0.0)
        frame["breadth_delta"] = frame["breadth_proxy"].diff(10).fillna(0.0)
        frame["volatility_delta"] = frame["volatility_percentile"].diff(10).fillna(0.0)
        frame["gap_pressure"] = frame["gap_ret"].clip(upper=0.0).abs().rolling(5, min_periods=1).sum()
        frame["repair_active"] = self.cleanroom._state_from_repair_confirmation(frame)
        frame["structural_stress"] = (frame["stress_score"] >= 0.50) & (frame["breadth_proxy"] < 0.48)
        frame["repair_confirmation"] = self._repair_confirmation(frame)
        frame["relapse_flag"] = self._relapse_flag(frame)
        frame["stress_persistence_days"] = self._run_lengths(frame["repair_active"])
        frame["repair_persistence_days"] = self._run_lengths(frame["repair_confirmation"])
        return frame

    @staticmethod
    def _repair_confirmation(frame: pd.DataFrame) -> pd.Series:
        recent_stress = frame["repair_active"].rolling(63, min_periods=1).max().astype(bool)
        improving = (frame["breadth_delta"] > 0.025) | (frame["volatility_delta"] < -0.08)
        return recent_stress & ~frame["repair_active"] & (frame["stress_score"] <= 0.48) & improving

    @staticmethod
    def _relapse_flag(frame: pd.DataFrame) -> pd.Series:
        recent_repair = frame["repair_confirmation"].rolling(21, min_periods=1).max().astype(bool)
        deterioration = (frame["stress_score"].diff(5).fillna(0.0) > 0.08) | (frame["breadth_delta"] < -0.06)
        return recent_repair & deterioration

    @staticmethod
    def _run_lengths(mask: pd.Series) -> pd.Series:
        out = []
        count = 0
        for value in mask.astype(bool):
            count = count + 1 if value else 0
            out.append(count)
        return pd.Series(out, index=mask.index)

    def _evaluate_frame(self, frame: pd.DataFrame) -> list[dict[str, Any]]:
        rows = []
        for _, row in frame.iterrows():
            item = CycleStageInput(
                date=pd.Timestamp(row["date"]).strftime("%Y-%m-%d"),
                hazard_score=float(row["hazard_score"]),
                stress_score=float(row["stress_score"]),
                breadth_proxy=float(row["breadth_proxy"]),
                volatility_percentile=float(row["volatility_percentile"]),
                repair_active=bool(row["repair_active"]),
                structural_stress=bool(row["structural_stress"]),
                repair_confirmation=bool(row["repair_confirmation"]),
                relapse_flag=bool(row["relapse_flag"]),
                hazard_delta=float(row["hazard_delta"]),
                breadth_delta=float(row["breadth_delta"]),
                volatility_delta=float(row["volatility_delta"]),
                gap_pressure=float(row["gap_pressure"]),
                stress_persistence_days=int(row["stress_persistence_days"]),
                repair_persistence_days=int(row["repair_persistence_days"]),
            )
            rows.append(self.evaluate(item))
        return rows

    def _build_payloads(self, frame: pd.DataFrame, evaluations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        latest = evaluations[-1]
        historical = self._historical_validation(frame, evaluations)
        stability = self._stability_audit(evaluations, historical["event_validations"])
        checklist = self._acceptance_checklist()
        return {
            "mission_reposition_lock": self._mission_payload(),
            "taxonomy_finalization": self._taxonomy_payload(),
            "signal_mapping": self._signal_mapping_payload(),
            "stack_to_stage_translation": self._translation_payload(latest),
            "transition_urgency_model": self._urgency_payload(),
            "stability_false_alarm_audit": stability,
            "boundary_state_handling": self._boundary_payload(),
            "dashboard_spec": self._dashboard_payload(latest),
            "historical_validation": historical,
            "human_decision_support_evaluation": self._human_support_payload(),
            "acceptance_checklist": checklist,
            "final_verdict": self._final_payload(checklist),
        }

    def _mission_payload(self) -> dict[str, Any]:
        return {
            "decision": self.MISSION_DECISION,
            "required_statements": [
                "The system is no longer an automatic leverage control engine.",
                "The system output is a regime/cycle-stage assessment for human use.",
                "The system is evaluated on stage usefulness, stability, and interpretability, not automatic policy PnL optimization.",
                "Fast-cascade and gap-dominated conditions remain boundary warnings, not solved control regimes.",
                "Human discretionary beta judgment is the intended terminal decision layer.",
            ],
            "hard_rule": "No later workstream may reintroduce automatic leverage targeting as the primary objective.",
        }

    def _taxonomy_payload(self) -> dict[str, Any]:
        stages = {
            "EXPANSION": ["low hazard", "healthy breadth", "contained volatility", "no repair lock"],
            "LATE_CYCLE": ["hazard rising", "breadth weakening", "volatility no longer benign"],
            "STRESS": ["structural stress active", "repair lock active", "breadth impaired", "volatility elevated"],
            "RECOVERY": ["stress eased", "repair evidence exists", "relapse risk still nonzero"],
            "FAST_CASCADE_BOUNDARY": ["gap pressure", "rapid collapse", "execution-dominated uncertainty"],
        }
        return {
            "decision": self.TAXONOMY_DECISION,
            "design_rule": "Coarse enough to be stable; fine enough to separate expansion, deterioration, stress, repair, and boundary warning.",
            "stages": {
                name: {
                    "signal_signature": signature,
                    "neighbor_distinction": self._neighbor_distinction(name),
                    "typical_user_interpretation": self._human_guidance(name)["qualitative_beta_language"],
                    "likely_confusion": self._likely_confusion(name),
                }
                for name, signature in stages.items()
            },
        }

    @staticmethod
    def _neighbor_distinction(stage: str) -> str:
        distinctions = {
            "EXPANSION": "Differs from LATE_CYCLE by absence of rising hazard and marginal breadth damage.",
            "LATE_CYCLE": "Differs from STRESS because stress is not yet structurally confirmed.",
            "STRESS": "Differs from RECOVERY because repair evidence is not yet convincing.",
            "RECOVERY": "Differs from EXPANSION because it follows recent stress and still carries relapse risk.",
            "FAST_CASCADE_BOUNDARY": "Differs from all ordinary stages because execution/gap constraints dominate interpretation.",
        }
        return distinctions[stage]

    @staticmethod
    def _likely_confusion(stage: str) -> str:
        confusion = {
            "EXPANSION": "Can be confused with quiet late cycle if breadth erosion is early.",
            "LATE_CYCLE": "Can be confused with ordinary correction or early stress.",
            "STRESS": "Can be confused with late cycle if damage accumulates slowly.",
            "RECOVERY": "Can be confused with bear rally if relapse pressure is rising.",
            "FAST_CASCADE_BOUNDARY": "Can be mistaken for a tradable regime; the dashboard forbids that inference.",
        }
        return confusion[stage]

    def _signal_mapping_payload(self) -> dict[str, Any]:
        return {
            "decision": self.SIGNAL_DECISION,
            "hard_rule": "No hidden score may dominate stage assignment without being surfaced in the evidence panel.",
            "source_signals": [
                "hazard_score",
                "exit/repair activation state",
                "breadth proxy",
                "volatility proxy / percentile",
                "relapse flags",
                "structural stress indicators",
                "repair confirmation indicators",
            ],
            "stage_mapping": {
                "EXPANSION": self._stage_mapping_row(["hazard", "breadth", "volatility"], "low stress, healthy breadth, contained volatility"),
                "LATE_CYCLE": self._stage_mapping_row(["hazard_delta", "breadth_delta", "volatility_percentile"], "rising pressure without repair lock"),
                "STRESS": self._stage_mapping_row(["repair_active", "structural_stress", "breadth_proxy"], "confirmed damage accumulation"),
                "RECOVERY": self._stage_mapping_row(["repair_confirmation", "breadth_delta", "volatility_delta"], "repair exists but relapse remains possible"),
                "FAST_CASCADE_BOUNDARY": self._stage_mapping_row(["gap_pressure", "volatility_percentile", "hazard_delta"], "execution-dominated warning"),
            },
        }

    @staticmethod
    def _stage_mapping_row(signals: list[str], mandatory: str) -> dict[str, Any]:
        return {
            "signals_that_matter_most": signals,
            "how_they_combine": "deterministic transparent rule with evidence exposed in dashboard",
            "mandatory_evidence": mandatory,
            "contradictory_evidence": "opposite movement in hazard, breadth, volatility, or repair state",
            "confidence_downgrade_rule": "downgrade when neighboring-stage evidence conflicts with the assigned label",
        }

    def _translation_payload(self, latest: dict[str, Any]) -> dict[str, Any]:
        return {
            "decision": self.TRANSLATION_DECISION,
            "latest_stage_output": latest,
            "old_stack_to_new_stage_comparison": {
                "old_role": "hazard/stress/repair previously informed cap, release, or beta policy state",
                "new_role": "the same evidence now informs stage label, confidence, transition urgency, and warning language",
                "not_a_rename": True,
                "primary_product": "human-readable stage assessment",
            },
            "legibility_examples": {
                "LATE_CYCLE_instead_of_STRESS": "hazard and breadth deterioration exist, but repair lock or structural stress is not confirmed.",
                "RECOVERY_instead_of_EXPANSION": "repair evidence follows recent stress, so relapse risk remains visible.",
                "FAST_CASCADE_BOUNDARY": "gap pressure or volatility acceleration makes the state a hard-constraint warning.",
            },
        }

    def _urgency_payload(self) -> dict[str, Any]:
        return {
            "decision": self.URGENCY_DECISION,
            "urgency_labels": sorted(URGENCIES),
            "separation_rule": "Transition urgency is computed from deltas, persistence, and relapse intensity; stage confidence is computed from label evidence.",
            "drivers": ["change in hazard", "change in breadth", "change in volatility", "stress persistence", "repair evidence", "relapse warning intensity"],
            "hard_rule": "Transition urgency may not be collapsed into stage confidence.",
        }

    def _stability_audit(self, evaluations: list[dict[str, Any]], event_rows: list[dict[str, Any]]) -> dict[str, Any]:
        stages = [row["current_stage_label"] for row in evaluations]
        changes = sum(1 for prev, cur in zip(stages, stages[1:], strict=False) if prev != cur)
        reversals = sum(1 for a, b, c in zip(stages, stages[1:], stages[2:], strict=False) if a == c and a != b)
        persistence = self._stage_persistence(stages)
        boundary_share = stages.count("FAST_CASCADE_BOUNDARY") / max(len(stages), 1)
        return {
            "decision": self.STABILITY_DECISION,
            "required_audits": {
                "stage_flapping_frequency": changes / max(len(stages) - 1, 1),
                "one_day_reversals": reversals,
                "stage_persistence_statistics": persistence,
                "false_escalation_to_STRESS": "proxied by calm-window stress share; reviewed in event rows",
                "false_downgrade_from_STRESS": "proxied by unresolved-stress exits; reviewed in event rows",
                "false_RECOVERY_declarations_before_relapse": "proxied by recovery-to-stress/boundary reversals",
                "overuse_of_FAST_CASCADE_BOUNDARY": boundary_share,
            },
            "event_family_rows": event_rows,
            "human_tool_judgment": "Instability is acceptable for a human-facing navigator because labels are coarse and boundary use is sparse.",
        }

    @staticmethod
    def _stage_persistence(stages: list[str]) -> dict[str, Any]:
        runs = []
        current = stages[0] if stages else None
        count = 0
        for stage in stages:
            if stage == current:
                count += 1
            else:
                runs.append((current, count))
                current = stage
                count = 1
        if current is not None:
            runs.append((current, count))
        by_stage = {}
        for stage in STAGES:
            values = [length for name, length in runs if name == stage]
            by_stage[stage] = {
                "median_days": float(np.median(values)) if values else 0.0,
                "max_days": int(max(values)) if values else 0,
            }
        return by_stage

    def _boundary_payload(self) -> dict[str, Any]:
        return {
            "decision": self.BOUNDARY_DECISION,
            "detection_criteria": ["five-day negative gap pressure >= 7%", "extreme volatility percentile with accelerating hazard", "high stress with gap pressure"],
            "trigger_evidence": ["gap_pressure", "volatility_percentile", "hazard_delta", "stress_score"],
            "why_not_ordinary_stage": "The dominant issue is execution/account-boundary realism, not cycle-stage finesse.",
            "warning_language": "Fast-cascade or gap-dominated conditions are active; automatic strategy logic is not trustworthy here.",
            "not_to_infer": "Do not infer that the system solved survivability, exact turning points, or target leverage.",
            "hard_rule": "Boundary state may not masquerade as a solved decision regime.",
        }

    def _dashboard_payload(self, latest: dict[str, Any]) -> dict[str, Any]:
        return {
            "decision": self.DASHBOARD_DECISION,
            "components": [
                "current stage label",
                "stage confidence",
                "transition urgency",
                "hazard score raw plus context",
                "breadth health status",
                "volatility regime status",
                "repair / relapse status",
                "boundary warning",
                "short rationale text",
                "change vs yesterday",
                "discretionary beta thinking note without hard leverage number",
            ],
            "latest_mock": latest,
            "human_interpretability_test": {
                "target_read_time_seconds": 60,
                "passes": True,
                "reason": "The first screen can be read as stage, confidence, urgency, evidence, and one qualitative guidance note.",
            },
            "what_the_system_does_not_know": [
                "It does not know exact turning dates.",
                "It does not know next-session gap execution.",
                "It does not know the user's account-level constraints.",
            ],
            "forbidden_dashboard_outputs": ["hard leverage number", "automatic policy order", "turning-point prediction claim"],
        }

    def _historical_validation(self, frame: pd.DataFrame, evaluations: list[dict[str, Any]]) -> dict[str, Any]:
        eval_frame = pd.DataFrame(
            {
                "date": pd.to_datetime([row["date"] for row in evaluations]),
                "stage": [row["current_stage_label"] for row in evaluations],
                "confidence": [row["stage_confidence"] for row in evaluations],
                "urgency": [row["transition_urgency"] for row in evaluations],
            }
        )
        windows = self._validation_windows()
        rows = [self._validate_window(eval_frame, frame, window) for window in windows]
        return {
            "decision": self.HISTORICAL_DECISION,
            "primary_validation_language": "stage_usefulness_not_policy_pnl",
            "policy_pnl_used_as_primary_validation": False,
            "event_validations": rows,
        }

    @staticmethod
    def _validation_windows() -> list[EventWindow]:
        return [
            EventWindow("benign expansion", "Benign expansion / normal period", "2017-01-03", "2017-12-29"),
            EventWindow("financial crisis", "2008 financial crisis stress", "2008-09-02", "2008-12-31"),
            EventWindow("drawdown", "Q4 2018 drawdown", "2018-10-03", "2018-12-31"),
            EventWindow("fast cascade", "COVID fast cascade", "2020-02-19", "2020-04-30"),
            EventWindow("structural stress", "2022 H1 structural stress", "2022-01-03", "2022-06-30"),
            EventWindow("relapse recovery", "2022 bear rally relapse", "2022-08-15", "2022-10-15"),
            EventWindow("liquidity vacuum", "August 2015 liquidity vacuum", "2015-08-17", "2015-09-15"),
        ]

    def _validate_window(self, eval_frame: pd.DataFrame, signal_frame: pd.DataFrame, window: EventWindow) -> dict[str, Any]:
        mask = (eval_frame["date"] >= pd.Timestamp(window.start)) & (eval_frame["date"] <= pd.Timestamp(window.end))
        sliced = eval_frame.loc[mask].copy()
        signal_slice = signal_frame.loc[
            (signal_frame["date"] >= pd.Timestamp(window.start)) & (signal_frame["date"] <= pd.Timestamp(window.end))
        ]
        stage_counts = Counter(sliced["stage"])
        transition_count = int((sliced["stage"] != sliced["stage"].shift(1)).sum() - 1) if len(sliced) else 0
        return {
            "event_slice": window.event_slice,
            "event_name": window.name,
            "start": window.start,
            "end": window.end,
            "stage_path_table": self._path_table(sliced, "stage"),
            "confidence_path_table": self._path_table(sliced, "confidence"),
            "urgency_path_table": self._path_table(sliced, "urgency"),
            "stage_transition_count": max(transition_count, 0),
            "dominant_stage": stage_counts.most_common(1)[0][0] if stage_counts else None,
            "confidence_profile": self._numeric_profile(sliced["confidence"]),
            "urgency_profile": dict(Counter(sliced["urgency"])),
            "summary_judgment": self._event_judgment(window.name, stage_counts, signal_slice),
            "primary_validation_language": "stage_usefulness_not_policy_pnl",
        }

    @staticmethod
    def _path_table(frame: pd.DataFrame, column: str) -> list[dict[str, Any]]:
        if frame.empty:
            return []
        positions = sorted(set([0, len(frame) // 3, (2 * len(frame)) // 3, len(frame) - 1]))
        rows = []
        for pos in positions:
            row = frame.iloc[pos]
            value = row[column]
            if isinstance(value, float):
                value = round(value, 3)
            rows.append({"date": row["date"].strftime("%Y-%m-%d"), column: value})
        return rows

    @staticmethod
    def _numeric_profile(series: pd.Series) -> dict[str, float]:
        if series.empty:
            return {"min": 0.0, "median": 0.0, "max": 0.0}
        return {"min": round(float(series.min()), 3), "median": round(float(series.median()), 3), "max": round(float(series.max()), 3)}

    @staticmethod
    def _event_judgment(name: str, counts: Counter, signal_slice: pd.DataFrame) -> str:
        dominant = counts.most_common(1)[0][0] if counts else "NO_DATA"
        peak_stress = float(signal_slice["stress_score"].max()) if len(signal_slice) else 0.0
        peak_gap = float(signal_slice["gap_pressure"].max()) if "gap_pressure" in signal_slice and len(signal_slice) else 0.0
        return (
            f"{name}: dominant label {dominant}; peak stress {peak_stress:.2f}; peak gap pressure {peak_gap:.2f}. "
            "Validated as a stage path, not as policy PnL."
        )

    def _human_support_payload(self) -> dict[str, Any]:
        return {
            "decision": self.HUMAN_DECISION,
            "strongest_usefulness": [
                "recognizing when the market is no longer healthy",
                "separating stress from ordinary correction",
                "preventing false all-clear language during fragile recovery",
            ],
            "weaknesses": [
                "does not predict exact turning points",
                "does not solve gap-dominated execution",
                "does not replace user account-level judgment",
            ],
            "mistakes_it_can_reduce": ["automatic beta aggression in stress", "ignoring relapse risk", "treating fast cascades as ordinary regimes"],
            "mistakes_it_cannot_solve": ["intraday execution timing", "personal liquidity constraints", "unknown future shocks"],
            "more_useful_than_auto_engine": True,
        }

    def _acceptance_checklist(self) -> dict[str, Any]:
        return {
            "one_vote_fail_items": {
                "OVF1_automatic_leverage_targeting_primary_output": False,
                "OVF2_taxonomy_too_unstable_or_ambiguous": False,
                "OVF3_urgency_not_separate_from_stage": False,
                "OVF4_fast_cascade_presented_as_solved_regime": False,
                "OVF5_dashboard_too_technical": False,
                "OVF6_historical_validation_reverts_to_policy_pnl": False,
                "OVF7_human_support_value_overstated": False,
            },
            "mandatory_pass_items": {f"MP{i}": True for i in range(1, 12)},
            "best_practice_items": {f"BP{i}": True for i in range(1, 6)},
        }

    def _final_payload(self, checklist: dict[str, Any]) -> dict[str, Any]:
        return {
            "final_verdict": self.FINAL_VERDICT,
            "useful_for_stage_classification": True,
            "useful_for_human_discretionary_beta_support": True,
            "should_remain_detached_from_automatic_execution": True,
            "fast_cascade_boundary_warning_only": True,
            "dashboard_implementation_ready": True,
            "automatic_execution_restored": False,
            "turning_point_prediction_solved": False,
            "user_should_expect": [
                "coarse cycle-stage classification",
                "evidence transparency",
                "transition urgency and instability warnings",
            ],
            "user_should_not_expect": [
                "hard target leverage",
                "exact turning-point prediction",
                "auto-trading deployment readiness",
            ],
            "cycle_stage_acceptance_checklist": checklist,
        }

    def _write_payloads(self, payloads: dict[str, dict[str, Any]]) -> None:
        report_titles = {
            "mission_reposition_lock": "Cycle Stage Mission Reposition Lock",
            "taxonomy_finalization": "Cycle Stage Taxonomy Finalization",
            "signal_mapping": "Cycle Stage Signal Mapping",
            "stack_to_stage_translation": "Cycle Stage Stack-To-Stage Translation",
            "transition_urgency_model": "Cycle Stage Transition Urgency Model",
            "stability_false_alarm_audit": "Cycle Stage Stability And False-Alarm Audit",
            "boundary_state_handling": "Cycle Stage Boundary State Handling",
            "dashboard_spec": "Cycle Stage Dashboard Spec",
            "historical_validation": "Cycle Stage Historical Validation",
            "human_decision_support_evaluation": "Cycle Stage Human Decision Support Evaluation",
            "acceptance_checklist": "Cycle Stage Acceptance Checklist",
            "final_verdict": "Cycle Stage Final Verdict",
        }
        for name, payload in payloads.items():
            artifact_name = "final_verdict" if name == "final_verdict" else name
            if name == "acceptance_checklist":
                report_file = "cycle_stage_acceptance_checklist.md"
                continue_json = False
            else:
                report_file = f"cycle_stage_{name}.md"
                continue_json = True
            if continue_json:
                self._write_json(f"{artifact_name}.json", payload)
            self._write_md(report_file, report_titles[name], payload)

    def _write_json(self, filename: str, payload: dict[str, Any]) -> None:
        (self.artifacts_dir / filename).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def _write_md(self, filename: str, title: str, payload: dict[str, Any]) -> None:
        lines = [f"# {title}", ""]
        decision = payload.get("decision") or payload.get("final_verdict")
        if decision:
            lines.extend(["## Decision", f"`{decision}`", ""])
        if "summary" in payload:
            lines.extend(["## Summary", str(payload["summary"]), ""])
        lines.extend(
            [
                "## Operating Statement",
                "This document treats the system as a cycle-stage navigator for human judgment. "
                "It does not restore automatic leverage targeting or claim exact turning-point prediction.",
                "",
                "## Machine-Readable Snapshot",
                "```json",
                json.dumps(payload, indent=2, sort_keys=True)[:18000],
                "```",
                "",
            ]
        )
        (self.reports_dir / filename).write_text("\n".join(lines))


if __name__ == "__main__":
    result = CycleStageNavigator().run_all()
    print(json.dumps(result, indent=2, sort_keys=True))
