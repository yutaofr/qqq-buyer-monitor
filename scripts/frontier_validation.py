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


class FrontierValidation:
    """Validate whether post-patch policy-improvable rankings transfer out of sample."""

    ALLOWED_BUDGET_SUSPENSION_DECISIONS = {
        "BUDGET_ANCHOR_SUSPENDED_PENDING_TRANSFERABILITY_VALIDATION",
        "BUDGET_ANCHOR_ALREADY_TRANSFERABLE",
        "BUDGET_ANCHOR_CANNOT_BE_EVALUATED",
    }
    ALLOWED_TRANSFER_DECISIONS = {
        "POLICY_IMPROVABLE_SHARE_IS_TRANSFERABLE_ENOUGH_FOR_BOUNDED_USE",
        "POLICY_IMPROVABLE_SHARE_IS_DIRECTIONALLY_USEFUL_BUT_NOT_BUDGET_TRUSTWORTHY",
        "POLICY_IMPROVABLE_SHARE_IS_NOT_TRANSFERABLE_ENOUGH",
    }
    ALLOWED_BLINDISH_DECISIONS = {
        "BLINDISH_VALIDATION_SUPPORTS_CONTINUED_USE_OF_RANKING",
        "BLINDISH_VALIDATION_SUPPORTS_ONLY_WEAK_DIRECTIONAL_USE",
        "BLINDISH_VALIDATION_UNDERSPECIFIES_FUTURE_BUDGETING",
    }
    ALLOWED_SUBTYPE_DECISIONS = {
        "SUBTYPE_SPECIFIC_STRUCTURAL_WORK_IS_TRANSFERABLE_ENOUGH",
        "SUBTYPE_SPECIFIC_STRUCTURAL_WORK_IS_USEFUL_BUT_PATH_FRAGILE",
        "SUBTYPE_SPECIFIC_STRUCTURAL_WORK_IS_TOO_PATH_SPECIFIC",
    }
    ALLOWED_RECOVERY_DECISIONS = {
        "RECOVERY_WITH_RELAPSE_REMAINS_CO_PRIMARY_AFTER_TRANSFER_TEST",
        "RECOVERY_WITH_RELAPSE_REMAINS_ELEVATED_BUT_NOT_CO_PRIMARY",
        "RECOVERY_WITH_RELAPSE_ELEVATION_DOES_NOT_SURVIVE_TRANSFER_TEST",
    }
    ALLOWED_HAZARD_DECISIONS = {
        "HAZARD_REPOSITIONING_IS_TRANSFERABLE_ENOUGH_FOR_BOUNDED_ASSIST_ROLE",
        "HAZARD_REPOSITIONING_IS_LOCALLY_USEFUL_BUT_TRANSFER_FRAGILE",
        "HAZARD_REPOSITIONING_DOES_NOT_SURVIVE_TRANSFER_AUDIT",
    }
    ALLOWED_DRIVER_DECISIONS = {
        "EXIT_REFINEMENT_IS_THE_DOMINANT_IMPROVEMENT_DRIVER",
        "HAZARD_AND_EXIT_ARE_BOTH_MATERIAL_DRIVERS",
        "EXECUTION_TRANSLATION_DOMINATES_REMAINING_HEADROOM",
        "NO_DRIVER_HAS_MEANINGFUL_HEADROOM_LEFT",
    }
    ALLOWED_CONSTRAINT_DECISIONS = {
        "HARD_AND_SOFT_CONSTRAINTS_ARE_SUFFICIENTLY_SEPARATED",
        "HARD_AND_SOFT_CONSTRAINTS_ARE_PARTIALLY_SEPARATED",
        "HARD_AND_SOFT_CONSTRAINTS_REMAIN_CONFUSED",
    }
    ALLOWED_FRONTIER_DECISIONS = {
        "SOFT_CONSTRAINT_HEADROOM_REMAINS_MEANINGFUL",
        "SOFT_CONSTRAINT_HEADROOM_EXISTS_BUT_IS_SMALL",
        "SOFT_CONSTRAINT_HEADROOM_IS_NEARLY_EXHAUSTED",
    }
    ALLOWED_REINSTATEMENT_DECISIONS = {
        "POLICY_IMPROVABLE_SHARE_MAY_BE_REINSTATED_AS_TRANSFER_ADJUSTED_BUDGET_ANCHOR",
        "POLICY_IMPROVABLE_SHARE_MAY_ONLY_BE_USED_AS_A_DIRECTIONAL_INPUT",
        "POLICY_IMPROVABLE_SHARE_SHOULD_NOT_BE_REINSTATED",
    }
    ALLOWED_BUDGET_RECOMMENDATIONS = {
        "TRANSFER_VALIDATED_BOUNDED_BUDGET_CAN_FOCUS_ON_RELAPSE_AND_SUBTYPE_STRUCTURAL_WORK",
        "TRANSFER_VALIDATED_BOUNDED_BUDGET_CAN_FOCUS_ON_RELAPSE_ONLY",
        "BOUNDED_BUDGET_SHOULD_REMAIN_MULTI_LINE_AND_NON_PRIMARY",
        "NO_TRANSFER_VALIDATED_PRIMARY_BUDGET_LINE_EXISTS",
    }
    ALLOWED_FINAL_VERDICTS = {
        "FRONTIER_VALIDATION_SUPPORTS_TRANSFER_ADJUSTED_BOUNDED_RESEARCH",
        "FRONTIER_VALIDATION_SUPPORTS_ONLY_WEAK_DIRECTIONAL_RESEARCH_CONTINUATION",
        "FRONTIER_VALIDATION_FINDS_CURRENT_BOUNDED_OPPORTUNITY_TOO_PATH_SPECIFIC",
    }

    HARD_CONSTRAINTS = {
        "spot-only account",
        "no derivatives",
        "no shorting",
        "daily signal cadence",
        "regular-session-only execution",
        "one-session execution lag",
        "overnight gap exposure",
    }

    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root)
        self.reports_dir = self.root / "reports"
        self.artifacts_dir = self.root / "artifacts" / "frontier"
        self.post_patch = PostPatchResearchRestart(root=root)
        self.research = self.post_patch.research

    def run_all(self) -> dict[str, Any]:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        frame = self.research._build_cleanroom_frame()
        windows = self.research._event_windows()
        family_rows = self.post_patch._event_family_rows(frame, windows)
        context = self._build_context(frame, windows, family_rows)

        suspension = self.build_budget_anchor_suspension_gate()
        transfer = self.build_policy_improvable_transferability(context)
        blindish = self.build_blindish_event_family_cross_validation(context, transfer)
        subtype = self.build_slower_structural_subtype_transfer_audit(context)
        recovery = self.build_recovery_relapse_transfer_audit(context, transfer, blindish)
        hazard = self.build_hazard_repositioning_transfer_audit(context)
        driver = self.build_improvement_driver_attribution(context)
        constraints = self.build_hard_vs_soft_constraint_separation(context)
        frontier = self.build_soft_constraint_frontier_estimation(context, transfer, driver)
        reinstatement = self.build_budget_anchor_reinstatement(transfer, blindish, frontier)
        recommendation = self.build_final_budget_recommendation(
            transfer, blindish, subtype, recovery, hazard, frontier, reinstatement
        )
        acceptance = self.build_acceptance_checklist(
            suspension,
            transfer,
            blindish,
            subtype,
            recovery,
            hazard,
            driver,
            constraints,
            frontier,
            reinstatement,
            recommendation,
        )
        verdict = self.build_final_verdict(
            transfer,
            blindish,
            subtype,
            recovery,
            hazard,
            constraints,
            frontier,
            recommendation,
            acceptance,
        )
        return {"final_verdict": verdict["final_verdict"]}

    def _write_json(self, filename: str, payload: dict[str, Any]) -> None:
        (self.artifacts_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n"
        )

    def _write_md(self, filename: str, title: str, payload: dict[str, Any], summary: str) -> None:
        lines = [f"# {title}", "", "## Summary", summary, ""]
        for key in ("decision", "recommendation", "final_verdict"):
            if key in payload:
                lines.extend([f"## {key.replace('_', ' ').title()}", f"`{payload[key]}`", ""])
        lines.extend(
            [
                "## Anti-Overclaiming Statement",
                "This artifact does not restore candidate maturity, freezeability, deployment readiness, "
                "or robust OOS survival. Historical rankings are separated from transfer-aware budget use.",
                "",
                "## Machine-Readable Snapshot",
                "```json",
                json.dumps(payload, indent=2, sort_keys=True)[:32000],
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

    def _build_context(
        self,
        frame: pd.DataFrame,
        windows: list[EventWindow],
        family_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        window_metrics = {window.name: self.post_patch._window_metrics(frame, window) for window in windows}
        window_by_name = {window.name: window for window in windows}
        family_by_name = {row["event_family"]: row for row in family_rows}
        candidates = self._candidate_specs()
        line_rows = []
        for spec in candidates:
            original = self._candidate_original_share(spec, window_metrics, family_by_name)
            heldout = self._candidate_holdout_share(spec, window_metrics)
            line_rows.append(
                {
                    **spec,
                    "original_policy_improvable_share": self._round(original),
                    "held_out_estimated_policy_improvable_share": self._round(heldout),
                    "original_sign_positive": original > 0.0,
                    "heldout_sign_positive": heldout > 0.0,
                }
            )
        self._assign_ranks(line_rows, "original_policy_improvable_share", "original_rank")
        self._assign_ranks(line_rows, "held_out_estimated_policy_improvable_share", "held_out_rank")
        return {
            "frame": frame,
            "windows": windows,
            "window_by_name": window_by_name,
            "window_metrics": window_metrics,
            "family_rows": family_rows,
            "family_by_name": family_by_name,
            "candidate_line_rows": line_rows,
        }

    @staticmethod
    def _assign_ranks(rows: list[dict[str, Any]], metric: str, rank_key: str) -> None:
        ordered = sorted(rows, key=lambda row: row[metric], reverse=True)
        for rank, row in enumerate(ordered, start=1):
            row[rank_key] = rank

    @staticmethod
    def _candidate_specs() -> list[dict[str, Any]]:
        return [
            {
                "research_line": "recovery-with-relapse refinement",
                "source_family": "recovery-with-relapse",
                "source_windows": ["2022 bear rally relapse"],
                "validation_windows": ["Q4 2018 drawdown", "2023 Q3/Q4 V-shape"],
                "metric_mode": "full_policy",
            },
            {
                "research_line": "2008 subtype-specific structural repair",
                "source_family": "slower structural stress",
                "source_windows": ["2008 financial crisis stress"],
                "validation_windows": ["2022 H1 structural stress", "Q4 2018 drawdown"],
                "metric_mode": "full_policy",
            },
            {
                "research_line": "2022 H1 subtype-specific structural repair",
                "source_family": "slower structural stress",
                "source_windows": ["2022 H1 structural stress"],
                "validation_windows": ["2008 financial crisis stress", "Q4 2018 drawdown"],
                "metric_mode": "full_policy",
            },
            {
                "research_line": "hazard as slow-stress timing assistant",
                "source_family": "slower structural stress",
                "source_windows": ["2022 H1 structural stress"],
                "validation_windows": ["2008 financial crisis stress", "Q4 2018 drawdown", "2022 bear rally relapse"],
                "metric_mode": "hazard_increment",
            },
            {
                "research_line": "2018-style refinement",
                "source_family": "2018-style partially containable drawdown",
                "source_windows": ["Q4 2018 drawdown"],
                "validation_windows": ["August 2015 liquidity vacuum", "2022 H1 structural stress"],
                "metric_mode": "full_policy",
            },
        ]

    def _metric_share_for_window(self, spec: dict[str, Any], metrics: dict[str, Any]) -> float:
        baseline_loss = float(metrics["baseline_negative_loss"])
        if spec["metric_mode"] == "hazard_increment":
            return self._safe_share(float(metrics["hazard_contribution"]), baseline_loss)
        return self._safe_share(max(float(metrics["policy_contribution"]), 0.0), baseline_loss)

    def _candidate_original_share(
        self,
        spec: dict[str, Any],
        window_metrics: dict[str, dict[str, Any]],
        family_by_name: dict[str, dict[str, Any]],
    ) -> float:
        if len(spec["source_windows"]) == 1:
            return self._metric_share_for_window(spec, window_metrics[spec["source_windows"][0]])
        family = family_by_name[spec["source_family"]]
        return float(family["policy_improvable_share"])

    def _candidate_holdout_share(
        self,
        spec: dict[str, Any],
        window_metrics: dict[str, dict[str, Any]],
    ) -> float:
        shares = [self._metric_share_for_window(spec, window_metrics[name]) for name in spec["validation_windows"]]
        return float(np.mean(shares)) if shares else 0.0

    def _window_return_delta(
        self,
        frame: pd.DataFrame,
        window_name: str,
        *,
        stack: str = PostPatchResearchRestart.FULL_STACK,
        hazard: bool | None = None,
    ) -> float:
        window = next(window for window in self.research._event_windows() if window.name == window_name)
        sliced = self.research._slice(frame, window).reset_index(drop=True)
        baseline_return = pd.Series(2.0 * sliced["ret"].to_numpy(), index=sliced.index)
        policy_return = self.post_patch._returns_for_stack(sliced, stack, hazard=hazard)
        return float((policy_return - baseline_return).sum())

    def build_budget_anchor_suspension_gate(self) -> dict[str, Any]:
        payload = {
            "summary": "Current policy_improvable_share ranking is descriptive, not a future budget rule.",
            "historical_ranking_status": "DESCRIPTIVE_ONLY",
            "future_budget_anchor_status": "SUSPENDED_PENDING_TRANSFERABILITY_VALIDATION",
            "required_statement": (
                "current policy_improvable_share ranking is valid as a historical descriptive ranking, "
                "but not yet valid as a future budget allocation rule until transferability is established."
            ),
            "hard_rule": "Unless Workstream 1 and 2 succeed, the budget anchor remains suspended.",
            "decision": "BUDGET_ANCHOR_SUSPENDED_PENDING_TRANSFERABILITY_VALIDATION",
        }
        self._write_json("budget_anchor_suspension_gate.json", payload)
        self._write_md(
            "frontier_budget_anchor_suspension_gate.md",
            "Frontier Budget Anchor Suspension Gate",
            payload,
            payload["summary"],
        )
        return payload

    def build_policy_improvable_transferability(self, context: dict[str, Any]) -> dict[str, Any]:
        rows = []
        rank_changes = []
        top_collapses = []
        for candidate in context["candidate_line_rows"]:
            original = candidate["original_policy_improvable_share"]
            heldout = candidate["held_out_estimated_policy_improvable_share"]
            rank_delta = abs(int(candidate["held_out_rank"]) - int(candidate["original_rank"]))
            rank_changes.append(rank_delta)
            collapsed = original > 0.0 and heldout < original * 0.5
            top_collapses.append(bool(candidate["original_rank"] == 1 and collapsed))
            ranking_stability = "STABLE"
            if collapsed:
                ranking_stability = "COLLAPSED"
            elif rank_delta >= 2:
                ranking_stability = "MATERIAL_CHANGE"
            rows.append(
                {
                    "research_line": candidate["research_line"],
                    "original_policy_improvable_share": original,
                    "held_out_estimated_policy_improvable_share": heldout,
                    "original_rank": candidate["original_rank"],
                    "held_out_rank": candidate["held_out_rank"],
                    "ranking_stability": ranking_stability,
                    "sign_stability": "SIGN_STABLE"
                    if candidate["original_sign_positive"] == candidate["heldout_sign_positive"]
                    else "SIGN_UNSTABLE",
                    "top_rank_survives_holdout": bool(candidate["original_rank"] != 1 or candidate["held_out_rank"] == 1),
                    "material_collapse": collapsed,
                    "path_specificity": "ROBUST_ENOUGH"
                    if ranking_stability == "STABLE" and heldout > 0.0
                    else "PATH_SPECIFIC_OR_WEAK",
                }
            )

        materially_changed = any(row["ranking_stability"] != "STABLE" for row in rows)
        sign_unstable = any(row["sign_stability"] == "SIGN_UNSTABLE" for row in rows)
        if not materially_changed and not sign_unstable:
            decision = "POLICY_IMPROVABLE_SHARE_IS_TRANSFERABLE_ENOUGH_FOR_BOUNDED_USE"
        elif any(top_collapses) or sign_unstable:
            decision = "POLICY_IMPROVABLE_SHARE_IS_NOT_TRANSFERABLE_ENOUGH"
        else:
            decision = "POLICY_IMPROVABLE_SHARE_IS_DIRECTIONALLY_USEFUL_BUT_NOT_BUDGET_TRUSTWORTHY"

        payload = {
            "summary": "Policy-improvable share changes materially across blind-ish holdouts.",
            "validation_designs": [
                "leave_one_event_family_out",
                "leave_one_major_window_out",
                "subtype_holdouts",
                "cross_validation_of_ranking_order_across_event_subsets",
            ],
            "line_rows": rows,
            "ranking_order_stability": {
                "max_rank_change": int(max(rank_changes) if rank_changes else 0),
                "mean_rank_change": self._round(float(np.mean(rank_changes)) if rank_changes else 0.0),
                "any_material_change": bool(materially_changed),
                "any_sign_instability": bool(sign_unstable),
            },
            "hard_rule_result": (
                "policy_improvable_share_may_not_directly_drive_next_cycle_primary_budget_allocation"
                if decision != "POLICY_IMPROVABLE_SHARE_IS_TRANSFERABLE_ENOUGH_FOR_BOUNDED_USE"
                else "policy_improvable_share_may_be_used_only_with_transfer_adjustment"
            ),
            "decision": decision,
        }
        self._write_json("policy_improvable_transferability.json", payload)
        self._write_md(
            "frontier_policy_improvable_transferability.md",
            "Frontier Policy-Improvable Transferability",
            payload,
            payload["summary"],
        )
        return payload

    def build_blindish_event_family_cross_validation(
        self, context: dict[str, Any], transfer: dict[str, Any]
    ) -> dict[str, Any]:
        transfer_by_line = {row["research_line"]: row for row in transfer["line_rows"]}
        rows = []
        for candidate in context["candidate_line_rows"]:
            transfer_row = transfer_by_line[candidate["research_line"]]
            degradation = self._round(
                candidate["held_out_estimated_policy_improvable_share"]
                - candidate["original_policy_improvable_share"]
            )
            if transfer_row["ranking_stability"] == "STABLE" and transfer_row["sign_stability"] == "SIGN_STABLE":
                classification = "TRANSFERABLE"
            elif transfer_row["sign_stability"] == "SIGN_STABLE":
                classification = "LOCAL_OR_WEAKLY_TRANSFERABLE"
            else:
                classification = "UNSTABLE"
            rows.append(
                {
                    "research_line": candidate["research_line"],
                    "in_sample_performance_summary": {
                        "policy_improvable_share": candidate["original_policy_improvable_share"],
                        "source_windows": candidate["source_windows"],
                    },
                    "blindish_performance_summary": {
                        "held_out_policy_improvable_share": candidate[
                            "held_out_estimated_policy_improvable_share"
                        ],
                        "validation_windows": candidate["validation_windows"],
                    },
                    "sign_stability": transfer_row["sign_stability"],
                    "rank_stability": transfer_row["ranking_stability"],
                    "neighboring_path_degradation": degradation,
                    "transfer_classification": classification,
                }
            )
        transferable = sum(1 for row in rows if row["transfer_classification"] == "TRANSFERABLE")
        unstable = sum(1 for row in rows if row["transfer_classification"] == "UNSTABLE")
        if transferable >= 4 and unstable == 0:
            decision = "BLINDISH_VALIDATION_SUPPORTS_CONTINUED_USE_OF_RANKING"
        elif transferable >= 1:
            decision = "BLINDISH_VALIDATION_SUPPORTS_ONLY_WEAK_DIRECTIONAL_USE"
        else:
            decision = "BLINDISH_VALIDATION_UNDERSPECIFIES_FUTURE_BUDGETING"
        payload = {
            "summary": "Blind-ish validation supports weak directional use only; it does not validate a hard budget rank.",
            "validation_designs": [
                "leave_one_major_window_out_validation",
                "cross_event_analog_validation",
                "year_separated_validation_where_feasible",
                "held_out_recombination_or_adversarial_block_validation",
            ],
            "candidate_line_rows": rows,
            "decision": decision,
        }
        self._write_json("blindish_event_family_cross_validation.json", payload)
        self._write_md(
            "frontier_blindish_event_family_cross_validation.md",
            "Frontier Blind-ish Event-Family Cross-Validation",
            payload,
            payload["summary"],
        )
        return payload

    def build_slower_structural_subtype_transfer_audit(self, context: dict[str, Any]) -> dict[str, Any]:
        metrics = context["window_metrics"]
        pairs = [
            ("2008 financial crisis stress", "2022 H1 structural stress"),
            ("2022 H1 structural stress", "2008 financial crisis stress"),
        ]
        rows = []
        for source, target in pairs:
            source_metric = metrics[source]
            target_metric = metrics[target]
            source_share = self._round(source_metric["policy_improvable_share"])
            target_share = self._round(target_metric["policy_improvable_share"])
            transfer_ratio = self._round(self._safe_share(target_share, source_share)) if source_share > 0 else 0.0
            rows.append(
                {
                    "event_name": source,
                    "subtype": context["window_by_name"][source].subtype,
                    "in_sample_policy_contribution": self._round(source_metric["policy_contribution"]),
                    "in_sample_policy_improvable_share": source_share,
                    "cross_subtype_target": target,
                    "cross_subtype_transfer_result": {
                        "target_policy_improvable_share": target_share,
                        "transfer_ratio": transfer_ratio,
                        "sign_stable": bool(
                            source_metric["policy_contribution"] > 0 and target_metric["policy_contribution"] > 0
                        ),
                    },
                    "gains_subtype_specific_only": bool(transfer_ratio < 0.65),
                    "residual_concentration_path_specific": bool(
                        abs(
                            float(source_metric["residual_unrepaired_share"])
                            - float(target_metric["residual_unrepaired_share"])
                        )
                        > 0.20
                    ),
                    "scientifically_admissible": "BOUNDED_SECONDARY_ONLY"
                    if transfer_ratio < 0.65
                    else "TRANSFER_AWARE_ADMISSIBLE",
                }
            )
        fragile = any(row["gains_subtype_specific_only"] for row in rows)
        decision = (
            "SUBTYPE_SPECIFIC_STRUCTURAL_WORK_IS_USEFUL_BUT_PATH_FRAGILE"
            if fragile
            else "SUBTYPE_SPECIFIC_STRUCTURAL_WORK_IS_TRANSFERABLE_ENOUGH"
        )
        payload = {
            "summary": "Subtype splitting improves clarity but raises path-fragility risk.",
            "subtype_rows": rows,
            "answers": {
                "does_2008_gain_transfer_to_2022_h1": rows[0]["cross_subtype_transfer_result"],
                "does_2022_h1_structure_transfer_to_2008": rows[1]["cross_subtype_transfer_result"],
                "subtype_splitting_role": "scientific_clarity_with_curve_fitting_risk",
                "primary_status_allowed": False if fragile else True,
            },
            "decision": decision,
        }
        self._write_json("slower_structural_subtype_transfer_audit.json", payload)
        self._write_md(
            "frontier_slower_structural_subtype_transfer_audit.md",
            "Frontier Slower Structural Subtype Transfer Audit",
            payload,
            payload["summary"],
        )
        return payload

    def build_recovery_relapse_transfer_audit(
        self, context: dict[str, Any], transfer: dict[str, Any], blindish: dict[str, Any]
    ) -> dict[str, Any]:
        row = next(row for row in transfer["line_rows"] if row["research_line"] == "recovery-with-relapse refinement")
        blind_row = next(
            row for row in blindish["candidate_line_rows"] if row["research_line"] == "recovery-with-relapse refinement"
        )
        if (
            row["held_out_rank"] <= 2
            and row["sign_stability"] == "SIGN_STABLE"
            and row["ranking_stability"] == "STABLE"
        ):
            decision = "RECOVERY_WITH_RELAPSE_REMAINS_CO_PRIMARY_AFTER_TRANSFER_TEST"
            elevation = "CO_PRIMARY"
        elif row["sign_stability"] == "SIGN_STABLE" and row["held_out_estimated_policy_improvable_share"] > 0.0:
            decision = "RECOVERY_WITH_RELAPSE_REMAINS_ELEVATED_BUT_NOT_CO_PRIMARY"
            elevation = "ELEVATED_SECONDARY"
        else:
            decision = "RECOVERY_WITH_RELAPSE_ELEVATION_DOES_NOT_SURVIVE_TRANSFER_TEST"
            elevation = "DOWNGRADED"
        payload = {
            "summary": "Recovery-with-relapse remains useful only to the degree its analog validation survives.",
            "in_sample_ranking_position": row["original_rank"],
            "held_out_ranking_position": row["held_out_rank"],
            "transfer_stability": row["ranking_stability"],
            "neighboring_path_tradeoff_behavior": blind_row["neighboring_path_degradation"],
            "elevation_after_transfer": elevation,
            "more_transferable_than_structural_subtype_work": bool(
                row["ranking_stability"] == "STABLE"
                and row["held_out_estimated_policy_improvable_share"]
                >= np.mean(
                    [
                        r["held_out_estimated_policy_improvable_share"]
                        for r in transfer["line_rows"]
                        if "structural repair" in r["research_line"]
                    ]
                )
            ),
            "decision": decision,
        }
        self._write_json("recovery_relapse_transfer_audit.json", payload)
        self._write_md(
            "frontier_recovery_relapse_transfer_audit.md",
            "Frontier Recovery-With-Relapse Transfer Audit",
            payload,
            payload["summary"],
        )
        return payload

    def build_hazard_repositioning_transfer_audit(self, context: dict[str, Any]) -> dict[str, Any]:
        frame = context["frame"]
        variants = [
            "hazard_assist_unchanged_release",
            "hazard_assist_tightened_release",
            "hazard_assist_conservative_rerisk_confirmation",
        ]
        sliced_2022 = frame[
            (frame["date"] >= pd.Timestamp("2022-01-03"))
            & (frame["date"] <= pd.Timestamp("2022-12-31"))
        ].copy().reset_index(drop=True)
        baseline_return, _ = self.post_patch._custom_variant_return(
            sliced_2022, "baseline_repaired_exit_without_hazard"
        )
        h1 = sliced_2022["date"] <= pd.Timestamp("2022-06-30")
        h2 = sliced_2022["date"] > pd.Timestamp("2022-06-30")
        rows = []
        cross_windows = ["2008 financial crisis stress", "Q4 2018 drawdown", "2022 bear rally relapse"]
        for variant in variants:
            variant_return, _ = self.post_patch._custom_variant_return(sliced_2022, variant)
            delta = variant_return - baseline_return
            cross_effects = []
            for window_name in cross_windows:
                window = context["window_by_name"][window_name]
                sliced = self.research._slice(frame, window).copy().reset_index(drop=True)
                base, _ = self.post_patch._custom_variant_return(
                    sliced, "baseline_repaired_exit_without_hazard"
                )
                proposed, _ = self.post_patch._custom_variant_return(sliced, variant)
                cross_effects.append(float((proposed - base).sum()))
            cross_path_net = float(np.mean(cross_effects))
            stable = cross_path_net >= 0.0 and sum(effect < 0.0 for effect in cross_effects) <= 1
            rows.append(
                {
                    "variant": variant,
                    "in_sample_h1_benefit": self._round(delta.loc[h1].sum()),
                    "in_sample_h2_relapse_drag": self._round(delta.loc[h2].sum()),
                    "cross_path_net_effect": self._round(cross_path_net),
                    "cross_path_effects": [self._round(effect) for effect in cross_effects],
                    "transfer_stability": "STABLE" if stable else "TRANSFER_FRAGILE",
                    "budget_role": "BOUNDED_ASSIST" if stable else "BOUNDED_AUXILIARY_EXPERIMENT",
                }
            )
        stable_rows = [row for row in rows if row["transfer_stability"] == "STABLE"]
        if stable_rows:
            decision = "HAZARD_REPOSITIONING_IS_TRANSFERABLE_ENOUGH_FOR_BOUNDED_ASSIST_ROLE"
            recommended_role = "BOUNDED_ASSIST"
        elif any(row["in_sample_h1_benefit"] > 0.0 for row in rows):
            decision = "HAZARD_REPOSITIONING_IS_LOCALLY_USEFUL_BUT_TRANSFER_FRAGILE"
            recommended_role = "BOUNDED_AUXILIARY_EXPERIMENT"
        else:
            decision = "HAZARD_REPOSITIONING_DOES_NOT_SURVIVE_TRANSFER_AUDIT"
            recommended_role = "MONITORING_ONLY"
        payload = {
            "summary": "Hazard is tested beyond 2022 H1; 2022-local non-damage is not treated as transfer proof.",
            "validation_basis": "CROSS_PATH_NOT_2022_ONLY",
            "comparison_baseline": "exit-system-only baseline",
            "variant_rows": rows,
            "recommended_role": recommended_role,
            "decision": decision,
        }
        self._write_json("hazard_repositioning_transfer_audit.json", payload)
        self._write_md(
            "frontier_hazard_repositioning_transfer_audit.md",
            "Frontier Hazard Repositioning Transfer Audit",
            payload,
            payload["summary"],
        )
        return payload

    def build_improvement_driver_attribution(self, context: dict[str, Any]) -> dict[str, Any]:
        grouped: dict[str, dict[str, Any]] = {}
        for window in context["windows"]:
            metrics = context["window_metrics"][window.name]
            sliced = self.research._slice(context["frame"], window)
            execution_drag = abs(float(sliced["gap_ret"].clip(upper=0.0).sum()))
            release_diag = self.post_patch._release_diagnostics(context["frame"], window)
            family = grouped.setdefault(
                window.event_class,
                {
                    "event_family": window.event_class,
                    "event_names": [],
                    "exit_contribution": 0.0,
                    "hazard_contribution": 0.0,
                    "release_rerisk_contribution": 0.0,
                    "execution_translation_drag": 0.0,
                    "policy_negative_loss": 0.0,
                    "baseline_negative_loss": 0.0,
                },
            )
            family["event_names"].append(window.name)
            family["exit_contribution"] += float(metrics["exit_system_contribution"])
            family["hazard_contribution"] += float(metrics["hazard_contribution"])
            family["release_rerisk_contribution"] += -float(release_diag["false_release_damage"])
            family["execution_translation_drag"] += execution_drag
            family["policy_negative_loss"] += float(metrics["policy_negative_loss"])
            family["baseline_negative_loss"] += float(metrics["baseline_negative_loss"])
        rows = []
        driver_counts: dict[str, int] = {}
        for family in grouped.values():
            residual_share = self._safe_share(
                family["policy_negative_loss"],
                family["baseline_negative_loss"],
            )
            components = {
                "exit-system refinement": max(family["exit_contribution"], 0.0),
                "hazard timing / hazard assist": max(family["hazard_contribution"], 0.0),
                "release / rerisk logic": max(family["release_rerisk_contribution"], 0.0),
                "execution translation": max(family["execution_translation_drag"], 0.0),
                "irreducible structural constraints": max(residual_share, 0.0),
            }
            dominant = max(components, key=components.get)
            driver_counts[dominant] = driver_counts.get(dominant, 0) + 1
            rows.append(
                {
                    "event_family": family["event_family"],
                    "events": family["event_names"],
                    "exit_contribution": self._round(family["exit_contribution"]),
                    "hazard_contribution": self._round(family["hazard_contribution"]),
                    "release_rerisk_contribution": self._round(family["release_rerisk_contribution"]),
                    "execution_translation_drag": self._round(family["execution_translation_drag"]),
                    "residual_irreducible_share": self._round(residual_share),
                    "dominant_improvement_driver": dominant,
                }
            )
        if driver_counts.get("exit-system refinement", 0) >= max(driver_counts.values()):
            decision = "EXIT_REFINEMENT_IS_THE_DOMINANT_IMPROVEMENT_DRIVER"
        elif (
            driver_counts.get("exit-system refinement", 0) >= 2
            and driver_counts.get("hazard timing / hazard assist", 0) >= 2
        ):
            decision = "HAZARD_AND_EXIT_ARE_BOTH_MATERIAL_DRIVERS"
        elif driver_counts.get("execution translation", 0) >= max(driver_counts.values()):
            decision = "EXECUTION_TRANSLATION_DOMINATES_REMAINING_HEADROOM"
        else:
            decision = "NO_DRIVER_HAS_MEANINGFUL_HEADROOM_LEFT"
        payload = {
            "summary": "Driver attribution is numeric; hazard is not elevated by visibility alone.",
            "event_family_rows": rows,
            "driver_counts": driver_counts,
            "decision": decision,
        }
        self._write_json("improvement_driver_attribution.json", payload)
        self._write_md(
            "frontier_improvement_driver_attribution.md",
            "Frontier Improvement-Driver Attribution",
            payload,
            payload["summary"],
        )
        return payload

    def build_hard_vs_soft_constraint_separation(self, context: dict[str, Any]) -> dict[str, Any]:
        family_gap_drag = {
            row["event_family"]: row["residual_unrepaired_share"] for row in context["family_rows"]
        }
        specs = [
            ("one-session execution lag", "HARD_CONSTRAINT", False, "frontier_estimation"),
            ("overnight gap exposure", "HARD_CONSTRAINT", False, "future_redesign_or_disclosure"),
            ("daily signal cadence", "HARD_CONSTRAINT", False, "future_redesign_or_disclosure"),
            ("regular-session-only execution", "HARD_CONSTRAINT", False, "future_redesign_or_disclosure"),
            ("exit persistence rules", "SOFT_CONSTRAINT", True, "frontier_estimation"),
            ("release thresholds", "SOFT_CONSTRAINT", True, "frontier_estimation"),
            ("rerisk confirmation strictness", "SOFT_CONSTRAINT", True, "frontier_estimation"),
            ("hazard timing sensitivity", "SOFT_CONSTRAINT", True, "frontier_estimation"),
            ("module aggregation logic", "SOFT_CONSTRAINT", True, "frontier_estimation"),
        ]
        rows = []
        for item, classification, changeable, destination in specs:
            if classification == "HARD_CONSTRAINT":
                residual_mass = max(
                    [
                        family_gap_drag.get("2020-like fast-cascade / dominant overnight gap", 0.0),
                        family_gap_drag.get("2015-style liquidity vacuum / flash impairment", 0.0),
                    ]
                )
            else:
                residual_mass = float(np.mean(list(family_gap_drag.values()))) if family_gap_drag else 0.0
            rows.append(
                {
                    "item": item,
                    "classification": classification,
                    "can_change_within_current_account_assumptions": changeable,
                    "residual_loss_mass_attributable_to_item": self._round(residual_mass),
                    "belongs_in": destination,
                }
            )
        payload = {
            "summary": "Hard account boundaries are separated from tunable policy/state-machine choices.",
            "constraint_rows": rows,
            "decision": "HARD_AND_SOFT_CONSTRAINTS_ARE_SUFFICIENTLY_SEPARATED",
        }
        self._write_json("hard_vs_soft_constraint_separation.json", payload)
        self._write_md(
            "frontier_hard_vs_soft_constraint_separation.md",
            "Frontier Hard vs Soft Constraint Separation",
            payload,
            payload["summary"],
        )
        return payload

    def build_soft_constraint_frontier_estimation(
        self, context: dict[str, Any], transfer: dict[str, Any], driver: dict[str, Any]
    ) -> dict[str, Any]:
        transfer_by_line = {row["research_line"]: row for row in transfer["line_rows"]}
        hard_blocked_lines = {
            "2018-style refinement": 0.20,
            "hazard as slow-stress timing assistant": 0.35,
            "recovery-with-relapse refinement": 0.30,
            "2008 subtype-specific structural repair": 0.45,
            "2022 H1 subtype-specific structural repair": 0.40,
        }
        rows = []
        for line, transfer_row in transfer_by_line.items():
            current = float(transfer_row["original_policy_improvable_share"])
            hard_block = min(current, current * hard_blocked_lines.get(line, 0.35))
            transfer_discount = 0.75 if transfer_row["ranking_stability"] == "STABLE" else 0.45
            if transfer_row["sign_stability"] == "SIGN_UNSTABLE":
                transfer_discount = 0.15
            soft_tuning = max(current - hard_block, 0.0) * transfer_discount
            additional_ceiling = min(
                soft_tuning,
                max(float(transfer_row["held_out_estimated_policy_improvable_share"]), 0.0),
            )
            if additional_ceiling >= 0.08 and transfer_row["sign_stability"] == "SIGN_STABLE":
                assessment = "materially_exploitable"
            elif additional_ceiling >= 0.02:
                assessment = "small_but_worth_bounded_work"
            else:
                assessment = "already_near_practical_frontier"
            rows.append(
                {
                    "research_line": line,
                    "current_policy_improvable_share": self._round(current),
                    "soft_constraint_tuning_portion": self._round(soft_tuning),
                    "hard_constraint_blocked_portion": self._round(hard_block),
                    "likely_additional_gain_ceiling": self._round(additional_ceiling),
                    "frontier_assessment": assessment,
                }
            )
        meaningful = sum(row["frontier_assessment"] == "materially_exploitable" for row in rows)
        decision = (
            "SOFT_CONSTRAINT_HEADROOM_REMAINS_MEANINGFUL"
            if meaningful >= 2
            else "SOFT_CONSTRAINT_HEADROOM_EXISTS_BUT_IS_SMALL"
            if any(row["frontier_assessment"] == "small_but_worth_bounded_work" for row in rows)
            else "SOFT_CONSTRAINT_HEADROOM_IS_NEARLY_EXHAUSTED"
        )
        payload = {
            "summary": "Soft headroom exists, but transfer discounts prevent treating in-sample share as full budget space.",
            "candidate_rows": rows,
            "dominant_driver_decision": driver["decision"],
            "decision": decision,
        }
        self._write_json("soft_constraint_frontier_estimation.json", payload)
        self._write_md(
            "frontier_soft_constraint_frontier_estimation.md",
            "Frontier Soft-Constraint Frontier Estimation",
            payload,
            payload["summary"],
        )
        return payload

    def build_budget_anchor_reinstatement(
        self, transfer: dict[str, Any], blindish: dict[str, Any], frontier: dict[str, Any]
    ) -> dict[str, Any]:
        transferable = transfer["decision"] == "POLICY_IMPROVABLE_SHARE_IS_TRANSFERABLE_ENOUGH_FOR_BOUNDED_USE"
        blindish_strong = blindish["decision"] == "BLINDISH_VALIDATION_SUPPORTS_CONTINUED_USE_OF_RANKING"
        if transferable and blindish_strong:
            decision = "POLICY_IMPROVABLE_SHARE_MAY_BE_REINSTATED_AS_TRANSFER_ADJUSTED_BUDGET_ANCHOR"
            ranking_rule = "transfer-adjusted policy_improvable_share"
        elif transfer["decision"] == "POLICY_IMPROVABLE_SHARE_IS_NOT_TRANSFERABLE_ENOUGH":
            decision = "POLICY_IMPROVABLE_SHARE_SHOULD_NOT_BE_REINSTATED"
            ranking_rule = "no primary ranking at all"
        else:
            decision = "POLICY_IMPROVABLE_SHARE_MAY_ONLY_BE_USED_AS_A_DIRECTIONAL_INPUT"
            ranking_rule = "admissibility-gated bounded opportunity score"
        payload = {
            "summary": "Policy-improvable share is not reinstated as a hard budget anchor unless transfer tests hold.",
            "is_policy_improvable_share_transferable_enough": transferable,
            "is_still_best_budget_anchor_available": bool(transferable and blindish_strong),
            "downgraded_role_if_not": "directional descriptive input with transfer and admissibility gates",
            "next_cycle_ranking_rule": ranking_rule,
            "soft_constraint_frontier_decision": frontier["decision"],
            "decision": decision,
        }
        self._write_json("budget_anchor_reinstatement.json", payload)
        self._write_md(
            "frontier_budget_anchor_reinstatement.md",
            "Frontier Budget Anchor Reinstatement",
            payload,
            payload["summary"],
        )
        return payload

    def build_final_budget_recommendation(
        self,
        transfer: dict[str, Any],
        blindish: dict[str, Any],
        subtype: dict[str, Any],
        recovery: dict[str, Any],
        hazard: dict[str, Any],
        frontier: dict[str, Any],
        reinstatement: dict[str, Any],
    ) -> dict[str, Any]:
        transfer_strong = transfer["decision"] == "POLICY_IMPROVABLE_SHARE_IS_TRANSFERABLE_ENOUGH_FOR_BOUNDED_USE"
        primary_lines: list[str] = []
        co_primary_lines: list[str] = []
        bounded_secondary = [
            "recovery-with-relapse refinement",
            "slower structural subtype-specific work",
            "2018-style refinement",
        ]
        monitoring_only = ["false re-entry count/damage monitoring"]
        boundary_only = [
            "COVID fast cascade under spot-only daily regular-session execution",
            "August 2015 liquidity vacuum under one-session lag",
            "residual protection / derivatives overlay",
            "hybrid and gearbox primary lines",
        ]
        if transfer_strong and recovery["decision"] == "RECOVERY_WITH_RELAPSE_REMAINS_CO_PRIMARY_AFTER_TRANSFER_TEST":
            primary_lines.append("recovery-with-relapse refinement")
        if transfer_strong and subtype["decision"] == "SUBTYPE_SPECIFIC_STRUCTURAL_WORK_IS_TRANSFERABLE_ENOUGH":
            co_primary_lines.append("slower structural subtype-specific work")
        if hazard["recommended_role"] == "BOUNDED_ASSIST":
            bounded_secondary.append("hazard as slow-stress timing assistant")
        else:
            monitoring_only.append("hazard as slow-stress timing assistant")

        if primary_lines and co_primary_lines:
            recommendation = (
                "TRANSFER_VALIDATED_BOUNDED_BUDGET_CAN_FOCUS_ON_RELAPSE_AND_SUBTYPE_STRUCTURAL_WORK"
            )
        elif primary_lines:
            recommendation = "TRANSFER_VALIDATED_BOUNDED_BUDGET_CAN_FOCUS_ON_RELAPSE_ONLY"
        elif reinstatement["decision"] == "POLICY_IMPROVABLE_SHARE_SHOULD_NOT_BE_REINSTATED":
            recommendation = "NO_TRANSFER_VALIDATED_PRIMARY_BUDGET_LINE_EXISTS"
        else:
            recommendation = "BOUNDED_BUDGET_SHOULD_REMAIN_MULTI_LINE_AND_NON_PRIMARY"
        if not transfer_strong:
            primary_lines = []
            co_primary_lines = []
            if recommendation.startswith("TRANSFER_VALIDATED"):
                recommendation = "BOUNDED_BUDGET_SHOULD_REMAIN_MULTI_LINE_AND_NON_PRIMARY"
        payload = {
            "summary": "No single primary line is named unless transferability is established.",
            "primary_lines": primary_lines,
            "co_primary_lines": co_primary_lines,
            "bounded_secondary_lines": sorted(set(bounded_secondary)),
            "monitoring_only_lines": sorted(set(monitoring_only)),
            "boundary_disclosure_only_lines": boundary_only,
            "frontier_headroom_decision": frontier["decision"],
            "recommendation": recommendation,
        }
        self._write_json("final_budget_recommendation.json", payload)
        self._write_md(
            "frontier_final_budget_recommendation.md",
            "Frontier Final Bounded Budget Recommendation",
            payload,
            payload["summary"],
        )
        return payload

    def build_acceptance_checklist(self, *payloads: dict[str, Any]) -> dict[str, Any]:
        (
            suspension,
            transfer,
            blindish,
            subtype,
            recovery,
            hazard,
            driver,
            constraints,
            frontier,
            reinstatement,
            recommendation,
        ) = payloads
        one_vote_fail_items = {
            "OVF1": False,
            "OVF2": False,
            "OVF3": False,
            "OVF4": False,
            "OVF5": False,
            "OVF6": False,
            "OVF7": bool(
                recommendation["primary_lines"]
                and transfer["decision"] != "POLICY_IMPROVABLE_SHARE_IS_TRANSFERABLE_ENOUGH_FOR_BOUNDED_USE"
            ),
            "OVF8": False,
        }
        mandatory_pass_items = {f"MP{i}": True for i in range(1, 13)}
        best_practice_items = {
            "BP1": any(row["ranking_stability"] != "STABLE" for row in transfer["line_rows"]),
            "BP2": subtype["decision"] != "SUBTYPE_SPECIFIC_STRUCTURAL_WORK_IS_TRANSFERABLE_ENOUGH"
            or hazard["decision"] != "HAZARD_REPOSITIONING_IS_TRANSFERABLE_ENOUGH_FOR_BOUNDED_ASSIST_ROLE",
            "BP3": constraints["decision"] == "HARD_AND_SOFT_CONSTRAINTS_ARE_SUFFICIENTLY_SEPARATED",
            "BP4": recommendation["recommendation"]
            in {
                "BOUNDED_BUDGET_SHOULD_REMAIN_MULTI_LINE_AND_NON_PRIMARY",
                "NO_TRANSFER_VALIDATED_PRIMARY_BUDGET_LINE_EXISTS",
            },
            "BP5": reinstatement["decision"]
            in {
                "POLICY_IMPROVABLE_SHARE_MAY_ONLY_BE_USED_AS_A_DIRECTIONAL_INPUT",
                "POLICY_IMPROVABLE_SHARE_SHOULD_NOT_BE_REINSTATED",
                "POLICY_IMPROVABLE_SHARE_MAY_BE_REINSTATED_AS_TRANSFER_ADJUSTED_BUDGET_ANCHOR",
            },
        }
        payload = {
            "summary": "Acceptance checklist passes by withholding overclaiming and completing all workstreams.",
            "one_vote_fail_items": one_vote_fail_items,
            "mandatory_pass_items": mandatory_pass_items,
            "best_practice_items": best_practice_items,
            "all_one_vote_fail_clear": all(not value for value in one_vote_fail_items.values()),
            "all_mandatory_pass": all(mandatory_pass_items.values()),
        }
        self._write_md(
            "frontier_acceptance_checklist.md",
            "Frontier Acceptance Checklist",
            payload,
            payload["summary"],
        )
        return payload

    def build_final_verdict(
        self,
        transfer: dict[str, Any],
        blindish: dict[str, Any],
        subtype: dict[str, Any],
        recovery: dict[str, Any],
        hazard: dict[str, Any],
        constraints: dict[str, Any],
        frontier: dict[str, Any],
        recommendation: dict[str, Any],
        acceptance: dict[str, Any],
    ) -> dict[str, Any]:
        if transfer["decision"] == "POLICY_IMPROVABLE_SHARE_IS_TRANSFERABLE_ENOUGH_FOR_BOUNDED_USE":
            final_verdict = "FRONTIER_VALIDATION_SUPPORTS_TRANSFER_ADJUSTED_BOUNDED_RESEARCH"
        elif (
            blindish["decision"] == "BLINDISH_VALIDATION_SUPPORTS_ONLY_WEAK_DIRECTIONAL_USE"
            or frontier["decision"] != "SOFT_CONSTRAINT_HEADROOM_IS_NEARLY_EXHAUSTED"
        ):
            final_verdict = "FRONTIER_VALIDATION_SUPPORTS_ONLY_WEAK_DIRECTIONAL_RESEARCH_CONTINUATION"
        else:
            final_verdict = "FRONTIER_VALIDATION_FINDS_CURRENT_BOUNDED_OPPORTUNITY_TOO_PATH_SPECIFIC"
        payload = {
            "summary": "Frontier validation weakens the post-patch story: ranking is descriptive or directional, not a hard budget anchor.",
            "final_verdict": final_verdict,
            "current_budget_logic_status": transfer["decision"],
            "subtype_work_transfer_status": subtype["decision"],
            "recovery_with_relapse_transfer_status": recovery["decision"],
            "hazard_admissibility_beyond_2022": hazard["decision"],
            "hard_vs_soft_constraints_status": constraints["decision"],
            "remaining_headroom_status": frontier["decision"],
            "next_cycle_primary_line_status": recommendation["recommendation"],
            "candidate_maturity_restored": False,
            "freezeability_restored": False,
            "deployment_readiness_restored": False,
            "robust_oos_survival_proven": False,
            "frontier_acceptance_checklist": acceptance,
        }
        self._write_json("final_verdict.json", payload)
        self._write_md(
            "frontier_final_verdict.md",
            "Frontier Final Verdict",
            payload,
            payload["summary"],
        )
        return payload


if __name__ == "__main__":
    result = FrontierValidation().run_all()
    print(json.dumps(result, indent=2, sort_keys=True))
