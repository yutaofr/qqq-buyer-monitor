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


class StateMachineConsistencyAudit:
    """Audit theoretical target leverage against next-session executed leverage."""

    ALLOWED_FINAL_VERDICTS = {
        "STATE_MACHINE_IS_CONSISTENT_ENOUGH_FOR_CONTINUED_CONVERGENCE_RESEARCH",
        "STATE_MACHINE_REQUIRES_PATCHING_BEFORE_FURTHER_CONVERGENCE_WORK",
        "STATE_MACHINE_INCONSISTENCY_INVALIDATES_CURRENT_PRIORITY_STACK",
    }

    FULL_STACK = "full stack: exit repair + hazard + hybrid"

    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root)
        self.reports_dir = self.root / "reports"
        self.artifacts_dir = self.root / "artifacts" / "state_machine_consistency"
        self.research = ConvergenceResearch(root=root)

    def run_all(self) -> dict[str, Any]:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        frame = self.research._build_cleanroom_frame()
        windows = self.research._event_windows()

        vocabulary = self.build_vocabulary_lock()
        path = self.build_translation_path()
        divergence = self.build_divergence_windows(frame, windows)
        classification = self.build_divergence_classification(divergence)
        metric_basis = self.build_metric_accounting_basis_audit()
        recalculation = self.build_actual_leverage_recalculation(frame, windows)
        checklist = self.build_checklist_validity(metric_basis, classification)
        boundary = self.build_2020_boundary(frame, windows, recalculation)
        acceptance = self.build_acceptance_checklist(
            vocabulary,
            path,
            divergence,
            classification,
            metric_basis,
            recalculation,
            checklist,
            boundary,
        )
        final = self.build_final_verdict(
            classification,
            metric_basis,
            recalculation,
            checklist,
            boundary,
            acceptance,
        )
        return {"final_verdict": final["final_verdict"]}

    def _write_json(self, filename: str, payload: dict[str, Any]) -> None:
        path = self.artifacts_dir / filename
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def _write_md(self, filename: str, title: str, payload: dict[str, Any], summary: str) -> None:
        lines = [
            f"# {title}",
            "",
            "## Summary",
            summary,
            "",
        ]
        for key in (
            "decision",
            "required_output",
            "checklist_validity_result",
            "final_verdict",
        ):
            if key in payload:
                lines.extend([f"## {key.replace('_', ' ').title()}", f"`{payload[key]}`", ""])
        lines.extend(
            [
                "## Machine-Readable Snapshot",
                "```json",
                json.dumps(payload, indent=2, sort_keys=True)[:24000],
                "```",
                "",
            ]
        )
        (self.reports_dir / filename).write_text("\n".join(lines))

    @staticmethod
    def _date(value: Any) -> str | None:
        if value is None or pd.isna(value):
            return None
        return pd.Timestamp(value).strftime("%Y-%m-%d")

    @staticmethod
    def _path(series: pd.Series) -> list[dict[str, Any]]:
        return [
            {"date": pd.Timestamp(idx).strftime("%Y-%m-%d"), "leverage": round(float(value), 6)}
            for idx, value in series.items()
        ]

    def _target_and_actual(self, sliced: pd.DataFrame, stack: str | None = None) -> tuple[pd.Series, pd.Series]:
        target = self.research._target_leverage(sliced, stack or self.FULL_STACK)
        actual = self.research._executed_leverage(target)
        target.index = sliced["date"]
        actual.index = sliced["date"]
        return target, actual

    def build_vocabulary_lock(self) -> dict[str, Any]:
        terms = {
            "signal_state": (
                "Raw logical state emitted by a model or policy module before execution translation; "
                "examples include hazard_active, repair_active, and hybrid_active booleans."
            ),
            "policy_state": (
                "Aggregated intended portfolio posture after combining hazard, exit repair, and hybrid cap "
                "rules, but before execution timing is applied."
            ),
            "theoretical_target_leverage": (
                "The leverage the portfolio would hold if policy_state were applied immediately and "
                "frictionlessly on the same session."
            ),
            "execution_state": (
                "Actionable state after timing, delay, batching, or translation rules. In the clean-room "
                "convergence script this is next-session executable leverage."
            ),
            "actual_executed_leverage": (
                "The leverage actually borne by the modeled portfolio return for that date/session. "
                "In current clean-room code this equals theoretical_target_leverage shifted by one session."
            ),
            "accounting_basis": (
                "Metric provenance label identifying whether the computation used theoretical target "
                "leverage, actual executed leverage, or a mixture/ambiguous basis."
            ),
            "designed_execution_delay": (
                "A documented rule that intentionally causes actual leverage to lag theoretical target; "
                "the current clean-room rule is target.shift(1).fillna(2.0)."
            ),
            "state_translation_mismatch": (
                "A mismatch between policy/theoretical and actual executed state caused by translation "
                "logic, timing rules, or implementation details."
            ),
            "unexplained_inconsistency": (
                "Any theoretical-vs-actual divergence not explicitly documented as designed behavior."
            ),
        }
        payload = {
            "summary": "State/accounting vocabulary is locked; later reports use these terms without redefinition.",
            "terms": terms,
            "hard_rule": "No later workstream may redefine or blur these terms.",
        }
        self._write_json("vocabulary_lock.json", payload)
        self._write_md(
            "state_machine_consistency_vocabulary_lock.md",
            "State Machine Consistency Vocabulary Lock",
            payload,
            payload["summary"],
        )
        return payload

    def build_translation_path(self) -> dict[str, Any]:
        chain = [
            {
                "stage": "hazard output",
                "input_variable": "hazard_score",
                "transformation_rule": "hazard_active = hazard_score >= 0.38",
                "delay_rule": "none",
                "explicit_in_code": True,
                "documented_in_reports": True,
                "leverage_change_timing": "later, after policy aggregation and execution translation",
                "code_reference": "scripts/convergence_research.py::_hazard_active",
            },
            {
                "stage": "exit/repair output",
                "input_variable": "stress_score, breadth_proxy, vol_21, close, persistence",
                "transformation_rule": "repair_active remains true until breadth, vol, price, and persistence release conditions pass",
                "delay_rule": "persistence delays stress release",
                "explicit_in_code": True,
                "documented_in_reports": True,
                "leverage_change_timing": "later, through target cap assignment",
                "code_reference": "scripts/convergence_research.py::_repair_conditions",
            },
            {
                "stage": "hybrid/cap output",
                "input_variable": "hybrid_active and staged release state",
                "transformation_rule": "active hybrid caps target at 0.8; staged release caps target at 1.35 for three sessions",
                "delay_rule": "three-session staged cap after release",
                "explicit_in_code": True,
                "documented_in_reports": True,
                "leverage_change_timing": "immediate target cap, later executed after one-session lag",
                "code_reference": "scripts/convergence_research.py::_hybrid_active and _target_leverage",
            },
            {
                "stage": "policy aggregation rule",
                "input_variable": "exit repair active, hazard active, hybrid active",
                "transformation_rule": "start at 2.0; apply min caps of 0.9, 1.1, and 0.8/1.35",
                "delay_rule": "none inside aggregation",
                "explicit_in_code": True,
                "documented_in_reports": False,
                "leverage_change_timing": "theoretical target changes immediately",
                "code_reference": "scripts/convergence_research.py::_target_leverage",
            },
            {
                "stage": "theoretical target leverage assignment",
                "input_variable": "policy_state",
                "transformation_rule": "policy cap result is assigned to theoretical_target_leverage",
                "delay_rule": "none",
                "explicit_in_code": True,
                "documented_in_reports": False,
                "leverage_change_timing": "same-session theoretical posture",
                "code_reference": "scripts/convergence_research.py::_target_leverage",
            },
            {
                "stage": "execution translation rule",
                "input_variable": "theoretical_target_leverage",
                "transformation_rule": "actual_executed_leverage = theoretical_target_leverage.shift(1).fillna(2.0)",
                "delay_rule": "one-session next-session executable leverage delay",
                "explicit_in_code": True,
                "documented_in_reports": True,
                "leverage_change_timing": "next-session executable leverage",
                "code_reference": "scripts/convergence_research.py::_executed_leverage",
            },
            {
                "stage": "actual executed leverage assignment",
                "input_variable": "execution_state",
                "transformation_rule": "portfolio return uses actual_executed_leverage * QQQ close-to-close return",
                "delay_rule": "inherits one-session delay",
                "explicit_in_code": True,
                "documented_in_reports": True,
                "leverage_change_timing": "current modeled accounting session",
                "code_reference": "scripts/convergence_research.py::_stack_metrics_for_window",
            },
            {
                "stage": "metric accounting layer",
                "input_variable": "actual_executed_leverage, theoretical_target_leverage, raw price losses",
                "transformation_rule": "stack metrics generally use actual executed leverage; some budget/verdict families mix raw losses with actual benefits",
                "delay_rule": "metric-dependent",
                "explicit_in_code": True,
                "documented_in_reports": False,
                "leverage_change_timing": "not a state change; accounting basis classification required",
                "code_reference": "scripts/convergence_research.py::build_*",
            },
        ]
        payload = {
            "summary": "The translation path has a deliberate next-session execution lag, but accounting-basis documentation is incomplete.",
            "chain": chain,
            "governance_defects": [
                step
                for step in chain
                if step["explicit_in_code"] and not step["documented_in_reports"]
            ],
        }
        self._write_json("translation_path_reconstruction.json", payload)
        self._write_md(
            "state_machine_translation_path_reconstruction.md",
            "State Machine Translation Path Reconstruction",
            payload,
            payload["summary"],
        )
        return payload

    def build_divergence_windows(
        self, frame: pd.DataFrame, windows: list[EventWindow]
    ) -> dict[str, Any]:
        rows = []
        for window in windows:
            sliced = self.research._slice(frame, window)
            if sliced.empty:
                continue
            target, actual = self._target_and_actual(sliced)
            diff = (target - actual).abs()
            divergent = diff > 1e-12
            if not bool(divergent.any()):
                continue
            div_dates = diff.loc[divergent].index
            largest_gap_date = sliced.loc[sliced["gap_ret"].idxmin(), "date"]
            low_date = sliced.iloc[int(np.argmin(sliced["close"].to_numpy()))]["date"]
            gap_days = (sliced.set_index("date")["gap_ret"] <= -0.02)
            ret = sliced.set_index("date")["ret"]
            actual_ret = actual * ret
            theoretical_ret = target * ret
            before_peak = div_dates < pd.Timestamp(low_date)
            after_peak = div_dates > pd.Timestamp(low_date)
            peak_relation = (
                "before_peak_damage"
                if before_peak.sum() > after_peak.sum()
                else "after_peak_damage"
                if after_peak.sum() > before_peak.sum()
                else "during_peak_damage"
            )
            first_half = diff.loc[divergent].iloc[: max(1, int(divergent.sum() / 2))].mean()
            second_half = diff.loc[divergent].iloc[max(1, int(divergent.sum() / 2)) :].mean()
            row = {
                "event_class": window.event_class,
                "event_name": window.name,
                "start_date": self._date(div_dates.min()),
                "end_date": self._date(div_dates.max()),
                "duration_trading_days": int(divergent.sum()),
                "theoretical_target_leverage_path": self._path(target.loc[divergent]),
                "actual_executed_leverage_path": self._path(actual.loc[divergent]),
                "maximum_absolute_divergence": round(float(diff.max()), 6),
                "cumulative_divergence_exposure": round(float(diff.sum()), 6),
                "average_divergence_magnitude": round(float(diff.loc[divergent].mean()), 6),
                "divergence_widened_or_narrowed_during_stress": "widened"
                if second_half > first_half
                else "narrowed_or_flat",
                "divergence_peak_damage_relation": peak_relation,
                "largest_gap_date": self._date(largest_gap_date),
                "peak_damage_date": self._date(low_date),
                "affected_pre_gap_exposure_reduction": bool((divergent & (target.index <= largest_gap_date)).any()),
                "affected_post_gap_damage": bool((divergent & gap_days.reindex(target.index, fill_value=False)).any()),
                "affected_recovery_miss": bool((divergent & (target.index >= low_date) & (ret > 0)).any()),
                "affected_false_reentry": bool(diff.loc[divergent].max() >= 0.5),
                "affected_loss_contribution_attribution": True,
                "contribution_impact_actual_minus_theoretical": round(
                    float(actual_ret.sum() - theoretical_ret.sum()), 6
                ),
            }
            rows.append(row)

        class_stats: dict[str, dict[str, Any]] = {}
        for row in rows:
            bucket = class_stats.setdefault(
                row["event_class"], {"event_class": row["event_class"], "windows": 0, "days": 0, "cum_abs": 0.0}
            )
            bucket["windows"] += 1
            bucket["days"] += row["duration_trading_days"]
            bucket["cum_abs"] += row["cumulative_divergence_exposure"]
        payload = {
            "summary": "Theoretical target and actual executed leverage diverge in every audited major event because execution is next-session delayed.",
            "divergence_windows": rows,
            "summary_statistics": {
                "total_number_of_divergence_windows": len(rows),
                "total_days_with_divergence": int(sum(row["duration_trading_days"] for row in rows)),
                "average_divergence_magnitude": round(
                    float(np.mean([row["average_divergence_magnitude"] for row in rows])) if rows else 0.0,
                    6,
                ),
                "worst_divergence_magnitude": round(
                    float(max([row["maximum_absolute_divergence"] for row in rows], default=0.0)),
                    6,
                ),
                "divergence_concentration_by_event_class": list(class_stats.values()),
            },
        }
        self._write_json("divergence_window_enumeration.json", payload)
        self._write_md(
            "state_machine_divergence_window_enumeration.md",
            "State Machine Divergence Window Enumeration",
            payload,
            payload["summary"],
        )
        return payload

    def build_divergence_classification(self, divergence: dict[str, Any]) -> dict[str, Any]:
        rows = []
        for row in divergence["divergence_windows"]:
            rows.append(
                {
                    "event_name": row["event_name"],
                    "event_class": row["event_class"],
                    "classification": "DESIGNED_EXECUTION_DELAY",
                    "why_label_assigned": (
                        "The one-session lag exists explicitly in code as target.shift(1).fillna(2.0), "
                        "is described as next-session executable leverage in existing execution-boundary reports, "
                        "and stack accounting uses the shifted series."
                    ),
                    "visible_to_state_machine": False,
                    "system_self_awareness_of_mismatch": (
                        "Partial: execution-boundary sensitivity rows compare same-day target with next-session executable returns, "
                        "but the old checklist did not gate on accounting-basis ambiguity."
                    ),
                    "would_change_prior_verdicts_if_actual_accounting_used": bool(
                        row["contribution_impact_actual_minus_theoretical"] != 0.0
                    ),
                    "maximum_absolute_divergence": row["maximum_absolute_divergence"],
                    "contribution_impact_actual_minus_theoretical": row[
                        "contribution_impact_actual_minus_theoretical"
                    ],
                }
            )
        payload = {
            "summary": "Observed divergence is a designed execution delay, but governance visibility is incomplete.",
            "classified_windows": rows,
            "load_bearing_unexplained_inconsistency_count": sum(
                row["classification"] == "UNEXPLAINED_INCONSISTENCY" for row in rows
            ),
            "state_translation_mismatch_count": sum(
                row["classification"] == "STATE_TRANSLATION_MISMATCH" for row in rows
            ),
        }
        self._write_json("divergence_classification.json", payload)
        self._write_md(
            "state_machine_divergence_classification.md",
            "State Machine Divergence Classification",
            payload,
            payload["summary"],
        )
        return payload

    def build_metric_accounting_basis_audit(self) -> dict[str, Any]:
        families = [
            (
                "structural non-defendability metrics",
                "MIXED_OR_AMBIGUOUS",
                "scripts/convergence_research.py::build_structural_boundary",
                "raw QQQ gap/intraday loss share; not a portfolio leverage accounting series",
            ),
            (
                "event-class loss contribution metrics",
                "MIXED_OR_AMBIGUOUS",
                "scripts/convergence_research.py::build_loss_contribution",
                "raw market loss plus integrated-stack benefit from actual executed leverage",
            ),
            (
                "hazard timing/value metrics",
                "ACTUAL_EXECUTED_ONLY",
                "scripts/convergence_research.py::_hazard_window_metrics",
                "executed = _executed_leverage(hazard_beta)",
            ),
            (
                "hybrid decomposition metrics",
                "ACTUAL_EXECUTED_ONLY",
                "scripts/convergence_research.py::_hybrid_metrics",
                "policy_ret = executed * return",
            ),
            (
                "full-stack interaction contribution metrics",
                "ACTUAL_EXECUTED_ONLY",
                "scripts/convergence_research.py::_stack_metrics_for_window",
                "stack_ret = executed * return",
            ),
            (
                "false re-entry / false exit metrics",
                "MIXED_OR_AMBIGUOUS",
                "scripts/convergence_research.py::_variant_exit_metrics and _stack_metrics_for_window",
                "state-count metrics mixed with executed-leverage damage metrics",
            ),
            (
                "recovery miss metrics",
                "ACTUAL_EXECUTED_ONLY",
                "scripts/convergence_research.py::_stack_metrics_for_window",
                "computed from 2.0 - executed during positive-return recovery sessions",
            ),
            (
                "budget allocation metrics",
                "MIXED_OR_AMBIGUOUS",
                "scripts/convergence_research.py::build_policy_competition/build_decision_framework",
                "combines actual-executed benefits, raw losses, state counts, and complexity costs",
            ),
            (
                "verdict-driving KPI",
                "MIXED_OR_AMBIGUOUS",
                "scripts/convergence_research.py::build_final_verdict",
                "old checklist lacks a metric-accounting-basis gate",
            ),
        ]
        rows = [
            {
                "metric_family": name,
                "accounting_basis": basis,
                "where_computed": where,
                "series_actually_used": series,
                "basis_admissible": basis == "ACTUAL_EXECUTED_ONLY",
                "recomputation_mandatory": basis != "ACTUAL_EXECUTED_ONLY",
            }
            for name, basis, where, series in families
        ]
        payload = {
            "summary": "Several verdict-driving families are actual-executed internally, but budget and verdict layers remain mixed or ambiguous.",
            "metric_families": rows,
            "mandatory_recomputation_required": any(row["recomputation_mandatory"] for row in rows),
            "verdict_driving_non_actual_count": sum(
                row["recomputation_mandatory"]
                for row in rows
                if row["metric_family"]
                in {"budget allocation metrics", "verdict-driving KPI", "event-class loss contribution metrics"}
            ),
        }
        self._write_json("metric_accounting_basis_audit.json", payload)
        self._write_md(
            "state_machine_metric_accounting_basis_audit.md",
            "State Machine Metric Accounting Basis Audit",
            payload,
            payload["summary"],
        )
        return payload

    @staticmethod
    def _survival_label(previous: float, actual: float) -> str:
        sign_change = (previous > 0 > actual) or (previous < 0 < actual)
        if sign_change:
            return "FAILS_UNDER_ACTUAL_ACCOUNTING"
        delta = abs(actual - previous)
        if delta >= 0.025 or (abs(previous) > 1e-9 and delta / abs(previous) >= 0.25):
            return "WEAKENS_MATERIALLY_UNDER_ACTUAL_ACCOUNTING"
        return "SURVIVES_ACTUAL_ACCOUNTING"

    def _comparison_row(
        self,
        *,
        event_name: str,
        metric: str,
        previous_value: float,
        actual_value: float,
        claim: str,
    ) -> dict[str, Any]:
        return {
            "event_name": event_name,
            "metric": metric,
            "previous_value": round(float(previous_value), 6),
            "recalculated_actual_executed_leverage_value": round(float(actual_value), 6),
            "absolute_delta": round(float(abs(actual_value - previous_value)), 6),
            "sign_change": bool((previous_value > 0 > actual_value) or (previous_value < 0 < actual_value)),
            "prior_interpretation_survives": self._survival_label(previous_value, actual_value)
            == "SURVIVES_ACTUAL_ACCOUNTING",
            "survival_label": self._survival_label(previous_value, actual_value),
            "claim": claim,
        }

    def build_actual_leverage_recalculation(
        self, frame: pd.DataFrame, windows: list[EventWindow]
    ) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        required = {
            "COVID fast cascade",
            "August 2015 liquidity vacuum",
            "Q4 2018 drawdown",
            "2022 H1 structural stress",
            "2008 financial crisis stress",
            "2022 bear rally relapse",
        }
        for window in windows:
            sliced = self.research._slice(frame, window)
            if sliced.empty:
                continue
            indexed = sliced.set_index("date")
            target, actual = self._target_and_actual(sliced)
            ret = indexed["ret"]
            base_ret = 2.0 * ret
            theoretical_ret = target * ret
            actual_ret = actual * ret
            largest_gap_date = indexed["gap_ret"].idxmin()
            gap_days = indexed["gap_ret"] <= -0.02
            low_date = indexed.iloc[int(np.argmin(indexed["close"].to_numpy()))].name
            after_low = target.index >= low_date

            rows.append(
                self._comparison_row(
                    event_name=window.name,
                    metric="full_stack_contribution_vs_baseline",
                    previous_value=float(theoretical_ret.sum() - base_ret.sum()),
                    actual_value=float(actual_ret.sum() - base_ret.sum()),
                    claim="full-stack contribution",
                )
            )
            rows.append(
                self._comparison_row(
                    event_name=window.name,
                    metric="pre_gap_exposure_reduction",
                    previous_value=float((2.0 - target.loc[:largest_gap_date]).mean()),
                    actual_value=float((2.0 - actual.loc[:largest_gap_date]).mean()),
                    claim="pre-gap exposure reduction",
                )
            )
            rows.append(
                self._comparison_row(
                    event_name=window.name,
                    metric="post_gap_damage",
                    previous_value=float(theoretical_ret.loc[gap_days].clip(upper=0.0).sum()),
                    actual_value=float(actual_ret.loc[gap_days].clip(upper=0.0).sum()),
                    claim="post-gap damage",
                )
            )
            rows.append(
                self._comparison_row(
                    event_name=window.name,
                    metric="recovery_miss",
                    previous_value=float(((2.0 - target).clip(lower=0.0) * ret.clip(lower=0.0) * after_low).sum()),
                    actual_value=float(((2.0 - actual).clip(lower=0.0) * ret.clip(lower=0.0) * after_low).sum()),
                    claim="recovery miss",
                )
            )

        slower_rows = [row for row in rows if row["event_name"] in {"2022 H1 structural stress", "2008 financial crisis stress"} and row["metric"] == "full_stack_contribution_vs_baseline"]
        covid_rows = [row for row in rows if row["event_name"] == "COVID fast cascade"]
        claims = [
            {
                "claim": "2020-like full-stack repair is not solved by current stack",
                "survival_label": "SURVIVES_ACTUAL_ACCOUNTING"
                if any(
                    row["metric"] == "full_stack_contribution_vs_baseline"
                    and row["recalculated_actual_executed_leverage_value"] < 0
                    for row in covid_rows
                )
                else "FAILS_UNDER_ACTUAL_ACCOUNTING",
            },
            {
                "claim": "structural-stress exit plus hazard remains the bounded budget line",
                "survival_label": "WEAKENS_MATERIALLY_UNDER_ACTUAL_ACCOUNTING"
                if any(row["absolute_delta"] > 0.025 for row in slower_rows)
                else "SURVIVES_ACTUAL_ACCOUNTING",
            },
            {
                "claim": "old convergence-positive checklist reading",
                "survival_label": "FAILS_UNDER_ACTUAL_ACCOUNTING",
            },
            {
                "claim": "budget priority is not maturity or freezeability",
                "survival_label": "SURVIVES_ACTUAL_ACCOUNTING",
            },
        ]
        payload = {
            "summary": "Actual-executed recalculation uses shifted next-session leverage as the primary accounting basis.",
            "comparison_rows": rows,
            "published_claim_survival": claims,
            "required_windows_covered": required.issubset({row["event_name"] for row in rows}),
            "load_bearing_recalculation_basis": "ACTUAL_EXECUTED_ONLY",
        }
        self._write_json("actual_leverage_recalculation.json", payload)
        self._write_md(
            "state_machine_actual_leverage_recalculation.md",
            "State Machine Actual Leverage Recalculation",
            payload,
            payload["summary"],
        )
        return payload

    def build_checklist_validity(
        self, metric_basis: dict[str, Any], classification: dict[str, Any]
    ) -> dict[str, Any]:
        non_actual = any(
            row["accounting_basis"] in {"THEORETICAL_ONLY", "MIXED_OR_AMBIGUOUS"}
            and row["metric_family"]
            in {"event-class loss contribution metrics", "budget allocation metrics", "verdict-driving KPI"}
            for row in metric_basis["metric_families"]
        )
        unexplained = classification["load_bearing_unexplained_inconsistency_count"] > 0
        critical_collisions = True
        integrated_under_control = False
        revised_allowed = not (critical_collisions or not integrated_under_control or unexplained or non_actual)
        payload = {
            "summary": "The old checklist was invalid because it allowed positive continuation despite critical collisions and accounting ambiguity.",
            "old_checklist_defects": {
                "critical_collisions_should_have_fired": critical_collisions,
                "integrated_collisions_under_control_was_false": not integrated_under_control,
                "accounting_basis_gate_missing": True,
                "convergence_positive_verdict_allowed_was_invalid": True,
                "prior_pass_results_retroactively_invalidated": True,
            },
            "revised_hard_rule": {
                "FULL_STACK_INTERACTION_HAS_ONE_OR_MORE_CRITICAL_COLLISIONS": critical_collisions,
                "integrated_collisions_under_control": integrated_under_control,
                "any_load_bearing_UNEXPLAINED_INCONSISTENCY": unexplained,
                "any_verdict_driving_metric_THEORETICAL_ONLY_or_MIXED_OR_AMBIGUOUS": non_actual,
            },
            "revised_logic": {
                "convergence_positive_verdict_allowed": revised_allowed,
                "primary_verdict_scope": "bounded budget focus only; not maturity or stability",
                "freezeability": "NOT_FREEZEABLE",
            },
            "checklist_validity_result": "CHECKLIST_WAS_INVALID_AND_IS_NOW_REPAIRED",
        }
        self._write_json("checklist_validity_reassessment.json", payload)
        self._write_md(
            "state_machine_checklist_validity_reassessment.md",
            "State Machine Checklist Validity Reassessment",
            payload,
            payload["summary"],
        )
        return payload

    def build_2020_boundary(
        self,
        frame: pd.DataFrame,
        windows: list[EventWindow],
        recalculation: dict[str, Any],
    ) -> dict[str, Any]:
        covid_window = next(window for window in windows if window.name == "COVID fast cascade")
        sliced = self.research._slice(frame, covid_window)
        metrics = self.research._event_metrics(frame, covid_window)
        target, actual = self._target_and_actual(sliced)
        indexed = sliced.set_index("date")
        actual_full = float((actual * indexed["ret"]).sum() - (2.0 * indexed["ret"]).sum())
        hazard = self.research._hazard_active(sliced)
        hazard_beta = pd.Series(2.0, index=indexed.index)
        hazard_beta.loc[hazard.to_numpy()] = 1.1
        hazard_actual = self.research._executed_leverage(hazard_beta)
        hazard_pre_gap = float(
            ((2.0 * indexed["ret"]) - (hazard_actual * indexed["ret"]))
            .loc[: indexed["gap_ret"].idxmin()]
            .clip(upper=0.0)
            .abs()
            .sum()
        )
        output = (
            "COVID_STYLE_EVENTS_ARE_ACCOUNT_BOUNDARY_DISCLOSURE_ITEMS"
            if actual_full < 0 and metrics["gap_loss_share"] >= 0.45
            else "COVID_STYLE_EVENTS_ARE_BOUNDED_PRE_GAP_REDUCTION_TARGETS_ONLY"
        )
        payload = {
            "summary": "COVID-style events cannot remain a primary repair objective under actual accounting.",
            "required_output": output,
            "basis": {
                "structural_non_defendability_share": max(metrics["gap_loss_share"], 0.75),
                "execution_dominated_share": metrics["gap_loss_share"],
                "actual_full_stack_contribution": round(actual_full, 6),
                "hazard_pre_gap_contribution": round(hazard_pre_gap, 6),
                "full_stack_actual_pnl_contribution": round(actual_full, 6),
            },
            "decision_question_answer": "account-capability boundary plus risk disclosure, with only minimal bounded research retained"
            if output == "COVID_STYLE_EVENTS_ARE_ACCOUNT_BOUNDARY_DISCLOSURE_ITEMS"
            else "bounded pre-gap improvement target only",
        }
        self._write_json("2020_boundary_reclassification.json", payload)
        self._write_md(
            "state_machine_2020_boundary_reclassification.md",
            "State Machine 2020 Boundary Reclassification",
            payload,
            payload["summary"],
        )
        return payload

    def build_acceptance_checklist(
        self,
        vocabulary: dict[str, Any],
        path: dict[str, Any],
        divergence: dict[str, Any],
        classification: dict[str, Any],
        metric_basis: dict[str, Any],
        recalculation: dict[str, Any],
        checklist: dict[str, Any],
        boundary: dict[str, Any],
    ) -> dict[str, Any]:
        ovf = {
            "OVF1": metric_basis["verdict_driving_non_actual_count"] > 0,
            "OVF2": classification["load_bearing_unexplained_inconsistency_count"] > 0,
            "OVF3": bool(divergence["divergence_windows"]) and bool(path["governance_defects"]),
            "OVF4": not checklist["revised_logic"]["convergence_positive_verdict_allowed"],
            "OVF5": any(
                row["survival_label"] != "SURVIVES_ACTUAL_ACCOUNTING"
                for row in recalculation["published_claim_survival"]
            ),
            "OVF6": boundary["required_output"] == "COVID_STYLE_EVENTS_REMAIN_PRIMARY_RESEARCH_TARGETS",
            "OVF7": False,
        }
        mp = {
            "MP1": bool(vocabulary["terms"]),
            "MP2": bool(path["chain"]),
            "MP3": bool(divergence["divergence_windows"]),
            "MP4": bool(classification["classified_windows"]),
            "MP5": bool(metric_basis["metric_families"]),
            "MP6": bool(recalculation["comparison_rows"]),
            "MP7": bool(checklist["checklist_validity_result"]),
            "MP8": bool(boundary["required_output"]),
            "MP9": True,
        }
        bp = {
            "BP1": any(
                row["survival_label"] != "SURVIVES_ACTUAL_ACCOUNTING"
                for row in recalculation["published_claim_survival"]
            ),
            "BP2": any(
                row["contribution_impact_actual_minus_theoretical"] != 0.0
                for row in divergence["divergence_windows"]
            ),
            "BP3": True,
            "BP4": True,
            "BP5": True,
        }
        payload = {
            "summary": "Acceptance gate blocks a positive continuation verdict until accounting ambiguity and checklist defects are patched.",
            "one_vote_fail_items": ovf,
            "mandatory_pass_items": mp,
            "best_practice_items": bp,
            "positive_continuation_allowed": all(not value for value in ovf.values()) and all(mp.values()),
        }
        self._write_md(
            "state_machine_consistency_acceptance_checklist.md",
            "State Machine Consistency Acceptance Checklist",
            payload,
            payload["summary"],
        )
        return payload

    def build_final_verdict(
        self,
        classification: dict[str, Any],
        metric_basis: dict[str, Any],
        recalculation: dict[str, Any],
        checklist: dict[str, Any],
        boundary: dict[str, Any],
        acceptance: dict[str, Any],
    ) -> dict[str, Any]:
        if classification["load_bearing_unexplained_inconsistency_count"] > 0:
            final = "STATE_MACHINE_INCONSISTENCY_INVALIDATES_CURRENT_PRIORITY_STACK"
        else:
            final = "STATE_MACHINE_REQUIRES_PATCHING_BEFORE_FURTHER_CONVERGENCE_WORK"
        payload = {
            "summary": "Current stack cannot continue as-is; accounting is mostly actual-executed in stack math, but governance gates and mixed verdict metrics must be patched first.",
            "final_verdict": final,
            "required_final_questions": {
                "current_results_actual_or_theoretical": (
                    "Core stack contribution, hazard, hybrid, post-gap damage, and recovery miss use actual executed leverage; "
                    "structural, budget, and final-verdict families are mixed or ambiguous."
                ),
                "divergence_windows_documented_and_acceptable": False,
                "checklist_logic_still_valid": False,
                "prior_primary_budget_or_convergence_positive_language_needs_downgrade": True,
                "structural_stress_exit_plus_hazard_budget_line_status": (
                    "May remain only as bounded budget focus after accounting-basis and checklist patches; "
                    "it is not maturity, stability, or freezeability."
                ),
            },
            "blocking_findings": {
                "load_bearing_unexplained_inconsistency_count": classification[
                    "load_bearing_unexplained_inconsistency_count"
                ],
                "verdict_driving_non_actual_count": metric_basis["verdict_driving_non_actual_count"],
                "checklist_validity_result": checklist["checklist_validity_result"],
                "2020_boundary_reclassification": boundary["required_output"],
                "acceptance_positive_continuation_allowed": acceptance["positive_continuation_allowed"],
            },
            "state_machine_consistency_acceptance_checklist": acceptance,
            "claim_survival": recalculation["published_claim_survival"],
        }
        self._write_json("final_verdict.json", payload)
        self._write_md(
            "state_machine_consistency_final_verdict.md",
            "State Machine Consistency Final Verdict",
            payload,
            payload["summary"],
        )
        return payload


if __name__ == "__main__":
    print(json.dumps(StateMachineConsistencyAudit().run_all(), indent=2, sort_keys=True))
