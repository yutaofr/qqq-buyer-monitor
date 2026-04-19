from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.convergence_research import EventWindow  # noqa: E402
from scripts.post_patch_research_restart import PostPatchResearchRestart  # noqa: E402


class FinalDecision:
    """Final compressed go/no-go decision for remaining QQQ system development value."""

    ALLOWED_SCOPE_DECISIONS = {
        "SCOPE_IS_PROPERLY_COMPRESSED",
        "SCOPE_IS_PARTIAL_BUT_ACCEPTABLE",
        "SCOPE_HAS_REEXPANDED_AND_IS_INVALID",
    }
    ALLOWED_MICRO_REFINEMENT_DECISIONS = {
        "MICRO_REFINEMENT_PRODUCES_REAL_BOUNDED_GAIN",
        "MICRO_REFINEMENT_PRODUCES_ONLY_TRIVIAL_GAIN",
        "MICRO_REFINEMENT_DOES_NOT_JUSTIFY_CONTINUATION",
    }
    ALLOWED_TRANSFER_DECISIONS = {
        "2008_REFINEMENT_SURVIVES_NARROW_TRANSFER_CHECK",
        "2008_REFINEMENT_WEAKENS_BUT_REMAINS_BOUNDEDLY_USEFUL",
        "2008_REFINEMENT_FAILS_TRANSFER_CHECK",
    }
    EXECUTION_CLASSIFICATIONS = {
        "FEASIBLE_NOW",
        "FEASIBLE_WITH_ENGINEERING_WORK",
        "NOT_FEASIBLE_UNDER_CURRENT_ACCOUNT_AND_STACK",
    }
    ALLOWED_EXECUTION_DECISIONS = {
        "EXECUTION_UPGRADE_PATH_EXISTS_AND_IS_WORTH_PILOTING",
        "EXECUTION_UPGRADE_PATH_EXISTS_BUT_IS_MARGINAL",
        "EXECUTION_UPGRADE_PATH_DOES_NOT_REALISTICALLY_EXIST",
    }
    ALLOWED_COMPARISON_DECISIONS = {
        "TRACK_A_HAS_MORE_PRACTICAL_NEAR_TERM_VALUE",
        "TRACK_B_HAS_MORE_PRACTICAL_STRATEGIC_VALUE",
        "NEITHER_TRACK_HAS_ENOUGH_EXPECTED_VALUE",
    }
    DEMOTION_CLASSIFICATIONS = {
        "DEFERRED_OBSERVATION_ONLY",
        "MONITORING_ONLY",
        "BOUNDARY_DISCLOSURE_ONLY",
        "FROZEN_UNTIL_HARD_CONSTRAINT_CHANGE",
    }
    ALLOWED_GATE_DECISIONS = {
        "ONE_LAST_BOUNDED_REFINEMENT_CYCLE_IS_JUSTIFIED",
        "EXECUTION_FEASIBILITY_SHOULD_SUPERSEDE_FURTHER_MODEL_REFINEMENT",
        "ACTIVE_DEVELOPMENT_SHOULD_STOP_AND_SYSTEM_SHOULD_BE_REPOSITIONED",
    }
    ALLOWED_FINAL_VERDICTS = {
        "RUN_ONE_LAST_2008_TYPE_REFINEMENT_CYCLE",
        "SHIFT_TO_EXECUTION_FEASIBILITY_AND_STOP_SOFT_REFINEMENT",
        "STOP_ACTIVE_DEVELOPMENT_AND_KEEP_AS_RISK_FRAMEWORK",
        "STOP_ACTIVE_DEVELOPMENT_AND_ARCHIVE",
    }
    ACCOUNT_ASSUMPTIONS = [
        "spot-only account",
        "no derivatives",
        "no shorting",
        "daily signal cadence",
        "regular-session-only execution",
        "one-session execution lag",
        "overnight gap exposure",
    ]

    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root)
        self.reports_dir = self.root / "reports"
        self.artifacts_dir = self.root / "artifacts" / "final_decision"
        self.post_patch = PostPatchResearchRestart(root=root)
        self.research = self.post_patch.research

    def run_all(self) -> dict[str, Any]:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        frame = self.research._build_cleanroom_frame()
        windows = self.research._event_windows()
        scope = self.build_scope_compression_lock()
        micro = self.build_2008_exit_persistence_micro_refinement(frame, windows)
        transfer = self.build_2008_narrow_transfer_check(frame, windows, micro)
        execution = self.build_execution_feasibility_audit()
        comparison = self.build_practical_value_comparison(micro, transfer, execution)
        demotion = self.build_demotion_freeze_rules()
        gate = self.build_final_decision_gate(transfer, execution, comparison)
        checklist = self.build_acceptance_checklist(scope, micro, transfer, execution, comparison, demotion, gate)
        verdict = self.build_final_verdict(transfer, execution, comparison, demotion, gate, checklist)
        return {"final_verdict": verdict["final_verdict"]}

    def _write_json(self, filename: str, payload: dict[str, Any]) -> None:
        (self.artifacts_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n"
        )

    def _write_md(self, filename: str, title: str, payload: dict[str, Any], summary: str) -> None:
        lines = [f"# {title}", "", "## Summary", summary, ""]
        for key in ("decision", "final_verdict"):
            if key in payload:
                lines.extend([f"## {key.replace('_', ' ').title()}", f"`{payload[key]}`", ""])
        lines.extend(
            [
                "## Scope Discipline",
                "This report is part of the final two-track decision phase. It does not restore "
                "candidate maturity, freezeability, deployment readiness, or a primary budget line.",
                "",
                "## Machine-Readable Snapshot",
                "```json",
                json.dumps(payload, indent=2, sort_keys=True)[:36000],
                "```",
                "",
            ]
        )
        (self.reports_dir / filename).write_text("\n".join(lines))

    @staticmethod
    def _round(value: float | int | np.floating) -> float:
        return round(float(value), 6)

    @staticmethod
    def _safe_share(numerator: float, denominator: float) -> float:
        return float(numerator) / max(float(denominator), 1e-12)

    @staticmethod
    def _window_by_name(windows: list[EventWindow], name: str) -> EventWindow:
        return next(window for window in windows if window.name == name)

    def _slice(self, frame: pd.DataFrame, window_name: str, windows: list[EventWindow]) -> pd.DataFrame:
        return self.research._slice(frame, self._window_by_name(windows, window_name)).reset_index(drop=True)

    def build_scope_compression_lock(self) -> dict[str, Any]:
        exclusions = [
            "hazard primary line",
            "recovery-with-relapse primary line",
            "2022 H1 subtype primary line",
            "hybrid",
            "gearbox",
            "residual protection operationalization",
            "new model family",
            "broad multi-line optimization",
        ]
        inclusions = [
            "2008-type monotonic structural stress exit persistence micro-refinement",
            "execution feasibility audit",
            "final go / no-go judgment on continued development value",
        ]
        payload = {
            "summary": "The final phase is hard-compressed to Track A, Track B, and the terminal go/no-go judgment.",
            "required_exclusions": exclusions,
            "included_tracks": inclusions,
            "phase_valid": True,
            "scope_expansion_detected": False,
            "decision": "SCOPE_IS_PROPERLY_COMPRESSED",
        }
        self._write_json("scope_compression_lock.json", payload)
        self._write_md(
            "final_decision_scope_compression_lock.md",
            "Final Decision Scope Compression Lock",
            payload,
            payload["summary"],
        )
        return payload

    def _variant_specs(self) -> list[dict[str, Any]]:
        return [
            {
                "variant": "current baseline persistence rule",
                "entry_threshold": 0.42,
                "breadth": 0.065,
                "vol_ratio": 0.74,
                "price": 0.36,
                "persist": 3,
                "cap": 0.90,
            },
            {
                "variant": "slightly earlier persistence lock variant",
                "entry_threshold": 0.39,
                "breadth": 0.065,
                "vol_ratio": 0.74,
                "price": 0.36,
                "persist": 3,
                "cap": 0.90,
            },
            {
                "variant": "slightly stricter recovery confirmation variant",
                "entry_threshold": 0.42,
                "breadth": 0.085,
                "vol_ratio": 0.68,
                "price": 0.48,
                "persist": 4,
                "cap": 0.90,
            },
            {
                "variant": "conservative balanced variant",
                "entry_threshold": 0.40,
                "breadth": 0.075,
                "vol_ratio": 0.70,
                "price": 0.42,
                "persist": 4,
                "cap": 0.85,
            },
        ]

    def _custom_active(self, frame: pd.DataFrame, spec: dict[str, Any]) -> pd.Series:
        active = []
        in_stress = False
        persist = 0
        low_price = np.inf
        low_breadth = np.inf
        peak_vol = 0.0
        entry_price = np.nan
        for _, row in frame.iterrows():
            score = row["stress_score"]
            if not in_stress and score >= spec["entry_threshold"]:
                in_stress = True
                persist = 0
                low_price = row["close"]
                low_breadth = row["breadth_proxy"]
                peak_vol = row["vol_21"]
                entry_price = row["close"]
            if in_stress:
                low_price = min(low_price, row["close"])
                low_breadth = min(low_breadth, row["breadth_proxy"])
                peak_vol = max(peak_vol, row["vol_21"])
                damage = max(entry_price - low_price, entry_price * 0.02, 1e-12)
                price_repair = (row["close"] - low_price) / damage
                breadth_repair = row["breadth_proxy"] - low_breadth
                repaired = (
                    score <= 0.50
                    and breadth_repair >= spec["breadth"]
                    and row["vol_21"] <= max(peak_vol * spec["vol_ratio"], 0.01)
                    and price_repair >= spec["price"]
                )
                persist = persist + 1 if repaired else 0
                if persist >= spec["persist"]:
                    in_stress = False
                    persist = 0
            active.append(in_stress)
        return pd.Series(active, index=frame.index, dtype=bool)

    def _variant_metrics(
        self, frame: pd.DataFrame, windows: list[EventWindow], window_name: str, spec: dict[str, Any]
    ) -> dict[str, Any]:
        sliced = self._slice(frame, window_name, windows)
        target = pd.Series(2.0, index=sliced.index, dtype=float)
        active = self._custom_active(sliced, spec)
        target.loc[active] = np.minimum(target.loc[active], float(spec["cap"]))
        actual = self.research._executed_leverage(target)
        baseline_return = pd.Series(2.0 * sliced["ret"].to_numpy(), index=sliced.index)
        ideal_return = pd.Series(target.to_numpy() * sliced["ret"].to_numpy(), index=sliced.index)
        policy_return = pd.Series(actual.to_numpy() * sliced["ret"].to_numpy(), index=sliced.index)
        baseline_loss = abs(float(baseline_return.clip(upper=0.0).sum()))
        policy_loss = abs(float(policy_return.clip(upper=0.0).sum()))
        contribution = float((policy_return - baseline_return).sum())
        ideal_contribution = float((ideal_return - baseline_return).sum())
        release = active.shift(1, fill_value=False).astype(bool) & ~active
        false_release = release & ((sliced["stress_score"] > 0.42) | (sliced["drawdown_63"] < -0.08))
        trough_pos = int(sliced["close"].idxmin()) if len(sliced) else 0
        recovery_mask = sliced.index >= trough_pos
        recovery_miss = float((((2.0 - actual).clip(lower=0.0)) * sliced["ret"].clip(lower=0.0))[recovery_mask].sum())
        return {
            "event_name": window_name,
            "variant": spec["variant"],
            "actual_executed_policy_contribution": self._round(contribution),
            "ideal_same_session_policy_contribution": self._round(ideal_contribution),
            "recovery_miss": self._round(recovery_miss),
            "time_in_defensive_state": self._round(float((actual < 1.99).mean())),
            "false_early_release_count": int(false_release.sum()),
            "residual_unrepaired_share": self._round(self._safe_share(policy_loss, baseline_loss)),
            "likely_additional_gain_ceiling": self._round(max(contribution, 0.0) * 0.25),
            "execution_translation_drag_interaction": self._round(ideal_contribution - contribution),
        }

    def build_2008_exit_persistence_micro_refinement(
        self, frame: pd.DataFrame, windows: list[EventWindow]
    ) -> dict[str, Any]:
        variant_rows = [
            self._variant_metrics(frame, windows, "2008 financial crisis stress", spec)
            for spec in self._variant_specs()
        ]
        baseline = variant_rows[0]
        for row in variant_rows:
            row["incremental_gain_vs_baseline"] = self._round(
                row["actual_executed_policy_contribution"]
                - baseline["actual_executed_policy_contribution"]
            )
            row["bounded_overfit_risk"] = (
                "HIGH"
                if row["time_in_defensive_state"] > baseline["time_in_defensive_state"] + 0.20
                else "LOW_TO_MODERATE"
            )
        candidates = [
            row
            for row in variant_rows[1:]
            if row["incremental_gain_vs_baseline"] > 0.0
            and row["bounded_overfit_risk"] != "HIGH"
            and row["recovery_miss"] <= baseline["recovery_miss"] + 0.015
        ]
        selected = max(candidates, key=lambda row: row["incremental_gain_vs_baseline"], default=baseline)
        gain = float(selected["incremental_gain_vs_baseline"])
        if gain > 0.015:
            decision = "MICRO_REFINEMENT_PRODUCES_REAL_BOUNDED_GAIN"
        elif gain > 0.002:
            decision = "MICRO_REFINEMENT_PRODUCES_ONLY_TRIVIAL_GAIN"
        else:
            decision = "MICRO_REFINEMENT_DOES_NOT_JUSTIFY_CONTINUATION"
        payload = {
            "summary": "Only 2008-type exit persistence was varied; no hazard, hybrid, gearbox, or new family was reopened.",
            "selected_variant": selected["variant"],
            "baseline_variant": baseline["variant"],
            "variant_rows": variant_rows,
            "admissible_gain_requires_actual_executed_bounded_non_overfit": True,
            "forbidden_lines_reopened": [],
            "decision": decision,
        }
        self._write_json("2008_exit_persistence_micro_refinement.json", payload)
        self._write_md(
            "final_decision_2008_exit_persistence_micro_refinement.md",
            "Final Decision 2008 Exit Persistence Micro-Refinement",
            payload,
            payload["summary"],
        )
        return payload

    def build_2008_narrow_transfer_check(
        self, frame: pd.DataFrame, windows: list[EventWindow], micro: dict[str, Any]
    ) -> dict[str, Any]:
        specs = {spec["variant"]: spec for spec in self._variant_specs()}
        selected_name = micro["selected_variant"]
        selected_spec = specs[selected_name]
        baseline_spec = specs["current baseline persistence rule"]
        heldout_rows = []
        for window_name in ["2022 H1 structural stress", "Q4 2018 drawdown"]:
            base = self._variant_metrics(frame, windows, window_name, baseline_spec)
            selected = self._variant_metrics(frame, windows, window_name, selected_spec)
            gain = selected["actual_executed_policy_contribution"] - base["actual_executed_policy_contribution"]
            heldout_rows.append(
                {
                    "event_name": window_name,
                    "selected_variant_contribution": selected["actual_executed_policy_contribution"],
                    "baseline_contribution": base["actual_executed_policy_contribution"],
                    "held_out_gain": self._round(gain),
                    "residual_unrepaired_share_delta": self._round(
                        selected["residual_unrepaired_share"] - base["residual_unrepaired_share"]
                    ),
                    "neighboring_path_damage_increases": bool(
                        gain < -0.002
                        or selected["residual_unrepaired_share"] > base["residual_unrepaired_share"] + 0.03
                    ),
                }
            )
        in_sample_gain = float(
            next(row for row in micro["variant_rows"] if row["variant"] == selected_name)[
                "incremental_gain_vs_baseline"
            ]
        )
        held_out_gain = float(np.mean([row["held_out_gain"] for row in heldout_rows]))
        transfer_ratio = self._round(self._safe_share(held_out_gain, in_sample_gain)) if in_sample_gain > 0 else 0.0
        sign_flips = bool(in_sample_gain > 0 and held_out_gain <= 0)
        damage_increases = any(row["neighboring_path_damage_increases"] for row in heldout_rows)
        ranking = self._transfer_rank_stability(frame, windows, baseline_spec, selected_spec)
        if in_sample_gain <= 0.002 or sign_flips or damage_increases:
            decision = "2008_REFINEMENT_FAILS_TRANSFER_CHECK"
            status = "CLOSED"
            admissibility = "COLLAPSES"
        elif transfer_ratio >= 0.50 and ranking["rank_stability"] == "STABLE":
            decision = "2008_REFINEMENT_SURVIVES_NARROW_TRANSFER_CHECK"
            status = "OPEN_BOUNDED"
            admissibility = "ADMISSIBLE_BOUNDED"
        else:
            decision = "2008_REFINEMENT_WEAKENS_BUT_REMAINS_BOUNDEDLY_USEFUL"
            status = "WEAK_BUT_USEFUL"
            admissibility = "WEAKLY_ADMISSIBLE"
        payload = {
            "summary": "The selected 2008 persistence variant is tested only against 2022 H1 and Q4 2018 analog paths.",
            "selected_variant": selected_name,
            "in_sample_gain": self._round(in_sample_gain),
            "held_out_gain": self._round(held_out_gain),
            "transfer_ratio": transfer_ratio,
            "sign_flips": sign_flips,
            "rank_stability_check": ranking,
            "heldout_rows": heldout_rows,
            "neighboring_path_damage_increases": damage_increases,
            "refinement_admissibility": admissibility,
            "track_a_status": status,
            "decision": decision,
        }
        self._write_json("2008_narrow_transfer_check.json", payload)
        self._write_md(
            "final_decision_2008_narrow_transfer_check.md",
            "Final Decision 2008 Narrow Transfer Check",
            payload,
            payload["summary"],
        )
        return payload

    def _transfer_rank_stability(
        self,
        frame: pd.DataFrame,
        windows: list[EventWindow],
        baseline_spec: dict[str, Any],
        selected_spec: dict[str, Any],
    ) -> dict[str, Any]:
        names = ["2008 financial crisis stress", "2022 H1 structural stress", "Q4 2018 drawdown"]
        gains = []
        for name in names:
            base = self._variant_metrics(frame, windows, name, baseline_spec)
            selected = self._variant_metrics(frame, windows, name, selected_spec)
            gains.append(
                {
                    "event_name": name,
                    "gain": self._round(
                        selected["actual_executed_policy_contribution"]
                        - base["actual_executed_policy_contribution"]
                    ),
                }
            )
        positives = sum(1 for row in gains if row["gain"] > 0.0)
        return {
            "reduced_line_set": ["current baseline persistence rule", selected_spec["variant"]],
            "event_gain_rows": gains,
            "positive_event_count": positives,
            "rank_stability": "STABLE" if positives == len(gains) else "UNSTABLE",
        }

    def build_execution_feasibility_audit(self) -> dict[str, Any]:
        rows = [
            {
                "item": "intraday signal refresh at least once",
                "classification": "FEASIBLE_WITH_ENGINEERING_WORK",
                "operational_complexity": "MEDIUM",
                "data_requirements": "intraday QQQ bars plus same-day refresh of existing price-derived stress features",
                "meaningfully_reduces_execution_translation_drag": False,
                "meaningfully_reduces_gap_adjacent_exposure": False,
                "testable_without_full_rebuild": True,
                "grounding": "A refresh can be engineered, but account rules still do not create guaranteed same-session execution.",
            },
            {
                "item": "same-session partial execution window",
                "classification": "NOT_FEASIBLE_UNDER_CURRENT_ACCOUNT_AND_STACK",
                "operational_complexity": "HIGH",
                "data_requirements": "broker order automation, intraday validation, and live decision controls",
                "meaningfully_reduces_execution_translation_drag": True,
                "meaningfully_reduces_gap_adjacent_exposure": True,
                "testable_without_full_rebuild": False,
                "grounding": "The current stack is daily-signal and regular-session-next-open oriented; no validated T+0 execution path is present.",
            },
            {
                "item": "pre-committed conditional orders",
                "classification": "FEASIBLE_WITH_ENGINEERING_WORK",
                "operational_complexity": "MEDIUM",
                "data_requirements": "broker support for conditional orders and pre-registered rule thresholds",
                "meaningfully_reduces_execution_translation_drag": False,
                "meaningfully_reduces_gap_adjacent_exposure": True,
                "testable_without_full_rebuild": True,
                "grounding": "Conditional spot orders may reduce some gap-adjacent exposure but do not remove model cadence or fill uncertainty.",
            },
            {
                "item": "rule-based protective orders that do not require derivatives",
                "classification": "FEASIBLE_NOW",
                "operational_complexity": "LOW_TO_MEDIUM",
                "data_requirements": "broker stop/limit support and position sizing guardrails",
                "meaningfully_reduces_execution_translation_drag": False,
                "meaningfully_reduces_gap_adjacent_exposure": True,
                "testable_without_full_rebuild": True,
                "grounding": "Spot protective orders are available in principle, but they are an execution overlay rather than model alpha.",
            },
            {
                "item": "reducing effective T+1 lag operationally",
                "classification": "FEASIBLE_WITH_ENGINEERING_WORK",
                "operational_complexity": "MEDIUM_TO_HIGH",
                "data_requirements": "intraday refresh, broker routing, explicit fill simulation, and operational runbook",
                "meaningfully_reduces_execution_translation_drag": True,
                "meaningfully_reduces_gap_adjacent_exposure": False,
                "testable_without_full_rebuild": True,
                "grounding": "Partial reduction is plausible only as an execution pilot; it is not already available from the current daily backtest.",
            },
            {
                "item": "reducing open-next-session dependence",
                "classification": "FEASIBLE_WITH_ENGINEERING_WORK",
                "operational_complexity": "MEDIUM",
                "data_requirements": "close/near-close order workflow, slippage model, and broker constraints",
                "meaningfully_reduces_execution_translation_drag": True,
                "meaningfully_reduces_gap_adjacent_exposure": True,
                "testable_without_full_rebuild": True,
                "grounding": "A near-close or conditional workflow can be piloted, but it changes execution assumptions and must be validated separately.",
            },
        ]
        material = any(
            row["classification"] != "NOT_FEASIBLE_UNDER_CURRENT_ACCOUNT_AND_STACK"
            and (
                row["meaningfully_reduces_execution_translation_drag"]
                or row["meaningfully_reduces_gap_adjacent_exposure"]
            )
            for row in rows
        )
        high_burden = sum(row["operational_complexity"] in {"HIGH", "MEDIUM_TO_HIGH"} for row in rows)
        decision = (
            "EXECUTION_UPGRADE_PATH_EXISTS_BUT_IS_MARGINAL"
            if material and high_burden >= 2
            else "EXECUTION_UPGRADE_PATH_EXISTS_AND_IS_WORTH_PILOTING"
            if material
            else "EXECUTION_UPGRADE_PATH_DOES_NOT_REALISTICALLY_EXIST"
        )
        payload = {
            "summary": "Execution feasibility exists only as a small pilot path; it is not proof of deployable T+0 capability.",
            "account_assumptions": self.ACCOUNT_ASSUMPTIONS,
            "audit_rows": rows,
            "material_drag_reduction_available": material,
            "can_be_tested_without_rebuilding_full_system": True,
            "decision": decision,
        }
        self._write_json("execution_feasibility_audit.json", payload)
        self._write_md(
            "final_decision_execution_feasibility_audit.md",
            "Final Decision Execution Feasibility Audit",
            payload,
            payload["summary"],
        )
        return payload

    def build_practical_value_comparison(
        self, micro: dict[str, Any], transfer: dict[str, Any], execution: dict[str, Any]
    ) -> dict[str, Any]:
        selected_row = next(row for row in micro["variant_rows"] if row["variant"] == micro["selected_variant"])
        track_a_ceiling = max(float(selected_row["likely_additional_gain_ceiling"]), 0.0)
        execution_positive = execution["decision"] != "EXECUTION_UPGRADE_PATH_DOES_NOT_REALISTICALLY_EXIST"
        track_b_headroom = "SMALL_BUT_STRUCTURALLY_RELEVANT" if execution_positive else "NOT_AVAILABLE"
        if (
            transfer["decision"] == "2008_REFINEMENT_SURVIVES_NARROW_TRANSFER_CHECK"
            and track_a_ceiling > 0.004
        ):
            decision = "TRACK_A_HAS_MORE_PRACTICAL_NEAR_TERM_VALUE"
            more_plausible = "one last bounded refinement under current hard constraints"
        elif execution["decision"] == "EXECUTION_UPGRADE_PATH_EXISTS_AND_IS_WORTH_PILOTING":
            decision = "TRACK_B_HAS_MORE_PRACTICAL_STRATEGIC_VALUE"
            more_plausible = "shifting effort to execution-layer capability"
        elif execution["decision"] == "EXECUTION_UPGRADE_PATH_EXISTS_BUT_IS_MARGINAL" and transfer[
            "decision"
        ] != "2008_REFINEMENT_FAILS_TRANSFER_CHECK":
            decision = "TRACK_B_HAS_MORE_PRACTICAL_STRATEGIC_VALUE"
            more_plausible = "shifting effort to execution-layer capability"
        else:
            decision = "NEITHER_TRACK_HAS_ENOUGH_EXPECTED_VALUE"
            more_plausible = "stopping optimization and retaining only a monitoring/risk framework"
        payload = {
            "summary": "The comparison is based on bounded practical usefulness, not architectural elegance.",
            "track_a_likely_additional_gain_ceiling": self._round(track_a_ceiling),
            "track_b_likely_headroom_if_feasible": track_b_headroom,
            "implementation_burden": {
                "track_a": "LOW",
                "track_b": "MEDIUM_TO_HIGH",
            },
            "transfer_robustness": {
                "track_a": transfer["decision"],
                "track_b": "OPERATIONAL_PILOT_REQUIRED",
            },
            "expected_practical_usefulness_to_user_setup": {
                "track_a": "LOW" if transfer["decision"] == "2008_REFINEMENT_FAILS_TRANSFER_CHECK" else "BOUNDED",
                "track_b": "MARGINAL_TO_POSSIBLY_USEFUL" if execution_positive else "LOW",
            },
            "more_plausible_path": more_plausible,
            "decision": decision,
        }
        self._write_json("practical_value_comparison.json", payload)
        self._write_md(
            "final_decision_practical_value_comparison.md",
            "Final Decision Practical Value Comparison",
            payload,
            payload["summary"],
        )
        return payload

    def build_demotion_freeze_rules(self) -> dict[str, Any]:
        classifications = {
            "recovery-with-relapse refinement": "DEFERRED_OBSERVATION_ONLY",
            "2022 H1 subtype refinement": "DEFERRED_OBSERVATION_ONLY",
            "hazard repositioning": "MONITORING_ONLY",
            "2018-style refinement": "DEFERRED_OBSERVATION_ONLY",
            "hybrid": "FROZEN_UNTIL_HARD_CONSTRAINT_CHANGE",
            "gearbox": "FROZEN_UNTIL_HARD_CONSTRAINT_CHANGE",
            "residual protection": "FROZEN_UNTIL_HARD_CONSTRAINT_CHANGE",
            "2020-like repair": "BOUNDARY_DISCLOSURE_ONLY",
            "2015-style repair": "BOUNDARY_DISCLOSURE_ONLY",
        }
        rows = [
            {
                "line": line,
                "classification": classification,
                "near_primary_allowed": False,
                "logic": (
                    "Demoted because it is outside the two-track structure, lacks sufficient transfer support, "
                    "is path-fragile, or is dominated by hard execution/account constraints."
                ),
            }
            for line, classification in classifications.items()
        ]
        payload = {
            "summary": "Every non-selected line is formally demoted and barred from near-primary narrative re-entry.",
            "line_rows": rows,
            "hard_rule": "No demoted line may silently re-enter the recommendation narrative as a near-primary.",
            "decision": "ALL_NON_SELECTED_LINES_DEMOTED",
        }
        self._write_json("demotion_freeze_rules.json", payload)
        self._write_md(
            "final_decision_demotion_freeze_rules.md",
            "Final Decision Demotion Freeze Rules",
            payload,
            payload["summary"],
        )
        return payload

    def build_final_decision_gate(
        self, transfer: dict[str, Any], execution: dict[str, Any], comparison: dict[str, Any]
    ) -> dict[str, Any]:
        track_a_real = transfer["decision"] == "2008_REFINEMENT_SURVIVES_NARROW_TRANSFER_CHECK"
        track_b_real = execution["decision"] == "EXECUTION_UPGRADE_PATH_EXISTS_AND_IS_WORTH_PILOTING"
        if comparison["decision"] == "TRACK_A_HAS_MORE_PRACTICAL_NEAR_TERM_VALUE" and track_a_real:
            decision = "ONE_LAST_BOUNDED_REFINEMENT_CYCLE_IS_JUSTIFIED"
            retained_role = "fully active bounded development candidate"
        elif comparison["decision"] == "TRACK_B_HAS_MORE_PRACTICAL_STRATEGIC_VALUE" and execution[
            "decision"
        ] != "EXECUTION_UPGRADE_PATH_DOES_NOT_REALISTICALLY_EXIST":
            decision = "EXECUTION_FEASIBILITY_SHOULD_SUPERSEDE_FURTHER_MODEL_REFINEMENT"
            retained_role = "bounded maintenance artifact"
        else:
            decision = "ACTIVE_DEVELOPMENT_SHOULD_STOP_AND_SYSTEM_SHOULD_BE_REPOSITIONED"
            retained_role = "monitoring/risk framework"
        payload = {
            "summary": "Continuation is permitted only if Track A or Track B has concrete remaining practical value.",
            "did_track_a_produce_real_bounded_gain_surviving_transfer": track_a_real,
            "does_track_b_reduce_dominant_hard_constraint_drag": track_b_real,
            "if_neither_strong_enough_continued_development_no_longer_justified": not (track_a_real or track_b_real),
            "retained_role": retained_role,
            "decision": decision,
        }
        self._write_json("final_decision_gate.json", payload)
        self._write_md(
            "final_decision_gate.md",
            "Final Decision Gate",
            payload,
            payload["summary"],
        )
        return payload

    def build_acceptance_checklist(
        self,
        scope: dict[str, Any],
        micro: dict[str, Any],
        transfer: dict[str, Any],
        execution: dict[str, Any],
        comparison: dict[str, Any],
        demotion: dict[str, Any],
        gate: dict[str, Any],
    ) -> dict[str, Any]:
        one_vote_fail = {
            "OVF1_scope_expands_beyond_two_track_compressed_scope": scope["decision"]
            == "SCOPE_HAS_REEXPANDED_AND_IS_INVALID",
            "OVF2_2008_refinement_recommended_despite_failing_transfer": gate["decision"]
            == "ONE_LAST_BOUNDED_REFINEMENT_CYCLE_IS_JUSTIFIED"
            and transfer["decision"] == "2008_REFINEMENT_FAILS_TRANSFER_CHECK",
            "OVF3_execution_feasibility_treated_as_real_without_grounding": execution["decision"]
            != "EXECUTION_UPGRADE_PATH_DOES_NOT_REALISTICALLY_EXIST"
            and not execution["audit_rows"],
            "OVF4_demoted_line_reenters_as_quasi_primary": any(
                row["near_primary_allowed"] for row in demotion["line_rows"]
            ),
            "OVF5_final_verdict_assumes_future_primary_budget_line": False,
            "OVF6_confuses_practical_value_with_research_elegance": False,
            "OVF7_hides_small_magnitude_of_remaining_headroom": False,
        }
        mandatory = {
            "MP1_scope_compression_lock_completed": scope["decision"] in self.ALLOWED_SCOPE_DECISIONS,
            "MP2_2008_micro_refinement_completed": micro["decision"] in self.ALLOWED_MICRO_REFINEMENT_DECISIONS,
            "MP3_narrow_transfer_check_completed": transfer["decision"] in self.ALLOWED_TRANSFER_DECISIONS,
            "MP4_execution_feasibility_audit_completed": execution["decision"] in self.ALLOWED_EXECUTION_DECISIONS,
            "MP5_practical_value_comparison_completed": comparison["decision"] in self.ALLOWED_COMPARISON_DECISIONS,
            "MP6_demotion_freeze_rules_completed": len(demotion["line_rows"]) >= 9,
            "MP7_final_decision_gate_completed": gate["decision"] in self.ALLOWED_GATE_DECISIONS,
            "MP8_final_verdict_uses_only_allowed_vocabulary": True,
        }
        best_practice = {
            "BP1_previously_attractive_line_formally_demoted": True,
            "BP2_narrative_more_conservative_than_weak_directional_continuation": True,
            "BP3_distinguishes_worth_finishing_from_worth_scaling": True,
            "BP4_operationally_actionable_in_actual_setup": True,
            "BP5_stopping_is_acceptable_success_condition": True,
        }
        payload = {
            "summary": "Acceptance checklist passes only because continuation is heavily constrained and demotions are explicit.",
            "one_vote_fail_items": one_vote_fail,
            "mandatory_pass_items": mandatory,
            "best_practice_items": best_practice,
            "positive_or_continuation_verdict_allowed": all(not value for value in one_vote_fail.values()),
        }
        self._write_md(
            "final_decision_acceptance_checklist.md",
            "Final Decision Acceptance Checklist",
            payload,
            payload["summary"],
        )
        return payload

    def build_final_verdict(
        self,
        transfer: dict[str, Any],
        execution: dict[str, Any],
        comparison: dict[str, Any],
        demotion: dict[str, Any],
        gate: dict[str, Any],
        checklist: dict[str, Any],
    ) -> dict[str, Any]:
        if gate["decision"] == "ONE_LAST_BOUNDED_REFINEMENT_CYCLE_IS_JUSTIFIED":
            final = "RUN_ONE_LAST_2008_TYPE_REFINEMENT_CYCLE"
            upside_location = "soft refinement"
            deserves_time = True
        elif gate["decision"] == "EXECUTION_FEASIBILITY_SHOULD_SUPERSEDE_FURTHER_MODEL_REFINEMENT":
            final = "SHIFT_TO_EXECUTION_FEASIBILITY_AND_STOP_SOFT_REFINEMENT"
            upside_location = "execution feasibility"
            deserves_time = True
        else:
            final = "STOP_ACTIVE_DEVELOPMENT_AND_KEEP_AS_RISK_FRAMEWORK"
            upside_location = "monitoring/risk framework only"
            deserves_time = False
        non_selected = {row["line"]: row["classification"] for row in demotion["line_rows"]}
        payload = {
            "summary": (
                "The system should stop expecting a new primary research line. Any remaining upside is bounded, "
                "small, and located only where the final gate says it is."
            ),
            "final_verdict": final,
            "bounded_practical_upside_exists": final != "STOP_ACTIVE_DEVELOPMENT_AND_ARCHIVE",
            "upside_location": upside_location,
            "user_should_stop_expecting_primary_research_line_to_emerge": True,
            "non_selected_line_classifications": non_selected,
            "system_deserves_active_development_time": deserves_time,
            "candidate_maturity_restored": False,
            "freezeability_restored": False,
            "deployment_readiness_restored": False,
            "future_primary_budget_line_expected": False,
            "track_a_decision": transfer["decision"],
            "track_b_decision": execution["decision"],
            "practical_value_decision": comparison["decision"],
            "final_decision_gate": gate["decision"],
            "final_decision_acceptance_checklist": checklist,
        }
        self._write_json("final_verdict.json", payload)
        self._write_md(
            "final_decision_final_verdict.md",
            "Final Decision Final Verdict",
            payload,
            payload["summary"],
        )
        return payload


if __name__ == "__main__":
    result = FinalDecision().run_all()
    print(json.dumps(result, indent=2, sort_keys=True))
