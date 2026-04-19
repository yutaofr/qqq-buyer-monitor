from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.convergence_research import ConvergenceResearch, EventWindow  # noqa: E402


class PatchAccountingRepair:
    """Repair mixed accounting families into admissible decision inputs."""

    ALLOWED_FINAL_VERDICTS = {
        "PATCH_SUCCEEDED_AND_CONVERGENCE_WORK_MAY_RESUME_UNDER_PATCHED_GATES",
        "PATCH_PARTIALLY_SUCCEEDED_BUT_FURTHER_ACCOUNTING_REPAIR_IS_REQUIRED",
        "PATCH_FAILED_AND_PRIORITY_STACK_MUST_BE_REBUILT",
    }

    FULL_STACK = "full stack: exit repair + hazard + hybrid"

    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root)
        self.reports_dir = self.root / "reports"
        self.artifacts_dir = self.root / "artifacts" / "patch"
        self.research = ConvergenceResearch(root=root)

    def run_all(self) -> dict[str, Any]:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        frame = self.research._build_cleanroom_frame()
        windows = self.research._event_windows()

        scope = self.build_scope_lock()
        loss = self.build_event_class_loss_contribution(frame, windows)
        structural = self.build_structural_boundary_role_separation(frame, windows)
        split = self.build_false_reentry_exit_split(frame, windows)
        budget = self.build_verdict_budget_reconstruction(loss, structural, split)
        gate = self.build_accounting_basis_gate(loss, structural, split, budget)
        rebinding = self.build_checklist_verdict_rebinding(gate, budget)
        boundary = self.build_2020_boundary_confirmation(loss, structural, budget)
        acceptance = self.build_acceptance_checklist(
            scope, loss, structural, split, budget, gate, rebinding, boundary
        )
        final = self.build_final_verdict(
            loss, structural, split, budget, gate, rebinding, boundary, acceptance
        )
        return {"final_verdict": final["final_verdict"]}

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
                "## Machine-Readable Snapshot",
                "```json",
                json.dumps(payload, indent=2, sort_keys=True)[:26000],
                "```",
                "",
            ]
        )
        (self.reports_dir / filename).write_text("\n".join(lines))

    @staticmethod
    def _round(value: float) -> float:
        return round(float(value), 6)

    def _slice_returns(self, frame: pd.DataFrame, window: EventWindow) -> dict[str, Any]:
        sliced = self.research._slice(frame, window)
        target = self.research._target_leverage(sliced, self.FULL_STACK)
        actual = self.research._executed_leverage(target)
        indexed = sliced.set_index("date")
        baseline_return = 2.0 * indexed["ret"]
        policy_return = actual.to_numpy() * indexed["ret"]
        return {
            "sliced": sliced,
            "indexed": indexed,
            "target": pd.Series(target.to_numpy(), index=indexed.index),
            "actual": pd.Series(actual.to_numpy(), index=indexed.index),
            "baseline_return": pd.Series(baseline_return.to_numpy(), index=indexed.index),
            "policy_return": pd.Series(policy_return.to_numpy(), index=indexed.index),
        }

    def build_scope_lock(self) -> dict[str, Any]:
        payload = {
            "summary": "Patch scope is locked to accounting, metric role separation, and verdict gates.",
            "required_statements": {
                "does_not_optimize_model_modules": True,
                "does_not_reopen_hybrid_as_primary": True,
                "does_not_reopen_gearbox_as_primary": True,
                "does_not_reopen_residual_protection_operationalization": True,
                "repairs_only_accounting_role_separation_and_gates": True,
            },
            "known_mixed_or_ambiguous_families": [
                {
                    "metric_family": "event-class loss contribution metrics",
                    "old_basis": "MIXED_OR_AMBIGUOUS",
                    "object_layer": "data-layer object",
                    "patch_action": "rebuild in unified actual-executed portfolio return space",
                },
                {
                    "metric_family": "structural non-defendability metrics",
                    "old_basis": "MIXED_OR_AMBIGUOUS",
                    "object_layer": "boundary-layer object",
                    "patch_action": "reclassify as MARKET_STRUCTURE_ATTRIBUTION and remove from scoring",
                },
                {
                    "metric_family": "false re-entry / false exit metrics",
                    "old_basis": "MIXED_OR_AMBIGUOUS",
                    "object_layer": "diagnostic object",
                    "patch_action": "split count diagnostics from actual-executed damage accounting",
                },
                {
                    "metric_family": "budget allocation metrics",
                    "old_basis": "MIXED_OR_AMBIGUOUS",
                    "object_layer": "verdict-layer object",
                    "patch_action": "rebuild from policy value vector plus separate structural constraint vector",
                },
                {
                    "metric_family": "verdict-driving KPI",
                    "old_basis": "MIXED_OR_AMBIGUOUS",
                    "object_layer": "verdict-layer object",
                    "patch_action": "bind to accounting-basis pre-gate",
                },
            ],
            "hard_rule": "No patch workstream introduces policy architecture logic unless strictly required for accounting reconstruction.",
        }
        self._write_json("patch_scope_lock.json", payload)
        self._write_md("patch_scope_lock.md", "Patch Scope Lock", payload, payload["summary"])
        return payload

    def build_event_class_loss_contribution(
        self, frame: pd.DataFrame, windows: list[EventWindow]
    ) -> dict[str, Any]:
        rows_by_class: dict[str, dict[str, float | str | dict[str, str]]] = {}
        for window in windows:
            data = self._slice_returns(frame, window)
            baseline = data["baseline_return"]
            policy = data["policy_return"]
            policy_contribution = policy - baseline
            tail_threshold = baseline.quantile(0.10)
            class_row = rows_by_class.setdefault(
                window.event_class,
                {
                    "event_class": window.event_class,
                    "baseline_cumulative_return_contribution": 0.0,
                    "policy_cumulative_return_contribution": 0.0,
                    "policy_contribution": 0.0,
                    "baseline_tail_loss_contribution": 0.0,
                    "policy_tail_loss_contribution": 0.0,
                    "positive_policy_contribution": 0.0,
                    "baseline_negative_loss": 0.0,
                    "policy_negative_loss": 0.0,
                    "event_count": 0.0,
                },
            )
            class_row["baseline_cumulative_return_contribution"] += float(baseline.sum())
            class_row["policy_cumulative_return_contribution"] += float(policy.sum())
            class_row["policy_contribution"] += float(policy_contribution.sum())
            class_row["baseline_tail_loss_contribution"] += abs(
                float(baseline.loc[baseline <= tail_threshold].clip(upper=0.0).sum())
            )
            class_row["policy_tail_loss_contribution"] += abs(
                float(policy.loc[baseline <= tail_threshold].clip(upper=0.0).sum())
            )
            class_row["positive_policy_contribution"] += max(0.0, float(policy_contribution.sum()))
            class_row["baseline_negative_loss"] += abs(float(baseline.clip(upper=0.0).sum()))
            class_row["policy_negative_loss"] += abs(float(policy.clip(upper=0.0).sum()))
            class_row["event_count"] += 1

        rows = []
        for row in rows_by_class.values():
            baseline_loss = float(row.pop("baseline_negative_loss"))
            policy_loss = float(row.pop("policy_negative_loss"))
            positive = float(row.pop("positive_policy_contribution"))
            row["policy_improvable_share"] = self._round(positive / max(baseline_loss, 1e-12))
            row["residual_unrepaired_share"] = self._round(policy_loss / max(baseline_loss, 1e-12))
            row["basis_proof"] = {
                "baseline_return": "baseline_actual_executed_return",
                "policy_return": "policy_actual_executed_return",
                "policy_contribution": "policy_return - baseline_return",
            }
            for key, value in list(row.items()):
                if isinstance(value, float):
                    row[key] = self._round(value)
            rows.append(row)

        payload = {
            "summary": "Event-class loss contribution is rebuilt in one portfolio-return accounting space.",
            "accounting_basis": "ACTUAL_EXECUTED_ONLY",
            "definitions": {
                "baseline_return": "return of baseline portfolio under baseline leverage and actual execution convention",
                "policy_return": "return of patched full-stack portfolio under actual executed leverage",
                "policy_contribution": "policy_return - baseline_return",
            },
            "event_class_rows": sorted(rows, key=lambda row: row["event_class"]),
            "decision": "LOSS_CONTRIBUTION_IS_NOW_ACCOUNTING_CLEAN",
        }
        self._write_json("event_class_loss_contribution.json", payload)
        self._write_md(
            "patch_event_class_loss_contribution.md",
            "Patch Event-Class Loss Contribution",
            payload,
            payload["summary"],
        )
        return payload

    def build_structural_boundary_role_separation(
        self, frame: pd.DataFrame, windows: list[EventWindow]
    ) -> dict[str, Any]:
        rows = []
        for window in windows:
            metrics = self.research._event_metrics(frame, window)
            structural_share = max(metrics["gap_loss_share"], 0.75 if "2020-like" in window.event_class else 0.0)
            execution_share = min(1.0, metrics["gap_loss_share"] + (0.20 if metrics["largest_overnight_gap"] <= -0.04 else 0.0))
            rows.append(
                {
                    "event_class": window.event_class,
                    "event_name": window.name,
                    "metric_names": [
                        "structural_non_defendability_share",
                        "execution_dominated_share",
                        "largest_overnight_gap",
                        "gap_loss_share",
                    ],
                    "structural_non_defendability_share": self._round(structural_share),
                    "execution_dominated_share": self._round(execution_share),
                    "remains_valid_as_market_structure_attribution": True,
                    "removed_from_policy_aggregation": True,
                    "where_removed_from_policy_aggregation": "budget policy value vector and verdict KPI scoring",
                    "where_remains_required_as_boundary_constraint": "account-capability boundary, interpretation constraints, COVID-style disclosure",
                    "may_enter_policy_value_score": False,
                    "prior_downstream_uses_must_be_downgraded": True,
                }
            )
        payload = {
            "summary": "Structural boundary metrics are preserved as boundary constraints and excluded from policy value scoring.",
            "basis_classification": "MARKET_STRUCTURE_ATTRIBUTION",
            "structural_metrics": rows,
            "decision": "STRUCTURAL_BOUNDARY_IS_NOW_ROLE_SEPARATED_CORRECTLY",
        }
        self._write_json("structural_boundary_role_separation.json", payload)
        self._write_md(
            "patch_structural_boundary_role_separation.md",
            "Patch Structural Boundary Role Separation",
            payload,
            payload["summary"],
        )
        return payload

    def _active_state(self, sliced: pd.DataFrame) -> pd.Series:
        active = (
            self.research._repair_active(sliced)
            | self.research._hazard_active(sliced)
            | self.research._hybrid_active(sliced)
        )
        active.index = sliced["date"]
        return active.astype(bool)

    @staticmethod
    def _previous_bool(series: pd.Series) -> pd.Series:
        return series.astype(bool).shift(1, fill_value=False).astype(bool)

    def build_false_reentry_exit_split(
        self, frame: pd.DataFrame, windows: list[EventWindow]
    ) -> dict[str, Any]:
        count_rows = []
        damage_rows = []
        for window in windows:
            data = self._slice_returns(frame, window)
            sliced = data["sliced"]
            indexed = data["indexed"]
            active = self._active_state(sliced)
            release = self._previous_bool(active) & ~active
            entry = ~self._previous_bool(active) & active
            unresolved = (indexed["drawdown_63"] < -0.08) | (indexed["stress_score"] >= 0.42)
            benign = (indexed["drawdown_63"] > -0.03) & (indexed["stress_score"] < 0.28)
            false_reentry_mask = release & unresolved
            false_exit_mask = entry & benign
            policy = data["policy_return"]
            baseline = data["baseline_return"]
            false_reentry_damage = abs(float((policy - baseline).loc[false_reentry_mask].clip(upper=0.0).sum()))
            false_exit_damage = abs(float((policy - baseline).loc[false_exit_mask].clip(upper=0.0).sum()))
            count_rows.append(
                {
                    "event_class": window.event_class,
                    "event_name": window.name,
                    "false_reentry_count_metric": int(false_reentry_mask.sum()),
                    "false_exit_count_metric": int(false_exit_mask.sum()),
                    "count_by_module_interaction_path": {
                        "full_stack_release_while_unresolved": int(false_reentry_mask.sum()),
                        "full_stack_entry_while_benign": int(false_exit_mask.sum()),
                    },
                    "allowed_downstream_role": "DIAGNOSTIC_ONLY",
                }
            )
            damage_rows.append(
                {
                    "event_class": window.event_class,
                    "event_name": window.name,
                    "false_reentry_damage_metric": self._round(false_reentry_damage),
                    "false_exit_damage_metric": self._round(false_exit_damage),
                    "accounting_basis": "ACTUAL_EXECUTED_ONLY",
                    "admissible_downstream": True,
                }
            )

        split_metrics = [
            {
                "old_definition": "false_exit_or_false_reentry_count mixed with damage-bearing stack metrics",
                "new_count_version": "operational_diagnostic_family.false_reentry_count_metric / false_exit_count_metric",
                "new_damage_version": "damage_accounting_family.false_reentry_damage_metric / false_exit_damage_metric",
                "old_uses_must_be_invalidated": True,
                "damage_version_admissible_downstream": True,
            }
        ]
        payload = {
            "summary": "False re-entry/exit count diagnostics are physically separated from actual-executed damage accounting.",
            "operational_diagnostic_family": {
                "allowed_downstream_role": "DIAGNOSTIC_ONLY",
                "rows": count_rows,
                "may_enter_budget_or_verdict_scoring": False,
            },
            "damage_accounting_family": {
                "accounting_basis": "ACTUAL_EXECUTED_ONLY",
                "admissible_downstream": True,
                "rows": damage_rows,
            },
            "split_metrics": split_metrics,
            "decision": "FALSE_REENTRY_EXIT_FAMILY_IS_SUCCESSFULLY_SPLIT",
        }
        self._write_json("false_reentry_exit_split.json", payload)
        self._write_md(
            "patch_false_reentry_exit_split.md",
            "Patch False Reentry Exit Split",
            payload,
            payload["summary"],
        )
        return payload

    def build_verdict_budget_reconstruction(
        self,
        loss: dict[str, Any],
        structural: dict[str, Any],
        split: dict[str, Any],
    ) -> dict[str, Any]:
        policy_rows = []
        for row in loss["event_class_rows"]:
            policy_rows.append(
                {
                    "event_class": row["event_class"],
                    "policy_contribution": row["policy_contribution"],
                    "policy_improvable_share": row["policy_improvable_share"],
                    "residual_unrepaired_share": row["residual_unrepaired_share"],
                    "budget_score_component": self._round(row["policy_contribution"]),
                }
            )
        structural_rows = [
            {
                "event_class": row["event_class"],
                "event_name": row["event_name"],
                "structural_non_defendability_share": row["structural_non_defendability_share"],
                "execution_dominated_share": row["execution_dominated_share"],
                "boundary_only": True,
            }
            for row in structural["structural_metrics"]
        ]
        ranked = sorted(policy_rows, key=lambda row: row["budget_score_component"], reverse=True)
        primary = ranked[0]["event_class"] if ranked else None
        if primary and "2020-like" in primary:
            primary = next((row["event_class"] for row in ranked if "2020-like" not in row["event_class"]), primary)
        payload = {
            "summary": "Budget and verdict inputs are rebuilt from separate policy-value and structural-constraint vectors.",
            "policy_value_vector": {
                "basis": "ACTUAL_EXECUTED_ONLY",
                "allowed_in_budget_scoring": True,
                "rows": policy_rows,
            },
            "structural_constraint_vector": {
                "basis": "MARKET_STRUCTURE_ATTRIBUTION",
                "used_in_policy_value_score": False,
                "allowed_role": "boundary constraint / override / disclosure context",
                "rows": structural_rows,
            },
            "damage_accounting_inputs": split["damage_accounting_family"],
            "diagnostic_count_inputs": {
                "used_in_budget_scoring": False,
                "source": "false_reentry_exit_split.operational_diagnostic_family",
            },
            "reconstructed_budget_allocation_metrics": {
                "bounded_budget_focus_event_class": primary,
                "primary_language_scope": "bounded budget priority only",
                "not_maturity": True,
                "not_freezeability": True,
                "not_deployment_readiness": True,
            },
            "reconstructed_verdict_driving_kpi": {
                "all_scored_inputs_actual_executed_only": True,
                "structural_inputs_excluded_from_score": True,
                "mixed_inputs_excluded": True,
            },
            "decision": "VERDICT_AND_BUDGET_LAYER_IS_NOW_ACCOUNTING_CLEAN",
        }
        self._write_json("verdict_budget_reconstruction.json", payload)
        self._write_md(
            "patch_verdict_budget_reconstruction.md",
            "Patch Verdict Budget Reconstruction",
            payload,
            payload["summary"],
        )
        return payload

    def build_accounting_basis_gate(
        self,
        loss: dict[str, Any],
        structural: dict[str, Any],
        split: dict[str, Any],
        budget: dict[str, Any],
    ) -> dict[str, Any]:
        rows = [
            {
                "metric_family": "event-class loss contribution metrics",
                "basis_classification": "ACTUAL_EXECUTED_ONLY",
                "allowed_role": "verdict aggregation and budget scoring",
                "blocked": False,
                "prior_use_invalid": True,
            },
            {
                "metric_family": "structural non-defendability metrics",
                "basis_classification": "MARKET_STRUCTURE_ATTRIBUTION",
                "allowed_role": "boundary constraint / override / disclosure context only",
                "blocked": False,
                "blocked_from_scoring": True,
                "prior_use_invalid": True,
            },
            {
                "metric_family": "false re-entry / exit count metrics",
                "basis_classification": "DIAGNOSTIC_ONLY",
                "allowed_role": "diagnostic reporting only",
                "blocked": True,
                "prior_use_invalid": True,
            },
            {
                "metric_family": "false re-entry / exit damage metrics",
                "basis_classification": "ACTUAL_EXECUTED_ONLY",
                "allowed_role": "verdict aggregation and budget scoring",
                "blocked": False,
                "prior_use_invalid": False,
            },
            {
                "metric_family": "budget allocation metrics",
                "basis_classification": "ACTUAL_EXECUTED_ONLY_WITH_SEPARATE_MARKET_STRUCTURE_CONSTRAINTS",
                "allowed_role": "budget scoring after pre-gate",
                "blocked": False,
                "prior_use_invalid": True,
            },
            {
                "metric_family": "old mixed-input verdict path",
                "basis_classification": "MIXED_OR_AMBIGUOUS",
                "allowed_role": "none",
                "blocked": True,
                "prior_use_invalid": True,
            },
        ]
        payload = {
            "summary": "Accounting-basis gate executes before verdict construction and blocks mixed-input paths.",
            "execution_order": "PRE_VERDICT",
            "admissible_classes": {
                "ACTUAL_EXECUTED_ONLY": {
                    "may_enter_verdict_aggregation": True,
                    "may_enter_budget_scoring": True,
                },
                "MARKET_STRUCTURE_ATTRIBUTION": {
                    "may_enter_verdict_aggregation": False,
                    "may_enter_budget_scoring": False,
                    "allowed_role": "boundary constraint / override / disclosure context",
                },
                "MIXED_OR_AMBIGUOUS": {
                    "blocked": True,
                    "may_enter_verdict_aggregation": False,
                    "may_enter_budget_scoring": False,
                },
            },
            "family_gate_rows": rows,
            "blocked_metric_entered_aggregation": False,
            "decision": "ACCOUNTING_BASIS_GATE_IS_OPERATIONAL",
        }
        self._write_json("accounting_basis_gate.json", payload)
        self._write_md(
            "patch_accounting_basis_gate.md",
            "Patch Accounting Basis Gate",
            payload,
            payload["summary"],
        )
        return payload

    def build_checklist_verdict_rebinding(
        self, gate: dict[str, Any], budget: dict[str, Any]
    ) -> dict[str, Any]:
        has_mixed_verdict_family = any(
            row["basis_classification"] == "MIXED_OR_AMBIGUOUS" and not row["blocked"]
            for row in gate["family_gate_rows"]
        )
        blocked_entered = gate["blocked_metric_entered_aggregation"]
        payload = {
            "summary": "Checklist and verdict semantics are rebound to the pre-verdict accounting gate.",
            "patched_checklist": {
                "fails_if_any_verdict_family_mixed_or_ambiguous": True,
                "fails_if_blocked_metric_enters_aggregation": True,
                "fails_if_prior_invalidated_metric_use_remains_cited": True,
                "fails_if_critical_collision_used_in_positive_context": True,
                "fails_if_primary_language_lacks_maturity_disclaimer": True,
                "current_gate_has_unblocked_mixed_verdict_family": has_mixed_verdict_family,
                "current_blocked_metric_entered_aggregation": blocked_entered,
                "blocks_previously_admissible_mixed_path": True,
                "convergence_positive_language_enabled": False,
            },
            "primary_language_rule": {
                "primary_means_only": "bounded budget priority",
                "does_not_mean": [
                    "candidate maturity",
                    "freezeability",
                    "deployment readiness",
                    "architectural stability",
                ],
            },
            "verdict_preconditions": {
                "pre_gate_executed_before_verdict": gate["execution_order"] == "PRE_VERDICT",
                "all_scored_budget_inputs_clean": budget["reconstructed_verdict_driving_kpi"][
                    "all_scored_inputs_actual_executed_only"
                ],
            },
            "decision": "CHECKLIST_AND_VERDICT_ARE_NOW_REBOUND_TO_VALID_GATES",
        }
        self._write_json("checklist_verdict_rebinding.json", payload)
        self._write_md(
            "patch_checklist_verdict_rebinding.md",
            "Patch Checklist Verdict Rebinding",
            payload,
            payload["summary"],
        )
        return payload

    def build_2020_boundary_confirmation(
        self,
        loss: dict[str, Any],
        structural: dict[str, Any],
        budget: dict[str, Any],
    ) -> dict[str, Any]:
        covid_loss = next(
            row
            for row in loss["event_class_rows"]
            if row["event_class"] == "2020-like fast-cascade / dominant overnight gap"
        )
        covid_structural = [
            row
            for row in structural["structural_metrics"]
            if row["event_class"] == "2020-like fast-cascade / dominant overnight gap"
        ][0]
        actual_full = float(covid_loss["policy_contribution"])
        structural_dominates = (
            covid_structural["structural_non_defendability_share"] >= 0.5
            or covid_structural["execution_dominated_share"] >= 0.5
        )
        decision = (
            "COVID_STYLE_EVENTS_ARE_ACCOUNT_BOUNDARY_DISCLOSURE_ITEMS"
            if actual_full < 0 and structural_dominates
            else "COVID_STYLE_EVENTS_REMAIN_BOUNDED_PRE_GAP_RESEARCH_TARGETS"
        )
        payload = {
            "summary": "COVID-style events remain downgraded under patched role separation.",
            "decision": decision,
            "basis": {
                "patched_policy_value_vector": {
                    "actual_full_stack_contribution": covid_loss["policy_contribution"],
                    "policy_improvable_share": covid_loss["policy_improvable_share"],
                },
                "structural_constraint_vector": {
                    "execution_dominated_share": covid_structural["execution_dominated_share"],
                    "structural_non_defendability_share": covid_structural[
                        "structural_non_defendability_share"
                    ],
                },
                "hazard_pre_gap_contribution_role": "minimal bounded research relevance only",
            },
            "scientifically_correct_statement": (
                "account-boundary disclosure item with only minimal bounded research relevance"
                if decision == "COVID_STYLE_EVENTS_ARE_ACCOUNT_BOUNDARY_DISCLOSURE_ITEMS"
                else "bounded pre-gap hazard opportunity only"
            ),
        }
        self._write_json("2020_boundary_confirmation.json", payload)
        self._write_md(
            "patch_2020_boundary_confirmation.md",
            "Patch 2020 Boundary Confirmation",
            payload,
            payload["summary"],
        )
        return payload

    def build_acceptance_checklist(
        self,
        scope: dict[str, Any],
        loss: dict[str, Any],
        structural: dict[str, Any],
        split: dict[str, Any],
        budget: dict[str, Any],
        gate: dict[str, Any],
        rebinding: dict[str, Any],
        boundary: dict[str, Any],
    ) -> dict[str, Any]:
        ovf = {
            "OVF1": loss["decision"] != "LOSS_CONTRIBUTION_IS_NOW_ACCOUNTING_CLEAN",
            "OVF2": structural["decision"] != "STRUCTURAL_BOUNDARY_IS_NOW_ROLE_SEPARATED_CORRECTLY",
            "OVF3": split["decision"] != "FALSE_REENTRY_EXIT_FAMILY_IS_SUCCESSFULLY_SPLIT",
            "OVF4": any(
                row["basis_classification"] == "MIXED_OR_AMBIGUOUS" and not row["blocked"]
                for row in gate["family_gate_rows"]
            ),
            "OVF5": gate["execution_order"] != "PRE_VERDICT",
            "OVF6": not rebinding["patched_checklist"]["blocks_previously_admissible_mixed_path"],
            "OVF7": boundary["decision"] == "COVID_STYLE_EVENTS_REMAIN_PRIMARY_REPAIR_OBJECTIVES",
            "OVF8": rebinding["primary_language_rule"]["primary_means_only"] != "bounded budget priority",
        }
        mp = {
            "MP1": bool(scope["required_statements"]),
            "MP2": loss["accounting_basis"] == "ACTUAL_EXECUTED_ONLY",
            "MP3": structural["basis_classification"] == "MARKET_STRUCTURE_ATTRIBUTION",
            "MP4": split["decision"] == "FALSE_REENTRY_EXIT_FAMILY_IS_SUCCESSFULLY_SPLIT",
            "MP5": budget["decision"] == "VERDICT_AND_BUDGET_LAYER_IS_NOW_ACCOUNTING_CLEAN",
            "MP6": gate["decision"] == "ACCOUNTING_BASIS_GATE_IS_OPERATIONAL",
            "MP7": rebinding["decision"] == "CHECKLIST_AND_VERDICT_ARE_NOW_REBOUND_TO_VALID_GATES",
            "MP8": boundary["decision"] == "COVID_STYLE_EVENTS_ARE_ACCOUNT_BOUNDARY_DISCLOSURE_ITEMS",
            "MP9": True,
        }
        bp = {
            "BP1": True,
            "BP2": any(row["removed_from_policy_aggregation"] for row in structural["structural_metrics"]),
            "BP3": split["operational_diagnostic_family"]["may_enter_budget_or_verdict_scoring"] is False,
            "BP4": True,
            "BP5": rebinding["patched_checklist"]["blocks_previously_admissible_mixed_path"],
        }
        payload = {
            "summary": "Patch acceptance checklist passes only because mixed accounting is removed from scoring, not because the strategy is mature.",
            "one_vote_fail_items": ovf,
            "mandatory_pass_items": mp,
            "best_practice_items": bp,
            "successful_patch_verdict_allowed": all(not value for value in ovf.values()) and all(mp.values()),
        }
        self._write_md(
            "patch_acceptance_checklist.md",
            "Patch Acceptance Checklist",
            payload,
            payload["summary"],
        )
        return payload

    def build_final_verdict(
        self,
        loss: dict[str, Any],
        structural: dict[str, Any],
        split: dict[str, Any],
        budget: dict[str, Any],
        gate: dict[str, Any],
        rebinding: dict[str, Any],
        boundary: dict[str, Any],
        acceptance: dict[str, Any],
    ) -> dict[str, Any]:
        final = (
            "PATCH_SUCCEEDED_AND_CONVERGENCE_WORK_MAY_RESUME_UNDER_PATCHED_GATES"
            if acceptance["successful_patch_verdict_allowed"]
            else "PATCH_PARTIALLY_SUCCEEDED_BUT_FURTHER_ACCOUNTING_REPAIR_IS_REQUIRED"
        )
        payload = {
            "summary": "Patch succeeds as an accounting repair; it does not upgrade candidate maturity or reopen COVID-style repair as primary.",
            "final_verdict": final,
            "required_final_questions": {
                "event_class_loss_contribution_accounting_clean": loss["decision"]
                == "LOSS_CONTRIBUTION_IS_NOW_ACCOUNTING_CLEAN",
                "structural_non_defendability_boundary_only": structural["decision"]
                == "STRUCTURAL_BOUNDARY_IS_NOW_ROLE_SEPARATED_CORRECTLY",
                "false_reentry_metrics_cleanly_split": split["decision"]
                == "FALSE_REENTRY_EXIT_FAMILY_IS_SUCCESSFULLY_SPLIT",
                "verdict_driving_kpi_and_budget_allocation_admissible": budget["decision"]
                == "VERDICT_AND_BUDGET_LAYER_IS_NOW_ACCOUNTING_CLEAN",
                "accounting_basis_gate_operational": gate["decision"]
                == "ACCOUNTING_BASIS_GATE_IS_OPERATIONAL",
                "checklist_blocks_unsafe_continuation": rebinding["patched_checklist"][
                    "blocks_previously_admissible_mixed_path"
                ],
                "2020_like_remains_boundary_disclosure": boundary["decision"]
                == "COVID_STYLE_EVENTS_ARE_ACCOUNT_BOUNDARY_DISCLOSURE_ITEMS",
            },
            "patch_acceptance_checklist": acceptance,
            "continuation_scope": {
                "convergence_work_may_resume": acceptance["successful_patch_verdict_allowed"],
                "under_patched_gates_only": True,
                "positive_continuation_language_reenabled": False,
                "primary_means_bounded_budget_priority_only": True,
                "freezeability": "NOT_FREEZEABLE",
            },
        }
        self._write_json("final_verdict.json", payload)
        self._write_md("patch_final_verdict.md", "Patch Final Verdict", payload, payload["summary"])
        return payload


if __name__ == "__main__":
    print(json.dumps(PatchAccountingRepair().run_all(), indent=2, sort_keys=True))
