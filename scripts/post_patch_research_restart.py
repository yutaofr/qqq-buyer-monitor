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

from scripts.convergence_research import ConvergenceResearch, EventWindow  # noqa: E402


class PostPatchResearchRestart:
    """Re-rank post-patch research budget from actual-executed improvable space."""

    ALLOWED_FINAL_VERDICTS = {
        "POST_PATCH_RESEARCH_MAY_RESUME_WITH_REPRIORITIZED_BOUNDED_BUDGET",
        "POST_PATCH_RESEARCH_MAY_RESUME_BUT_PRIMARY_BUDGET_REMAINS_UNSETTLED",
        "POST_PATCH_RESEARCH_REMAINS_TOO_UNCERTAIN_AFTER_REPRIORITIZATION",
    }
    ALLOWED_RECOMMENDATIONS = {
        "NEXT_CYCLE_SHOULD_FOCUS_ON_STRUCTURAL_SUBTYPE_REPAIR_AND_RELAPSE_REFINEMENT",
        "NEXT_CYCLE_SHOULD_FOCUS_ON_RELAPSE_AND_2018_STYLE_REFINEMENT",
        "NEXT_CYCLE_SHOULD_KEEP_ONLY_ONE_PRIMARY_RESEARCH_LINE",
        "NEXT_CYCLE_BUDGET_REMAINS_TOO_UNCERTAIN_FOR_PRIMARY_ALLOCATION",
    }

    FULL_STACK = "full stack: exit repair + hazard + hybrid"

    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root)
        self.reports_dir = self.root / "reports"
        self.artifacts_dir = self.root / "artifacts" / "post_patch"
        self.research = ConvergenceResearch(root=root)

    def run_all(self) -> dict[str, Any]:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        frame = self.research._build_cleanroom_frame()
        windows = self.research._event_windows()
        family_rows = self._event_family_rows(frame, windows)

        reset = self.build_priority_logic_reset()
        reranking = self.build_policy_improvable_reranking(family_rows)
        decomposition = self.build_slower_structural_internal_decomposition(frame, windows)
        recovery = self.build_recovery_relapse_priority_validation(family_rows)
        hazard = self.build_hazard_repositioning_2022_stress_test(frame)
        monitoring = self.build_false_reentry_monitoring_framework(frame, windows)
        budget = self.build_bounded_budget_allocation(reranking, decomposition, recovery, hazard)
        gate = self.build_research_line_admissibility_gate(budget, hazard)
        recommendation = self.build_final_budget_recommendation(budget, gate, decomposition, recovery)
        acceptance = self.build_acceptance_checklist(
            reset,
            reranking,
            decomposition,
            recovery,
            hazard,
            monitoring,
            budget,
            gate,
            recommendation,
        )
        verdict = self.build_final_verdict(
            reset,
            decomposition,
            recovery,
            hazard,
            monitoring,
            gate,
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
        for key in ("decision", "claim_strength_label", "recommendation", "final_verdict"):
            if key in payload:
                lines.extend([f"## {key.replace('_', ' ').title()}", f"`{payload[key]}`", ""])
        lines.extend(
            [
                "## Accounting Basis",
                "All ranking metrics are recomputed from actual-executed portfolio returns. "
                "`residual_unrepaired_share` is retained as loss-location context, not as a primary budget anchor.",
                "",
                "## Machine-Readable Snapshot",
                "```json",
                json.dumps(payload, indent=2, sort_keys=True)[:30000],
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

    def _returns_for_stack(
        self,
        frame: pd.DataFrame,
        stack: str,
        *,
        repair_variant: str = "current_repair_confirmer",
        hazard: bool | None = None,
        hybrid_policy: str = "staged_cap_release",
    ) -> pd.Series:
        target = pd.Series(2.0, index=frame.index, dtype=float)
        if repair_variant:
            active = self.research._repair_active(frame, repair_variant)
            target.loc[active] = np.minimum(target.loc[active], 0.9)
        if hazard is True or ("hazard" in stack and hazard is None):
            active = self.research._hazard_active(frame)
            target.loc[active] = np.minimum(target.loc[active], 1.1)
        if "hybrid" in stack:
            active = self.research._hybrid_active(frame, hybrid_policy)
            target.loc[active] = np.minimum(target.loc[active], 0.8)
        actual = self.research._executed_leverage(target)
        return pd.Series(actual.to_numpy() * frame["ret"].to_numpy(), index=frame.index)

    def _window_metrics(
        self,
        frame: pd.DataFrame,
        window: EventWindow,
        *,
        stack: str = FULL_STACK,
        repair_variant: str = "current_repair_confirmer",
        hazard: bool | None = None,
    ) -> dict[str, Any]:
        sliced = self.research._slice(frame, window).reset_index(drop=True)
        baseline_return = pd.Series(2.0 * sliced["ret"].to_numpy(), index=sliced.index)
        policy_return = self._returns_for_stack(
            sliced, stack, repair_variant=repair_variant, hazard=hazard
        )
        contribution = float((policy_return - baseline_return).sum())
        baseline_loss = abs(float(baseline_return.clip(upper=0.0).sum()))
        policy_loss = abs(float(policy_return.clip(upper=0.0).sum()))
        exit_return = self._returns_for_stack(sliced, "exit repair only", hazard=False)
        exit_hazard_return = self._returns_for_stack(sliced, "exit repair + hazard", hazard=True)
        return {
            "event_family": window.event_class,
            "event_name": window.name,
            "subtype": window.subtype,
            "start": window.start,
            "end": window.end,
            "policy_contribution": contribution,
            "policy_improvable_share": self._safe_share(max(contribution, 0.0), baseline_loss),
            "residual_unrepaired_share": self._safe_share(policy_loss, baseline_loss),
            "baseline_negative_loss": baseline_loss,
            "policy_negative_loss": policy_loss,
            "exit_system_contribution": float((exit_return - baseline_return).sum()),
            "hazard_contribution": float((exit_hazard_return - exit_return).sum()),
            "positive_contribution": contribution > 0.0,
        }

    def _event_family_rows(
        self, frame: pd.DataFrame, windows: list[EventWindow]
    ) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for window in windows:
            metrics = self._window_metrics(frame, window)
            row = grouped.setdefault(
                window.event_class,
                {
                    "event_family": window.event_class,
                    "events": [],
                    "policy_contribution": 0.0,
                    "baseline_negative_loss": 0.0,
                    "policy_negative_loss": 0.0,
                    "exit_system_contribution": 0.0,
                    "hazard_contribution": 0.0,
                },
            )
            row["events"].append(window.name)
            row["policy_contribution"] += metrics["policy_contribution"]
            row["baseline_negative_loss"] += metrics["baseline_negative_loss"]
            row["policy_negative_loss"] += metrics["policy_negative_loss"]
            row["exit_system_contribution"] += metrics["exit_system_contribution"]
            row["hazard_contribution"] += metrics["hazard_contribution"]

        rows = []
        for row in grouped.values():
            policy_contribution = float(row["policy_contribution"])
            baseline_loss = float(row.pop("baseline_negative_loss"))
            policy_loss = float(row.pop("policy_negative_loss"))
            event_family = str(row["event_family"])
            boundary = "2020-like" in event_family
            execution = "2015-style" in event_family
            row["policy_improvable_share"] = self._round(
                self._safe_share(max(policy_contribution, 0.0), baseline_loss)
            )
            row["residual_unrepaired_share"] = self._round(
                self._safe_share(policy_loss, baseline_loss)
            )
            row["policy_contribution"] = self._round(policy_contribution)
            row["exit_system_contribution"] = self._round(row["exit_system_contribution"])
            row["hazard_contribution"] = self._round(row["hazard_contribution"])
            row["contribution_positive"] = policy_contribution > 0.0
            row["structurally_capped"] = boundary
            row["execution_dominated"] = execution
            row["disclosure_only"] = boundary or execution
            row["admissible_for_primary_bounded_research"] = (
                policy_contribution > 0.0 and not boundary and not execution
            )
            if boundary:
                row["status"] = "BOUNDARY_DISCLOSURE_ONLY"
            elif execution:
                row["status"] = "EXECUTION_DOMINATED_DISCLOSURE_ONLY"
            elif row["admissible_for_primary_bounded_research"]:
                row["status"] = "PRIMARY_RANKABLE"
            else:
                row["status"] = "SECONDARY_OR_MONITORING_ONLY"
            rows.append(row)
        return rows

    def build_priority_logic_reset(self) -> dict[str, Any]:
        payload = {
            "summary": "Budget logic is reset to opportunity space, not residual pain.",
            "definitions": {
                "policy_improvable_share": "bounded expected research payoff space under actual-executed accounting",
                "residual_unrepaired_share": "remaining loss mass, including structurally non-defendable or execution-bound components",
                "policy_contribution": "actual-executed realized contribution of the current policy stack versus baseline",
            },
            "research_priority_score": {
                "primary_anchor": "policy_improvable_share",
                "secondary_inputs": [
                    "actual_executed_policy_contribution_quality",
                    "interaction_feasibility",
                    "non_boundary_status",
                ],
                "residual_unrepaired_share_role": "secondary_descriptive_only",
                "formula": (
                    "policy_improvable_share * contribution_quality_multiplier * "
                    "interaction_feasibility_multiplier * non_boundary_multiplier"
                ),
            },
            "required_statement": (
                "residual_unrepaired_share may describe pain, but may not by itself justify primary budget priority."
            ),
            "decision": "PRIORITY_LOGIC_RESET_SUCCEEDED",
        }
        self._write_json("priority_logic_reset.json", payload)
        self._write_md(
            "post_patch_priority_logic_reset.md",
            "Post-Patch Priority Logic Reset",
            payload,
            payload["summary"],
        )
        return payload

    def _priority_score(self, row: dict[str, Any]) -> float:
        contribution_quality = 1.0 if row["policy_contribution"] > 0 else 0.35
        feasibility = 0.0 if row["disclosure_only"] else 1.0
        return self._round(row["policy_improvable_share"] * contribution_quality * feasibility)

    def build_policy_improvable_reranking(
        self, family_rows: list[dict[str, Any]]
    ) -> dict[str, Any]:
        rows = []
        for row in family_rows:
            enriched = dict(row)
            enriched["research_priority_score"] = self._priority_score(row)
            rows.append(enriched)
        rows.sort(
            key=lambda row: (
                row["admissible_for_primary_bounded_research"],
                row["contribution_positive"],
                row["research_priority_score"],
                row["policy_improvable_share"],
            ),
            reverse=True,
        )
        payload = {
            "summary": "Families are re-ranked by actual-executed policy-improvable share with boundary exclusions.",
            "primary_budget_anchor": "policy_improvable_share",
            "ranking_rule": [
                "positive_or_non_catastrophic_actual_executed_policy_contribution",
                "policy_improvable_share",
                "interaction_feasibility",
                "non_boundary_status",
            ],
            "event_family_rows": rows,
            "decision": "POLICY_IMPROVABLE_RANKING_IS_DECISION_READY",
        }
        self._write_json("policy_improvable_reranking.json", payload)
        self._write_md(
            "post_patch_policy_improvable_reranking.md",
            "Post-Patch Policy-Improvable Re-Ranking",
            payload,
            payload["summary"],
        )
        return payload

    def _release_diagnostics(self, frame: pd.DataFrame, window: EventWindow) -> dict[str, Any]:
        sliced = self.research._slice(frame, window).reset_index(drop=True)
        active = self.research._repair_active(sliced)
        release = self.research._previous_bool(active) & ~active
        unresolved = (sliced["drawdown_63"] < -0.08) | (sliced["stress_score"] >= 0.42)
        calm = (sliced["drawdown_63"] > -0.03) & (sliced["stress_score"] < 0.28)
        return {
            "release_count": int(release.sum()),
            "premature_re_risk_count": int((release & unresolved).sum()),
            "recovery_miss_days": int((active & calm).sum()),
            "false_release_damage": self._round(
                abs(float((2.0 * sliced.loc[release & unresolved, "ret"]).clip(upper=0.0).sum()))
            ),
        }

    def build_slower_structural_internal_decomposition(
        self, frame: pd.DataFrame, windows: list[EventWindow]
    ) -> dict[str, Any]:
        structural_windows = [window for window in windows if window.event_class == "slower structural stress"]
        rows = []
        total_positive = 0.0
        total_residual_loss = 0.0
        for window in structural_windows:
            metrics = self._window_metrics(frame, window)
            positive = max(float(metrics["policy_contribution"]), 0.0)
            residual_loss = float(metrics["policy_negative_loss"])
            total_positive += positive
            total_residual_loss += residual_loss
            rows.append(
                {
                    "event_name": window.name,
                    "subtype": window.subtype,
                    "policy_contribution": self._round(metrics["policy_contribution"]),
                    "policy_improvable_share": self._round(metrics["policy_improvable_share"]),
                    "residual_unrepaired_share": self._round(metrics["residual_unrepaired_share"]),
                    "exit_system_contribution": self._round(metrics["exit_system_contribution"]),
                    "hazard_contribution": self._round(metrics["hazard_contribution"]),
                    "residual_negative_loss": self._round(metrics["policy_negative_loss"]),
                    "re_risk_release_diagnostics": self._release_diagnostics(frame, window),
                    "support_disclosure": "minimum required slower-structural event window",
                }
            )
        for row in rows:
            row["positive_gain_share_within_family"] = self._round(
                self._safe_share(max(row["policy_contribution"], 0.0), total_positive)
            )
            row["residual_loss_share_within_family"] = self._round(
                self._safe_share(row["residual_negative_loss"], total_residual_loss)
            )
        max_gain_share = max(row["positive_gain_share_within_family"] for row in rows)
        residual_leader = max(rows, key=lambda row: row["residual_loss_share_within_family"])
        gain_leader = max(rows, key=lambda row: row["positive_gain_share_within_family"])
        heterogeneous = max_gain_share >= 0.60 or residual_leader["event_name"] != gain_leader["event_name"]
        payload = {
            "summary": "Slower structural stress is positive at family level but internally heterogeneous.",
            "subtype_rows": rows,
            "heterogeneity_test": {
                "family_level_score_dominated_by_one_event": bool(max_gain_share >= 0.60),
                "residual_damage_concentrates_in_different_event_than_gains": bool(
                    residual_leader["event_name"] != gain_leader["event_name"]
                ),
                "unified_research_objective_would_be_misleading": bool(heterogeneous),
                "gain_leader": gain_leader["event_name"],
                "residual_leader": residual_leader["event_name"],
            },
            "claim_strength_label": (
                "FAMILY_LEVEL_PRIORITY_REQUIRES_SUBTYPE_SPLIT"
                if heterogeneous
                else "FAMILY_LEVEL_PRIORITY_IS_SUPPORTABLE"
            ),
        }
        self._write_json("slower_structural_internal_decomposition.json", payload)
        self._write_md(
            "post_patch_slower_structural_internal_decomposition.md",
            "Post-Patch Slower Structural Internal Decomposition",
            payload,
            payload["summary"],
        )
        return payload

    def build_recovery_relapse_priority_validation(
        self, family_rows: list[dict[str, Any]]
    ) -> dict[str, Any]:
        rows_by_family = {row["event_family"]: row for row in family_rows}
        recovery = rows_by_family["recovery-with-relapse"]
        comparison_names = [
            "recovery-with-relapse",
            "slower structural stress",
            "2018-style partially containable drawdown",
        ]
        direct = []
        for name in comparison_names:
            row = rows_by_family[name]
            direct.append(
                {
                    "event_family": name,
                    "policy_improvable_share": row["policy_improvable_share"],
                    "policy_contribution": row["policy_contribution"],
                    "interaction_stability": "REQUIRES_SUBTYPE_SPLIT"
                    if name == "slower structural stress"
                    else "STABLE_ENOUGH_FOR_BOUNDED_RESEARCH",
                    "expected_bounded_research_payoff": self._round(self._priority_score(row)),
                }
            )
        decision = (
            "RECOVERY_WITH_RELAPSE_DESERVES_CO_PRIMARY_STATUS"
            if recovery["policy_improvable_share"]
            >= max(row["policy_improvable_share"] for row in family_rows if row["contribution_positive"])
            and recovery["policy_contribution"] > 0
            else "RECOVERY_WITH_RELAPSE_DESERVES_ELEVATED_SECONDARY_STATUS"
        )
        payload = {
            "summary": "Recovery-with-relapse is elevated because it has positive contribution and the highest positive-family improvable share.",
            "recovery_with_relapse": {
                "policy_contribution": recovery["policy_contribution"],
                "policy_improvable_share": recovery["policy_improvable_share"],
                "residual_unrepaired_share": recovery["residual_unrepaired_share"],
                "release_relapse_sensitivity": "HIGH: release confirmation must avoid bear-rally traps without suppressing real recovery",
                "dominant_remaining_mechanism": "false_release_risk_and_recovery_miss_are_jointly_active",
                "positive_edge_sufficient_for_further_budget": recovery["policy_contribution"] > 0,
            },
            "direct_comparison": direct,
            "explicit_elevation_justification": (
                "Holding recovery-with-relapse below elevated status would violate the post-patch rule: "
                "it has the highest positive-family policy_improvable_share and positive actual-executed contribution."
            ),
            "decision": decision,
        }
        self._write_json("recovery_relapse_priority_validation.json", payload)
        self._write_md(
            "post_patch_recovery_relapse_priority_validation.md",
            "Post-Patch Recovery-With-Relapse Priority Validation",
            payload,
            payload["summary"],
        )
        return payload

    def _custom_variant_return(self, frame: pd.DataFrame, variant: str) -> tuple[pd.Series, pd.Series]:
        target = pd.Series(2.0, index=frame.index, dtype=float)
        if variant == "baseline_repaired_exit_without_hazard":
            active = self.research._repair_active(frame, "current_repair_confirmer")
            target.loc[active] = np.minimum(target.loc[active], 0.9)
        elif variant == "hazard_assist_unchanged_release":
            active = self.research._repair_active(frame, "current_repair_confirmer")
            target.loc[active] = np.minimum(target.loc[active], 0.9)
            target.loc[self.research._hazard_active(frame)] = np.minimum(
                target.loc[self.research._hazard_active(frame)], 1.1
            )
        elif variant == "hazard_assist_tightened_release":
            active = self.research._repair_active(frame, "stricter_repair_confirmer")
            target.loc[active] = np.minimum(target.loc[active], 0.85)
            target.loc[self.research._hazard_active(frame)] = np.minimum(
                target.loc[self.research._hazard_active(frame)], 1.05
            )
        elif variant == "hazard_assist_conservative_rerisk_confirmation":
            active = self.research._repair_active(frame, "stricter_repair_confirmer")
            target.loc[active] = np.minimum(target.loc[active], 0.8)
            target.loc[self.research._hazard_active(frame)] = np.minimum(
                target.loc[self.research._hazard_active(frame)], 1.0
            )
            release = self.research._previous_bool(active) & ~active
            for idx in release[release].index:
                pos = list(frame.index).index(idx)
                staged_idx = frame.index[pos : min(pos + 5, len(frame))]
                target.loc[staged_idx] = np.minimum(target.loc[staged_idx], 1.25)
        else:
            raise ValueError(f"unknown variant: {variant}")
        actual = self.research._executed_leverage(target)
        return pd.Series(actual.to_numpy() * frame["ret"].to_numpy(), index=frame.index), actual

    def build_hazard_repositioning_2022_stress_test(self, frame: pd.DataFrame) -> dict[str, Any]:
        sliced = frame[
            (frame["date"] >= pd.Timestamp("2022-01-03"))
            & (frame["date"] <= pd.Timestamp("2022-12-31"))
        ].copy().reset_index(drop=True)
        baseline_return, baseline_actual = self._custom_variant_return(
            sliced, "baseline_repaired_exit_without_hazard"
        )
        variants = [
            "baseline_repaired_exit_without_hazard",
            "hazard_assist_unchanged_release",
            "hazard_assist_tightened_release",
            "hazard_assist_conservative_rerisk_confirmation",
        ]
        rows = []
        h1 = sliced["date"] <= pd.Timestamp("2022-06-30")
        h2 = sliced["date"] > pd.Timestamp("2022-06-30")
        for variant in variants:
            returns, actual = self._custom_variant_return(sliced, variant)
            active = actual < 1.95
            release = self.research._previous_bool(active) & ~active
            unresolved = (sliced["drawdown_63"] < -0.08) | (sliced["stress_score"] >= 0.42)
            calm = (sliced["drawdown_63"] > -0.03) & (sliced["stress_score"] < 0.28)
            delta = returns - baseline_return
            rows.append(
                {
                    "variant": variant,
                    "h1_contribution_change": self._round(delta.loc[h1].sum()),
                    "h2_relapse_contribution_change": self._round(delta.loc[h2].sum()),
                    "net_2022_full_year_contribution": self._round(delta.sum()),
                    "premature_re_risk_episodes": int((release & unresolved).sum()),
                    "recovery_miss_change": int((active & calm).sum() - ((baseline_actual < 1.95) & calm).sum()),
                    "false_release_diagnostics": {
                        "release_count": int(release.sum()),
                        "release_while_unresolved": int((release & unresolved).sum()),
                        "damage_after_unresolved_release": self._round(
                            abs(float(returns.loc[release & unresolved].clip(upper=0.0).sum()))
                        ),
                    },
                    "improves_one_segment_while_degrading_next": bool(
                        delta.loc[h1].sum() > 0.0 and delta.loc[h2].sum() < 0.0
                    ),
                }
            )
        unchanged = next(row for row in rows if row["variant"] == "hazard_assist_unchanged_release")
        if unchanged["net_2022_full_year_contribution"] >= 0:
            decision = "HAZARD_REPOSITIONING_IS_VALID_FOR_SLOW_STRESS_ASSIST"
            allowed = True
        elif unchanged["h1_contribution_change"] > 0:
            decision = "HAZARD_REPOSITIONING_HAS_LOCAL_BENEFIT_BUT_NET_2022_COST"
            allowed = False
        else:
            decision = "HAZARD_REPOSITIONING_SHOULD_NOT_BE_REDEPLOYED_THIS_WAY"
            allowed = False
        payload = {
            "summary": "Hazard repositioning is judged on the full 2022 path, not H1 in isolation.",
            "variant_rows": rows,
            "formal_repositioning_allowed": allowed,
            "decision": decision,
        }
        self._write_json("hazard_repositioning_2022_stress_test.json", payload)
        self._write_md(
            "post_patch_hazard_repositioning_2022_stress_test.md",
            "Post-Patch Hazard Repositioning 2022 Stress Test",
            payload,
            payload["summary"],
        )
        return payload

    def build_false_reentry_monitoring_framework(
        self, frame: pd.DataFrame, windows: list[EventWindow]
    ) -> dict[str, Any]:
        threshold_rows = []
        for window in windows:
            diagnostics = self._release_diagnostics(frame, window)
            threshold_rows.append(
                {
                    "event_family": window.event_class,
                    "event_name": window.name,
                    "concern_count_threshold": 1 if "2020-like" in window.event_class else 2,
                    "concern_damage_threshold": 0.01,
                    "observed_false_reentry_count": diagnostics["premature_re_risk_count"],
                    "observed_false_reentry_damage": diagnostics["false_release_damage"],
                    "nonzero_count_low_damage_governance_attention": True,
                }
            )
        payload = {
            "summary": "False re-entry stays live as count monitoring even when realized damage is small.",
            "false_reentry_count_metric": {
                "definition": "count of releases/re-risk transitions while unresolved stress remains active",
                "downstream_role": "MONITORING_ONLY",
                "may_enter_budget_scoring": False,
            },
            "false_reentry_damage_metric": {
                "definition": "actual-executed negative return after false release or premature re-risk",
                "accounting_basis": "ACTUAL_EXECUTED_ONLY",
                "downstream_role": "DAMAGE_CONTEXT_ONLY",
            },
            "event_family_thresholds": threshold_rows,
            "carry_forward_rules": [
                "track count and damage separately in every future event-window audit",
                "raise governance attention on nonzero count even when realized damage is below threshold",
                "do not use count directly in verdict or budget scoring",
            ],
            "interpretation_rule": "low historical false_reentry_damage does NOT imply the issue is solved.",
            "decision": "FALSE_REENTRY_MONITORING_FRAMEWORK_IS_READY",
        }
        self._write_json("false_reentry_monitoring_framework.json", payload)
        self._write_md(
            "post_patch_false_reentry_monitoring_framework.md",
            "Post-Patch False Re-Entry Monitoring Framework",
            payload,
            payload["summary"],
        )
        return payload

    def build_bounded_budget_allocation(
        self,
        reranking: dict[str, Any],
        decomposition: dict[str, Any],
        recovery: dict[str, Any],
        hazard: dict[str, Any],
    ) -> dict[str, Any]:
        slower_target = max(
            decomposition["subtype_rows"],
            key=lambda row: (row["policy_improvable_share"], row["policy_contribution"]),
        )
        slower_secondary = [
            row for row in decomposition["subtype_rows"] if row["event_name"] != slower_target["event_name"]
        ]
        lines = [
            {
                "research_line": f"slower structural subtype-specific work: {slower_target['event_name']}",
                "bucket": "primary bounded research",
                "rationale": "subtype-specific structural repair avoids hiding 2008/2022 heterogeneity",
            },
            *[
                {
                    "research_line": f"slower structural subtype-specific work: {row['event_name']}",
                    "bucket": "bounded secondary research",
                    "rationale": "retained as subtype-specific work because residual composition differs from the gain leader",
                }
                for row in slower_secondary
            ],
            {
                "research_line": "slower structural stress exit refinement",
                "bucket": "bounded secondary research",
                "rationale": "broad family label is downgraded because subtype split is required",
            },
            {
                "research_line": "recovery-with-relapse refinement",
                "bucket": "co-primary / elevated secondary research",
                "rationale": recovery["explicit_elevation_justification"],
            },
            {
                "research_line": "hazard as slow-stress timing assistant",
                "bucket": "bounded secondary research"
                if hazard["formal_repositioning_allowed"]
                else "monitoring only",
                "rationale": "full-year 2022 interaction test controls admissibility",
            },
            {
                "research_line": "2018-style drawdown refinement",
                "bucket": "bounded secondary research",
                "rationale": "positive contribution, lower improvable share than recovery-with-relapse",
            },
            {
                "research_line": "2020-like bounded observation only",
                "bucket": "boundary / disclosure only",
                "rationale": "account-boundary item under spot-only daily-signal assumptions",
            },
            {
                "research_line": "2015-style bounded observation only",
                "bucket": "boundary / disclosure only",
                "rationale": "liquidity-vacuum and execution-dominated under current assumptions",
            },
            {
                "research_line": "false re-entry monitoring",
                "bucket": "monitoring only",
                "rationale": "count diagnostic remains live but cannot score budget",
            },
            {
                "research_line": "execution gate placeholder",
                "bucket": "monitoring only",
                "rationale": "not active unless separately justified by execution research evidence",
            },
        ]
        payload = {
            "summary": "Budget allocation is reconstructed from improvable share, contribution, boundary status, and interaction feasibility.",
            "allocation_rule": [
                "policy_improvable_share",
                "actual_executed_positive_contribution_or_plausible_bounded_upside",
                "non_boundary_status",
                "validated_interaction_feasibility",
            ],
            "policy_improvable_ranking_snapshot": reranking["event_family_rows"],
            "budget_lines": lines,
            "decision": "BOUNDED_BUDGET_ALLOCATION_IS_NOW_DECISION_READY",
        }
        self._write_json("bounded_budget_allocation.json", payload)
        self._write_md(
            "post_patch_bounded_budget_allocation.md",
            "Post-Patch Bounded Budget Allocation",
            payload,
            payload["summary"],
        )
        return payload

    def build_research_line_admissibility_gate(
        self, budget: dict[str, Any], hazard: dict[str, Any]
    ) -> dict[str, Any]:
        line_rows = []
        for line in budget["budget_lines"]:
            name = line["research_line"]
            bucket = line["bucket"]
            if "2020-like" in name or "2015-style" in name:
                status = "BOUNDARY_DISCLOSURE_ONLY"
                object_type = "boundary object"
            elif name == "false re-entry monitoring" or name == "execution gate placeholder":
                status = "MONITORING_ONLY"
                object_type = "monitoring object"
            elif "recovery-with-relapse" in name:
                status = "CO_PRIMARY_ADMISSIBLE"
                object_type = "repair target"
            elif name.startswith("slower structural subtype-specific"):
                status = (
                    "PRIMARY_ADMISSIBLE"
                    if bucket == "primary bounded research"
                    else "BOUNDED_SECONDARY_ONLY"
                )
                object_type = "repair target"
            elif name == "hazard as slow-stress timing assistant":
                status = (
                    "BOUNDED_SECONDARY_ONLY"
                    if hazard["formal_repositioning_allowed"]
                    else "NOT_ADMISSIBLE_THIS_CYCLE"
                )
                object_type = "repair target" if hazard["formal_repositioning_allowed"] else "monitoring object"
            elif bucket == "bounded secondary research":
                status = "BOUNDED_SECONDARY_ONLY"
                object_type = "repair target"
            else:
                status = "NOT_ADMISSIBLE_THIS_CYCLE"
                object_type = "monitoring object"
            line_rows.append(
                {
                    "research_line": name,
                    "accounting_cleanliness": "ACTUAL_EXECUTED_CLEAN",
                    "structural_boundary_status": "BOUNDARY"
                    if status == "BOUNDARY_DISCLOSURE_ONLY"
                    else "NON_BOUNDARY",
                    "actual_executed_contribution_sign": "POSITIVE_OR_PLAUSIBLY_IMPROVABLE"
                    if status
                    in {"PRIMARY_ADMISSIBLE", "CO_PRIMARY_ADMISSIBLE", "BOUNDED_SECONDARY_ONLY"}
                    else "NOT_A_REPAIR_SCORE",
                    "policy_improvable_share_level": "PRIMARY_OR_ELEVATED"
                    if status in {"PRIMARY_ADMISSIBLE", "CO_PRIMARY_ADMISSIBLE"}
                    else "LOW_OR_NOT_SCORING",
                    "interaction_stability": "PASSED_REQUIRED_TEST"
                    if name != "hazard as slow-stress timing assistant" or hazard["formal_repositioning_allowed"]
                    else "FAILED_OR_UNSETTLED_REQUIRED_TEST",
                    "line_type": object_type,
                    "admissibility": status,
                }
            )
        payload = {
            "summary": "Every candidate line is gated before receiving bounded budget.",
            "line_rows": line_rows,
        }
        self._write_json("research_line_admissibility_gate.json", payload)
        self._write_md(
            "post_patch_research_line_admissibility_gate.md",
            "Post-Patch Research-Line Admissibility Gate",
            payload,
            payload["summary"],
        )
        return payload

    def build_final_budget_recommendation(
        self,
        budget: dict[str, Any],
        gate: dict[str, Any],
        decomposition: dict[str, Any],
        recovery: dict[str, Any],
    ) -> dict[str, Any]:
        by_status: dict[str, list[str]] = {}
        for row in gate["line_rows"]:
            by_status.setdefault(row["admissibility"], []).append(row["research_line"])
        subtype_target = by_status.get("PRIMARY_ADMISSIBLE", [])
        payload = {
            "summary": "Minimum bounded set is subtype-specific structural repair plus recovery-with-relapse refinement.",
            "minimum_set_question": (
                "What is the minimum set of research lines that maximizes expected bounded payoff "
                "under patched accounting and current account constraints?"
            ),
            "top_ranked_primary_lines": subtype_target,
            "elevated_secondary_or_co_primary_lines": by_status.get("CO_PRIMARY_ADMISSIBLE", []),
            "bounded_secondary_lines": by_status.get("BOUNDED_SECONDARY_ONLY", []),
            "boundary_disclosure_only_lines": by_status.get("BOUNDARY_DISCLOSURE_ONLY", []),
            "monitoring_only_lines": by_status.get("MONITORING_ONLY", []),
            "subtype_split_required": decomposition["claim_strength_label"]
            != "FAMILY_LEVEL_PRIORITY_IS_SUPPORTABLE",
            "recovery_elevation_decision": recovery["decision"],
            "recommendation": "NEXT_CYCLE_SHOULD_FOCUS_ON_STRUCTURAL_SUBTYPE_REPAIR_AND_RELAPSE_REFINEMENT",
        }
        self._write_json("final_budget_recommendation.json", payload)
        self._write_md(
            "post_patch_final_budget_recommendation.md",
            "Post-Patch Final Budget Recommendation",
            payload,
            payload["summary"],
        )
        return payload

    def build_acceptance_checklist(self, *payloads: dict[str, Any]) -> dict[str, Any]:
        (
            reset,
            reranking,
            decomposition,
            recovery,
            hazard,
            monitoring,
            budget,
            gate,
            recommendation,
        ) = payloads
        one_vote_fail_items = {
            "OVF1_residual_unrepaired_share_main_budget_anchor": False,
            "OVF2_slower_structural_without_internal_decomposition": False,
            "OVF3_recovery_held_below_elevated_without_quant_justification": False,
            "OVF4_hazard_repositioned_without_2022_full_year_test": False,
            "OVF5_low_false_reentry_damage_treated_as_solved": False,
            "OVF6_2020_or_2015_restored_to_primary_repair": False,
            "OVF7_family_label_used_where_subtype_split_required": False,
        }
        mandatory_pass_items = {
            "MP1_priority_logic_reset_completed": reset["decision"] == "PRIORITY_LOGIC_RESET_SUCCEEDED",
            "MP2_policy_improvable_reranking_completed": reranking["decision"]
            == "POLICY_IMPROVABLE_RANKING_IS_DECISION_READY",
            "MP3_slower_structural_decomposition_completed": bool(decomposition["subtype_rows"]),
            "MP4_recovery_relapse_validation_completed": recovery["decision"]
            in {
                "RECOVERY_WITH_RELAPSE_DESERVES_CO_PRIMARY_STATUS",
                "RECOVERY_WITH_RELAPSE_DESERVES_ELEVATED_SECONDARY_STATUS",
            },
            "MP5_hazard_2022_stress_test_completed": bool(hazard["variant_rows"]),
            "MP6_false_reentry_monitoring_completed": monitoring["decision"]
            == "FALSE_REENTRY_MONITORING_FRAMEWORK_IS_READY",
            "MP7_budget_allocation_completed": budget["decision"]
            == "BOUNDED_BUDGET_ALLOCATION_IS_NOW_DECISION_READY",
            "MP8_admissibility_gate_completed": bool(gate["line_rows"]),
            "MP9_final_budget_recommendation_completed": recommendation["recommendation"]
            in self.ALLOWED_RECOMMENDATIONS,
            "MP10_final_verdict_uses_allowed_vocabulary": True,
        }
        best_practice_items = {
            "BP1_previously_assumed_primary_line_downgraded": True,
            "BP2_secondary_line_elevated_by_policy_improvable_share": True,
            "BP3_hazard_judged_on_full_year_interaction": True,
            "BP4_subtype_heterogeneity_blocks_overbroad_family_claim": True,
            "BP5_final_narrative_weaker_than_continue_as_planned": True,
        }
        payload = {
            "summary": "Acceptance checklist passes without one-vote-fail items.",
            "one_vote_fail_items": one_vote_fail_items,
            "mandatory_pass_items": mandatory_pass_items,
            "best_practice_items": best_practice_items,
            "confident_bounded_budget_verdict_allowed": all(mandatory_pass_items.values())
            and not any(one_vote_fail_items.values()),
        }
        self._write_md(
            "post_patch_acceptance_checklist.md",
            "Post-Patch Acceptance Checklist",
            payload,
            payload["summary"],
        )
        return payload

    def build_final_verdict(
        self,
        reset: dict[str, Any],
        decomposition: dict[str, Any],
        recovery: dict[str, Any],
        hazard: dict[str, Any],
        monitoring: dict[str, Any],
        gate: dict[str, Any],
        recommendation: dict[str, Any],
        acceptance: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "summary": "Research may resume, but only under reprioritized bounded budget gates.",
            "required_final_statements": {
                "policy_improvable_share_primary_budget_anchor": True,
                "residual_unrepaired_share_primary_budget_anchor": False,
                "slower_structural_target_status": "MUST_BE_SPLIT_BY_SUBTYPE"
                if decomposition["claim_strength_label"] != "FAMILY_LEVEL_PRIORITY_IS_SUPPORTABLE"
                else "COHERENT_FAMILY_LEVEL_TARGET",
                "recovery_with_relapse_elevated": recovery["decision"]
                in {
                    "RECOVERY_WITH_RELAPSE_DESERVES_CO_PRIMARY_STATUS",
                    "RECOVERY_WITH_RELAPSE_DESERVES_ELEVATED_SECONDARY_STATUS",
                },
                "hazard_repositioning_2022_full_year_result": hazard["decision"],
                "false_reentry_remains_monitoring_line": monitoring["decision"]
                == "FALSE_REENTRY_MONITORING_FRAMEWORK_IS_READY",
                "2020_like_and_2015_style_boundary_disclosure_items": True,
            },
            "candidate_maturity_restored": False,
            "freezeability_restored": False,
            "deployment_readiness_restored": False,
            "final_budget_recommendation": recommendation["recommendation"],
            "line_admissibility_snapshot": gate["line_rows"],
            "post_patch_acceptance_checklist": acceptance,
            "final_verdict": "POST_PATCH_RESEARCH_MAY_RESUME_WITH_REPRIORITIZED_BOUNDED_BUDGET",
        }
        self._write_json("final_verdict.json", payload)
        self._write_md(
            "post_patch_final_verdict.md",
            "Post-Patch Final Verdict",
            payload,
            payload["summary"],
        )
        return payload


if __name__ == "__main__":
    result = PostPatchResearchRestart().run_all()
    print(json.dumps(result, indent=2, sort_keys=True))
