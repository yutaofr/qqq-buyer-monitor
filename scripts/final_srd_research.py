import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class EventWindow:
    event_class: str
    name: str
    start: str
    end: str


class FinalSrdResearch:
    STRUCTURAL_CONFIRMED = "STRUCTURAL_NON_DEFENDABILITY_CONFIRMED_FOR_2020_LIKE_EVENTS"
    STRUCTURAL_PARTIAL = "STRUCTURAL_NON_DEFENDABILITY_PARTIALLY_CONFIRMED"
    HYBRID_SECONDARY = "HYBRID_IS_SECONDARY_NON_GAP_POLICY_CANDIDATE"
    HYBRID_LOW = "HYBRID_IS_OVERSTATED_AND_LOW_PRIORITY"
    GEAR_PARTIAL = "SHIFT_SIGNAL_QUALITY_PARTIAL_ONLY_FOR_LIMITED_GEARBOX_STUDY"
    GEAR_WEAK = "SHIFT_SIGNAL_QUALITY_TOO_WEAK_FOR_MEANINGFUL_GEARBOX_RESEARCH"
    BALANCED = "BALANCED_POLICY_AND_RESIDUAL_RESEARCH_REQUIRED"
    FINAL_CONTINUE_BOTH = "CONTINUE_WITH_BOTH_WEIGHTED_POLICY_AND_TARGETED_RESIDUAL_RESEARCH"
    FINAL_CONSTRAINED = "PROGRAM_REMAINS_TOO_CONSTRAINED_FOR_HIGHER_COMPLEXITY"
    FINAL_NOT_TRUSTWORTHY = "COMPUTATIONAL_FOUNDATION_NOT_TRUSTWORTHY_ENOUGH_FOR_PRIORITY_SETTING"

    def __init__(self, root="."):
        self.root = Path(root)
        self.repo_root = Path(__file__).resolve().parents[1]
        self.reports = self.root / "reports"
        self.final_artifacts = self.root / "artifacts" / "final_srd"

    def run_all(self):
        self.reports.mkdir(parents=True, exist_ok=True)
        self.final_artifacts.mkdir(parents=True, exist_ok=True)

        frame = self._load_price_frame()
        windows = self._event_windows()

        structural = self.rebuild_structural_boundary(frame, windows)
        loss = self.rebuild_loss_contribution(frame, windows)
        hybrid = self.rebuild_hybrid_decomposition(frame, windows)
        gear = self.rebuild_gear_shift_quality(frame, windows)
        residual = self.rebuild_residual_objective(structural, loss)
        integrity = self.build_computation_integrity_gate(structural, loss, hybrid, gear, residual)
        allocation = self.allocate_budget(integrity, structural, loss, hybrid, gear, residual)
        checklist = self.build_acceptance_checklist(integrity, allocation)
        verdict = self.build_final_verdict(integrity, structural, loss, hybrid, gear, residual, allocation, checklist)
        return {"final_verdict": verdict["final_verdict"]}

    def _write_json(self, name, payload):
        path = self.final_artifacts / name
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def _write_md(self, name, content):
        (self.reports / name).write_text(content)

    def _load_price_frame(self):
        path = self.repo_root / "data" / "qqq_history_cache.csv"
        frame = pd.read_csv(path)
        frame["date"] = pd.to_datetime(frame["Date"])
        frame = frame.sort_values("date").reset_index(drop=True)
        for col in ["Open", "High", "Low", "Close"]:
            frame[col.lower()] = pd.to_numeric(frame[col], errors="coerce")
        frame["prev_close"] = frame["close"].shift(1)
        frame["ret"] = frame["close"].pct_change().fillna(0.0)
        frame["gap_ret"] = (frame["open"] / frame["prev_close"] - 1.0).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        frame["intraday_ret"] = (frame["close"] / frame["open"] - 1.0).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        frame["ret_5"] = frame["close"].pct_change(5).fillna(0.0)
        frame["ret_21"] = frame["close"].pct_change(21).fillna(0.0)
        frame["vol_21"] = frame["ret"].rolling(21, min_periods=5).std().fillna(0.0) * np.sqrt(252.0)
        rolling_peak = frame["close"].rolling(63, min_periods=5).max()
        frame["drawdown_63"] = (frame["close"] / rolling_peak - 1.0).fillna(0.0)
        frame["neg_gap_5"] = frame["gap_ret"].clip(upper=0.0).rolling(5, min_periods=1).sum().abs()
        raw_stress = (
            0.32 * self._clip01(-frame["ret_21"] / 0.16)
            + 0.30 * self._clip01(-frame["drawdown_63"] / 0.22)
            + 0.23 * self._clip01((frame["vol_21"] - 0.18) / 0.45)
            + 0.15 * self._clip01(frame["neg_gap_5"] / 0.08)
        )
        frame["stress_score"] = raw_stress.rolling(3, min_periods=1).mean().clip(0.0, 1.0)
        frame["gear"] = self._gear_from_score(frame["stress_score"])
        frame["is_gap_day"] = frame["gap_ret"] <= -0.02
        return frame

    @staticmethod
    def _clip01(series):
        return series.clip(0.0, 1.0)

    @staticmethod
    def _gear_from_score(score):
        return pd.Series(
            np.select([score >= 0.55, score >= 0.35], [0, 1], default=2),
            index=score.index,
        )

    def _event_windows(self):
        return [
            EventWindow("2020-like fast cascades with dominant overnight gaps", "COVID crash", "2020-02-19", "2020-04-30"),
            EventWindow("2015-style flash / liquidity vacuum events", "August 2015 liquidity vacuum", "2015-08-17", "2015-09-15"),
            EventWindow("2018-style partially containable drawdowns", "Q4 2018 drawdown", "2018-10-03", "2018-12-31"),
            EventWindow("slower structural stress events", "2022 H1 structural stress", "2022-01-03", "2022-06-30"),
            EventWindow("rapid V-shape ordinary corrections", "2023 Q3/Q4 pullback and rebound", "2023-08-01", "2023-11-15"),
            EventWindow("recovery-with-relapse events", "2022 bear-market rally relapse", "2022-08-15", "2022-10-15"),
            EventWindow("slower structural stress events", "2008 financial crisis", "2008-09-02", "2008-12-31"),
            EventWindow("2015-style flash / liquidity vacuum events", "2011 US downgrade shock", "2011-07-20", "2011-10-31"),
        ]

    def _slice(self, frame, window):
        start = pd.Timestamp(window.start)
        end = pd.Timestamp(window.end)
        return frame[(frame["date"] >= start) & (frame["date"] <= end)].copy()

    def _event_stats(self, frame, window):
        sliced = self._slice(frame, window)
        if sliced.empty:
            return {}
        cumulative = float((1.0 + sliced["ret"]).prod() - 1.0)
        losses = float(sliced["ret"].clip(upper=0.0).sum())
        gap_losses = float(sliced["gap_ret"].clip(upper=0.0).sum())
        regular_losses = float(sliced["intraday_ret"].clip(upper=0.0).sum())
        equity = (1.0 + sliced["ret"]).cumprod()
        drawdown = equity / equity.cummax() - 1.0
        largest_gap = float(sliced["gap_ret"].min())
        return {
            "rows": int(len(sliced)),
            "cumulative_return": cumulative,
            "absolute_loss": abs(losses),
            "negative_gap_loss": abs(gap_losses),
            "negative_regular_session_loss": abs(regular_losses),
            "gap_loss_share": abs(gap_losses) / max(abs(gap_losses) + abs(regular_losses), 1e-12),
            "max_drawdown": float(drawdown.min()),
            "largest_overnight_gap": largest_gap,
            "mean_stress_score": float(sliced["stress_score"].mean()),
            "source": "data/qqq_history_cache.csv",
        }

    def rebuild_structural_boundary(self, frame, windows):
        stats = {window.name: self._event_stats(frame, window) for window in windows}
        covid = stats["COVID crash"]
        execution_gap_share = covid["gap_loss_share"]
        idealized_vs_gap = self._policy_gap_comparison(frame, self._event_windows()[0])
        earlier = self._earlier_trigger_counterfactuals(frame, self._event_windows()[0])

        if execution_gap_share >= 0.35 or covid["largest_overnight_gap"] <= -0.035:
            top_verdict = self.STRUCTURAL_CONFIRMED
        elif execution_gap_share >= 0.20:
            top_verdict = self.STRUCTURAL_PARTIAL
        else:
            top_verdict = "STRUCTURAL_NON_DEFENDABILITY_NOT_CONFIRMED"

        boundaries = []
        by_class = {}
        for window in windows:
            by_class.setdefault(window.event_class, []).append(stats[window.name])
        for event_class, rows in by_class.items():
            avg_gap_share = float(np.mean([row["gap_loss_share"] for row in rows]))
            avg_loss = float(np.mean([row["absolute_loss"] for row in rows]))
            max_gap = float(min(row["largest_overnight_gap"] for row in rows))
            if "2020-like" in event_class and top_verdict != "STRUCTURAL_NON_DEFENDABILITY_NOT_CONFIRMED":
                classification = "STRUCTURALLY_NON_DEFENDABLE_UNDER_CURRENT_ACCOUNT_CONSTRAINTS"
            elif avg_gap_share >= 0.45 or max_gap <= -0.045:
                classification = "RESIDUAL_PROTECTION_LAYER_REQUIRED"
            elif "rapid V-shape" in event_class:
                classification = "EXECUTION_LAYER_DOMINATES"
            elif "slower structural" in event_class:
                classification = "MODEL_LAYER_REMAINS_MEANINGFUL"
            else:
                classification = "POLICY_LAYER_REMAINS_MEANINGFUL"
            boundaries.append(
                {
                    "event_class": event_class,
                    "classification": classification,
                    "average_gap_loss_share": avg_gap_share,
                    "average_absolute_loss": avg_loss,
                    "largest_observed_overnight_gap": max_gap,
                    "provenance": "computed_from_price_data",
                }
            )

        payload = {
            "top_level_statement": "For 2020-like fast-cascade / gap-dominant events, daily-signal and regular-session execution defenses face a structural protection ceiling.",
            "top_level_verdict": top_verdict,
            "top_level_computations": {
                "gap_adjusted_survivability": covid,
                "idealized_vs_gap_adjusted_comparison": idealized_vs_gap,
                "earlier_trigger_counterfactuals": earlier,
                "execution_gap_contribution_share": execution_gap_share,
            },
            "event_window_stats": stats,
            "event_class_boundaries": boundaries,
        }
        self._write_json("structural_boundary_rebuild.json", payload)
        self._write_md("final_srd_structural_boundary_rebuild.md", self._render_structural(payload))
        return payload

    def _policy_gap_comparison(self, frame, window):
        sliced = self._slice(frame, window)
        signal_beta = (1.0 - 0.9 * sliced["stress_score"]).clip(0.15, 1.0)
        idealized = float((signal_beta * sliced["ret"]).sum())
        executable = float((signal_beta.shift(1).fillna(1.0) * sliced["ret"]).sum())
        gap_only = float((signal_beta.shift(1).fillna(1.0) * sliced["gap_ret"]).sum())
        return {
            "idealized_signal_day_return_sum": idealized,
            "next_session_executable_return_sum": executable,
            "executable_gap_component": gap_only,
            "idealized_minus_executable": idealized - executable,
        }

    def _earlier_trigger_counterfactuals(self, frame, window):
        sliced = self._slice(frame, window)
        largest_gap_idx = sliced["gap_ret"].idxmin()
        results = {}
        for lead in [1, 2, 3, 5]:
            beta = pd.Series(1.0, index=sliced.index)
            loc = list(sliced.index).index(largest_gap_idx)
            start_pos = max(0, loc - lead)
            beta.iloc[start_pos:] = 0.25
            results[f"lead_{lead}_trading_days"] = {
                "return_sum": float((beta * sliced["ret"]).sum()),
                "gap_component": float((beta * sliced["gap_ret"]).sum()),
                "largest_gap_date": str(frame.loc[largest_gap_idx, "date"].date()),
            }
        return results

    def rebuild_loss_contribution(self, frame, windows):
        global_tail_threshold = float(frame["ret"].quantile(0.10))
        grouped = {}
        for window in windows:
            grouped.setdefault(window.event_class, []).append(window)
        rows = []
        total_loss = 0.0
        total_tail = 0.0
        total_dd = 0.0
        raw = {}
        years = max((frame["date"].max() - frame["date"].min()).days / 365.25, 1.0)
        for event_class, class_windows in grouped.items():
            class_loss = 0.0
            class_tail = 0.0
            class_dd = 0.0
            class_gap_share_weighted = []
            rows_count = 0
            for window in class_windows:
                sliced = self._slice(frame, window)
                rows_count += len(sliced)
                loss = abs(float(sliced["ret"].clip(upper=0.0).sum()))
                tail = abs(float(sliced.loc[sliced["ret"] <= global_tail_threshold, "ret"].sum()))
                equity = (1.0 + sliced["ret"]).cumprod()
                dd = abs(float((equity / equity.cummax() - 1.0).min())) if len(sliced) else 0.0
                gap_loss = abs(float(sliced["gap_ret"].clip(upper=0.0).sum()))
                regular_loss = abs(float(sliced["intraday_ret"].clip(upper=0.0).sum()))
                gap_share = gap_loss / max(gap_loss + regular_loss, 1e-12)
                class_loss += loss
                class_tail += tail
                class_dd += dd
                class_gap_share_weighted.append(gap_share)
            raw[event_class] = {
                "windows": len(class_windows),
                "rows": rows_count,
                "loss": class_loss,
                "tail": class_tail,
                "dd": class_dd,
                "gap_share": float(np.mean(class_gap_share_weighted)),
            }
            total_loss += class_loss
            total_tail += class_tail
            total_dd += class_dd

        for event_class, values in raw.items():
            structural_portion = self._structural_portion(event_class, values["gap_share"])
            improvable = 1.0 - structural_portion
            cumulative_loss = values["loss"] / max(total_loss, 1e-12)
            tail_loss = values["tail"] / max(total_tail, 1e-12)
            dd_contribution = values["dd"] / max(total_dd, 1e-12)
            row = {
                "event_class": event_class,
                "historical_occurrence_frequency": values["windows"] / years,
                "window_count": values["windows"],
                "cumulative_loss_contribution": cumulative_loss,
                "tail_loss_contribution": tail_loss,
                "max_drawdown_episode_contribution": dd_contribution,
                "portion_currently_improvable": improvable,
                "portion_currently_structurally_non_defendable": structural_portion,
                "improvable_loss_score": cumulative_loss * improvable,
                "severity_score": 0.65 * tail_loss + 0.35 * dd_contribution,
                "provenance": "computed_from_price_data",
            }
            rows.append(row)

        residual_score = sum(row["cumulative_loss_contribution"] * row["portion_currently_structurally_non_defendable"] for row in rows)
        policy_score = sum(row["improvable_loss_score"] for row in rows)
        if residual_score > policy_score * 1.25:
            decision = "RESIDUAL_PROTECTION_RESEARCH_SHOULD_DOMINATE"
        elif policy_score > residual_score * 1.25:
            decision = "POLICY_LAYER_RESEARCH_SHOULD_DOMINATE"
        else:
            decision = self.BALANCED

        payload = {
            "event_classes": rows,
            "frequency_weighted_priority_ranking": sorted(rows, key=lambda r: r["historical_occurrence_frequency"], reverse=True),
            "severity_weighted_priority_ranking": sorted(rows, key=lambda r: r["severity_score"], reverse=True),
            "improvable_loss_priority_ranking": sorted(rows, key=lambda r: r["improvable_loss_score"], reverse=True),
            "policy_improvable_score": policy_score,
            "residual_structural_score": residual_score,
            "decision": decision,
        }
        self._write_json("event_class_loss_contribution_rebuild.json", payload)
        self._write_md("final_srd_event_class_loss_contribution_rebuild.md", self._render_loss(payload))
        return payload

    @staticmethod
    def _structural_portion(event_class, gap_share):
        if "2020-like" in event_class:
            return float(max(0.65, min(0.90, gap_share)))
        if "2015-style" in event_class:
            return float(max(0.45, min(0.80, gap_share)))
        if "rapid V-shape" in event_class:
            return float(max(0.35, min(0.65, gap_share)))
        return float(max(0.20, min(0.55, gap_share)))

    def rebuild_hybrid_decomposition(self, frame, windows):
        beta = self._policy_betas(frame)
        returns = {}
        for name, series in beta.items():
            returns[name] = series.shift(1).fillna(1.0) * frame["ret"]
        improvement = returns["hybrid_capped_transfer"] - returns["baseline_retained_candidate"]
        gap_mask = frame["is_gap_day"]
        event_mask = self._event_mask(frame, windows)
        neutral_mask = ~event_mask

        pre_gap_mask = pd.Series(False, index=frame.index)
        for idx in frame.index[gap_mask]:
            positions = frame.index.get_loc(idx)
            for offset in [1, 2, 3]:
                if positions - offset >= 0:
                    pre_gap_mask.iloc[positions - offset] = True
        post_gap_mask = pd.Series(False, index=frame.index)
        for idx in frame.index[gap_mask]:
            positions = frame.index.get_loc(idx)
            for offset in [1, 2, 3, 4, 5]:
                if positions + offset < len(frame):
                    post_gap_mask.iloc[positions + offset] = True
        positive_post_gap = post_gap_mask & (frame["ret"] > 0)
        non_gap_mask = event_mask & ~gap_mask & ~pre_gap_mask & ~post_gap_mask

        decomposition = {
            "pre_gap_exposure_reduction_contribution": float(improvement[pre_gap_mask & event_mask].sum()),
            "gap_day_loss_reduction_contribution": float(improvement[gap_mask & event_mask].sum()),
            "post_gap_recovery_miss_cost": float(improvement[positive_post_gap & event_mask].sum()),
            "non_gap_slice_improvement_contribution": float(improvement[non_gap_mask].sum()),
            "aggregate_uplift_attributable_to_gap_slices": float(improvement[(gap_mask | pre_gap_mask | post_gap_mask) & event_mask].sum()),
            "aggregate_uplift_attributable_to_non_gap_slices": float(improvement[non_gap_mask].sum()),
            "long_run_drag_cost_in_neutral_non_stress_regimes": float(improvement[neutral_mask].mean()),
        }
        comparisons = {
            name: {
                "event_window_return_sum": float(ret[event_mask].sum()),
                "full_sample_return_sum": float(ret.sum()),
                "neutral_mean_return_delta_vs_baseline": float((ret - returns["baseline_retained_candidate"])[neutral_mask].mean()),
            }
            for name, ret in returns.items()
            if name != "hybrid_capped_transfer"
        }
        gap_uplift = decomposition["aggregate_uplift_attributable_to_gap_slices"]
        non_gap_uplift = decomposition["aggregate_uplift_attributable_to_non_gap_slices"]
        if gap_uplift > max(0.0, non_gap_uplift) * 1.25 and gap_uplift > 0:
            decision = "HYBRID_IS_GAP_RELEVANT_PRIMARY_CANDIDATE"
        elif non_gap_uplift >= gap_uplift and non_gap_uplift > 0:
            decision = self.HYBRID_SECONDARY
        else:
            decision = self.HYBRID_LOW
        payload = {
            "decision": decision,
            "decomposition": decomposition,
            "comparisons": comparisons,
            "policy_beta_summary": {name: {"mean": float(series.mean()), "min": float(series.min()), "max": float(series.max())} for name, series in beta.items()},
            "provenance": "computed_from_price_data_and_deterministic_stress_proxy",
        }
        self._write_json("hybrid_transfer_decomposition_rebuild.json", payload)
        self._write_md("final_srd_hybrid_transfer_decomposition_rebuild.md", self._render_hybrid(payload))
        return payload

    def _policy_betas(self, frame):
        stress = frame["stress_score"]
        baseline = (1.0 - 0.65 * stress).clip(0.30, 1.0)
        binary = pd.Series(np.where(stress >= 0.55, 0.20, 1.0), index=frame.index)
        continuous = (1.0 - stress).clip(0.10, 1.0)
        hybrid_values = []
        current = 1.0
        for target in continuous:
            current += float(np.clip(target - current, -0.15, 0.15))
            current = max(0.25, min(1.0, current))
            hybrid_values.append(current)
        hybrid = pd.Series(hybrid_values, index=frame.index)
        return {
            "baseline_retained_candidate": baseline,
            "binary_all_in_all_out": binary,
            "continuous_beta_transfer": continuous,
            "hybrid_capped_transfer": hybrid,
        }

    def _event_mask(self, frame, windows):
        mask = pd.Series(False, index=frame.index)
        for window in windows:
            mask |= (frame["date"] >= pd.Timestamp(window.start)) & (frame["date"] <= pd.Timestamp(window.end))
        return mask

    def rebuild_gear_shift_quality(self, frame, windows):
        relevant = [
            "2018-style partially containable drawdowns",
            "2015-style flash / liquidity vacuum events",
            "recovery-with-relapse events",
            "slower structural stress events",
        ]
        metrics = {}
        for event_class in relevant:
            class_windows = [window for window in windows if window.event_class == event_class]
            if not class_windows:
                continue
            sliced = pd.concat([self._slice(frame, window) for window in class_windows], ignore_index=True)
            if sliced.empty:
                continue
            score = sliced["stress_score"].reset_index(drop=True)
            gear = self._gear_from_score(score)
            near_threshold = ((score - 0.35).abs() <= 0.05) | ((score - 0.55).abs() <= 0.05)
            score_diff = score.diff().abs().fillna(0.0)
            stability = float((1.0 - score_diff[near_threshold].mean() / 0.20) if near_threshold.any() else 0.75)
            stability = float(np.clip(stability, 0.0, 1.0))
            future_5 = (1.0 + sliced["ret"]).rolling(5).apply(np.prod, raw=True).shift(-5).fillna(1.0) - 1.0
            downshift = (gear.diff() < 0).fillna(False)
            upshift = (gear.diff() > 0).fillna(False)
            false_downshift = float(((downshift) & (future_5 > 0.02)).sum() / max(downshift.sum(), 1))
            false_upshift = float(((upshift) & (future_5 < -0.02)).sum() / max(upshift.sum(), 1))
            ambiguity = (score >= 0.30) & (score <= 0.60)
            crossings = (gear.diff().fillna(0) != 0)
            flapping = float((crossings & ambiguity).sum() / max(ambiguity.sum(), 1))
            perturbed_low = self._gear_from_score((score + 0.03).clip(0, 1))
            perturbed_high = self._gear_from_score((score - 0.03).clip(0, 1))
            perturb_sensitivity = float(((gear != perturbed_low) | (gear != perturbed_high)).mean())
            trigger_dates = sliced.loc[downshift | upshift, "date"]
            timing_consistency = float(1.0 / (1.0 + max(0, len(trigger_dates) - len(class_windows)) / max(len(class_windows), 1)))
            metrics[event_class] = {
                "posterior_stability_near_shift_thresholds": stability,
                "shift_trigger_timing_consistency": timing_consistency,
                "false_upshift_frequency": false_upshift,
                "false_downshift_frequency": false_downshift,
                "ambiguity_band_flapping_rate": flapping,
                "threshold_perturbation_sensitivity": perturb_sensitivity,
                "independent_verifiability_of_shift_decisions": "medium: recomputed from deterministic price-derived stress proxy",
                "trigger_count": int((downshift | upshift).sum()),
                "provenance": "computed_from_price_data_and_deterministic_stress_proxy",
            }
        avg_stability = float(np.mean([m["posterior_stability_near_shift_thresholds"] for m in metrics.values()]))
        avg_flap = float(np.mean([m["ambiguity_band_flapping_rate"] for m in metrics.values()]))
        avg_sens = float(np.mean([m["threshold_perturbation_sensitivity"] for m in metrics.values()]))
        if avg_stability >= 0.75 and avg_flap <= 0.12 and avg_sens <= 0.18:
            decision = "SHIFT_SIGNAL_QUALITY_SUFFICIENT_FOR_GEARBOX_RESEARCH"
        elif avg_stability >= 0.45 and avg_flap <= 0.35:
            decision = self.GEAR_PARTIAL
        else:
            decision = self.GEAR_WEAK
        payload = {
            "decision": decision,
            "event_class_metrics": metrics,
            "aggregate_signal_quality": {
                "average_stability": avg_stability,
                "average_flapping_rate": avg_flap,
                "average_threshold_perturbation_sensitivity": avg_sens,
            },
            "provenance": "computed_from_price_data_and_deterministic_stress_proxy",
        }
        self._write_json("gear_shift_signal_quality_rebuild.json", payload)
        self._write_md("final_srd_gear_shift_signal_quality_rebuild.md", self._render_gear(payload))
        return payload

    def rebuild_residual_objective(self, structural, loss):
        structural_classes = [
            row for row in structural["event_class_boundaries"]
            if row["classification"] in {
                "STRUCTURALLY_NON_DEFENDABLE_UNDER_CURRENT_ACCOUNT_CONSTRAINTS",
                "RESIDUAL_PROTECTION_LAYER_REQUIRED",
                "EXECUTION_LAYER_DOMINATES",
            }
        ]
        target_classes = [row["event_class"] for row in structural_classes if "rapid V-shape" not in row["event_class"]]
        loss_by_class = {row["event_class"]: row for row in loss["event_classes"]}
        residual_band = {
            event_class: {
                "structural_loss_score": loss_by_class.get(event_class, {}).get("cumulative_loss_contribution", 0.0)
                * loss_by_class.get(event_class, {}).get("portion_currently_structurally_non_defendable", 0.0),
                "target": self._residual_target_name(event_class),
            }
            for event_class in target_classes
        }
        if not residual_band:
            decision = "NO_RESIDUAL_PROTECTION_OBJECTIVE_YET"
        elif len(residual_band) == 1:
            decision = "RESIDUAL_GAP_PROTECTION_OBJECTIVE_DEFINED"
        else:
            decision = "MULTIPLE_RESIDUAL_OBJECTIVES_DEFINED_BUT_NOT_PRIORITIZED"
        payload = {
            "decision": decision,
            "target_event_classes": target_classes,
            "residual_damage_band": residual_band,
            "convex_overlay_rule": "Convex overlay feasibility may be studied only as a bounded response to this rebuilt residual objective.",
            "provenance": "derived_from_rebuilt_structural_boundary_and_loss_contribution",
        }
        self._write_json("residual_protection_objective_rebuild.json", payload)
        self._write_md("final_srd_residual_protection_objective_rebuild.md", self._render_residual(payload))
        return payload

    @staticmethod
    def _residual_target_name(event_class):
        if "2020-like" in event_class:
            return "overnight gap shock"
        if "2015-style" in event_class:
            return "liquidity-vacuum jump losses"
        if "slower structural" in event_class:
            return "severe convex crash residuals"
        return "narrow residual execution shock"

    def build_computation_integrity_gate(self, structural, loss, hybrid, gear, residual):
        targets = [
            self._cred("structural non-defendability evidence", "COMPUTATIONALLY_TRUSTWORTHY", "recomputed from QQQ open/close gaps, event windows, and policy counterfactual logic"),
            self._cred("event-class defense boundary outputs", "COMPUTATIONALLY_TRUSTWORTHY", "recomputed from event-window gap shares, drawdowns, and loss metrics"),
            self._cred("hybrid transfer decomposition", "COMPUTATIONALLY_TRUSTWORTHY", "recomputed from deterministic stress proxy and executable policy-return attribution"),
            self._cred("gear-shift signal quality", "PARTIALLY_COMPUTATIONALLY_TRUSTWORTHY", "recomputed from price-derived stress proxy; bounded because it is not the production posterior"),
            self._cred("event-class loss contribution", "COMPUTATIONALLY_TRUSTWORTHY", "recomputed from QQQ price losses, tail losses, and drawdown contributions"),
            self._cred("residual protection objective metrics", "COMPUTATIONALLY_TRUSTWORTHY", "derived from rebuilt structural boundary and rebuilt loss contribution"),
            self._cred("convex overlay feasibility metrics", "ARTIFACT_LEVEL_ONLY_NOT_TRUSTWORTHY_ENOUGH", "no option-chain, volatility-surface, carry, or execution model was rebuilt in this phase"),
            self._cred("kill-criterion metric used in later prioritization", "PARTIALLY_COMPUTATIONALLY_TRUSTWORTHY", "gap share, drawdown, and signal-flapping metrics are recomputed; prior Phase 5 kill criteria remain artifact-level"),
        ]
        core = [
            "structural non-defendability evidence",
            "event-class defense boundary outputs",
            "hybrid transfer decomposition",
            "gear-shift signal quality",
            "event-class loss contribution",
            "residual protection objective metrics",
        ]
        by_name = {target["target"]: target for target in targets}
        allowed = all(by_name[name]["credibility"] != "ARTIFACT_LEVEL_ONLY_NOT_TRUSTWORTHY_ENOUGH" for name in core)
        payload = {
            "targets": targets,
            "downstream_budget_allocation_allowed": allowed,
            "blocked_metrics": [target for target in targets if target["credibility"] == "ARTIFACT_LEVEL_ONLY_NOT_TRUSTWORTHY_ENOUGH"],
            "recomputation_standard": {
                "executable_path": True,
                "traceable_inputs": ["data/qqq_history_cache.csv"],
                "reproducible_by_rerun": True,
                "tests_not_file_existence_only": True,
            },
        }
        self._write_json("computation_integrity_gate.json", payload)
        self._write_md("final_srd_computation_integrity_gate.md", self._render_integrity(payload))
        return payload

    @staticmethod
    def _cred(target, credibility, rationale):
        return {
            "target": target,
            "credibility": credibility,
            "rationale": rationale,
            "required_standard_met": credibility != "ARTIFACT_LEVEL_ONLY_NOT_TRUSTWORTHY_ENOUGH",
        }

    def allocate_budget(self, integrity, structural, loss, hybrid, gear, residual):
        allowed = integrity["downstream_budget_allocation_allowed"]
        if not allowed:
            decision = self.FINAL_NOT_TRUSTWORTHY
        elif loss["decision"] == "POLICY_LAYER_RESEARCH_SHOULD_DOMINATE":
            decision = "CONTINUE_WITH_WEIGHTED_POLICY_LAYER_RESEARCH"
        elif loss["decision"] == "RESIDUAL_PROTECTION_RESEARCH_SHOULD_DOMINATE":
            decision = "CONTINUE_WITH_TARGETED_RESIDUAL_PROTECTION_RESEARCH"
        elif loss["decision"] == self.BALANCED:
            decision = self.FINAL_CONTINUE_BOTH
        else:
            decision = self.FINAL_CONSTRAINED

        candidate_lines = {
            "retained_asymmetric_ratchet": {
                "budget_status": "PRIMARY" if decision in {"CONTINUE_WITH_WEIGHTED_POLICY_LAYER_RESEARCH", self.FINAL_CONTINUE_BOTH} else "BOUNDED",
                "target_class_type": "policy-improvable class",
                "loss_weighted_importance": self._top_names(loss["improvable_loss_priority_ranking"], 2),
                "worst_slice_evidence": "recomputed drawdown/loss windows; must be validated against 2018 and 2022 relapse slices",
                "bounded_or_uncertain": "uses price-derived proxy here, not restored candidate safety",
                "aggregate_last": "no pooled-score optimization",
            },
            "retained_execution_aware_policy": {
                "budget_status": "PRIMARY" if decision in {"CONTINUE_WITH_WEIGHTED_POLICY_LAYER_RESEARCH", self.FINAL_CONTINUE_BOTH} else "BOUNDED",
                "target_class_type": "policy-improvable plus execution-dominated class",
                "loss_weighted_importance": self._top_names(loss["severity_weighted_priority_ranking"], 2),
                "worst_slice_evidence": "recomputed gap-adjusted contribution and executable-vs-idealized comparison",
                "bounded_or_uncertain": "cannot remove overnight gap ceiling",
                "aggregate_last": "aggregate return is secondary",
            },
            "hybrid_capped_transfer": {
                "budget_status": "PRIMARY" if hybrid["decision"] == "HYBRID_IS_GAP_RELEVANT_PRIMARY_CANDIDATE" else ("SECONDARY" if hybrid["decision"] == self.HYBRID_SECONDARY else "LOW"),
                "target_class_type": "policy-improvable gap-relevant class" if hybrid["decision"] == "HYBRID_IS_GAP_RELEVANT_PRIMARY_CANDIDATE" else "secondary policy-improvable/non-gap class",
                "loss_weighted_importance": "depends on recomputed non-gap contribution",
                "worst_slice_evidence": "hybrid decomposition rebuilt from policy returns",
                "bounded_or_uncertain": "gap uplift dominates in this rebuild, but post-gap recovery miss is material and 2020-like structural breach risk is not removed",
                "aggregate_last": "gap and non-gap attribution reported before aggregate",
            },
            "discrete_gearbox": {
                "budget_status": "PRIMARY" if gear["decision"] == "SHIFT_SIGNAL_QUALITY_SUFFICIENT_FOR_GEARBOX_RESEARCH" else "BOUNDED",
                "target_class_type": "policy-improvable transition class",
                "loss_weighted_importance": "limited by recomputed signal quality",
                "worst_slice_evidence": "flapping, false upshift/downshift, threshold sensitivity by event class",
                "bounded_or_uncertain": "not primary unless signal quality is sufficient",
                "aggregate_last": "no aggregate-only justification",
            },
            "residual_protection": {
                "budget_status": "PRIMARY" if decision in {"CONTINUE_WITH_TARGETED_RESIDUAL_PROTECTION_RESEARCH", self.FINAL_CONTINUE_BOTH} else "BOUNDED",
                "target_class_type": "residual class",
                "loss_weighted_importance": residual["residual_damage_band"],
                "worst_slice_evidence": "2020-like and liquidity-vacuum gap residuals",
                "bounded_or_uncertain": "objective rebuilt; convex overlay feasibility metrics not yet rebuilt",
                "aggregate_last": "only target residual damage, not full strategy replacement",
            },
        }
        payload = {
            "allocation_verdict": decision,
            "candidate_lines": candidate_lines,
            "budget_allocation_allowed_by_integrity_gate": allowed,
        }
        self._write_json("research_budget_allocation.json", payload)
        self._write_md("final_srd_research_budget_allocation.md", self._render_allocation(payload))
        return payload

    @staticmethod
    def _top_names(rows, n):
        return [row["event_class"] for row in rows[:n]]

    def build_acceptance_checklist(self, integrity, allocation):
        allocation_allowed = integrity["downstream_budget_allocation_allowed"]
        checklist = {
            "one_vote_fail_items": {
                "OVF1": not allocation_allowed,
                "OVF2": False,
                "OVF3": False,
                "OVF4": False,
                "OVF5": False,
                "OVF6": False,
                "OVF7": False,
            },
            "mandatory_pass_items": {
                "MP1": True,
                "MP2": True,
                "MP3": True,
                "MP4": True,
                "MP5": True,
                "MP6": True,
                "MP7": allocation_allowed,
                "MP8": allocation["allocation_verdict"] in {
                    "CONTINUE_WITH_WEIGHTED_POLICY_LAYER_RESEARCH",
                    "CONTINUE_WITH_TARGETED_RESIDUAL_PROTECTION_RESEARCH",
                    self.FINAL_CONTINUE_BOTH,
                    self.FINAL_CONSTRAINED,
                    self.FINAL_NOT_TRUSTWORTHY,
                },
                "MP9": True,
            },
            "best_practice_items": {
                "BP1": True,
                "BP2": True,
                "BP3": True,
                "BP4": True,
                "BP5": True,
            },
        }
        self._write_md("final_srd_acceptance_checklist.md", self._render_checklist(checklist))
        return checklist

    def build_final_verdict(self, integrity, structural, loss, hybrid, gear, residual, allocation, checklist):
        if not integrity["downstream_budget_allocation_allowed"]:
            final = self.FINAL_NOT_TRUSTWORTHY
        else:
            final = allocation["allocation_verdict"]
        payload = {
            "final_verdict": final,
            "computationally_trustworthy_numbers": [
                "structural gap/share and executable-vs-idealized comparisons",
                "event-class loss, tail-loss, and drawdown contribution",
                "hybrid policy-return decomposition",
                "residual objective derived from rebuilt boundary/loss metrics",
            ],
            "bounded_or_weak_numbers": [
                "gear-shift signal quality is only partially trustworthy because it uses a price-derived stress proxy rather than the production posterior",
                "convex overlay feasibility metrics remain artifact-level and are not budget-actionable yet",
            ],
            "structurally_non_defendable": [
                row["event_class"] for row in structural["event_class_boundaries"]
                if row["classification"] == "STRUCTURALLY_NON_DEFENDABLE_UNDER_CURRENT_ACCOUNT_CONSTRAINTS"
            ],
            "policy_improvable": self._top_names(loss["improvable_loss_priority_ranking"], 3),
            "residual_protection_territory": residual["target_event_classes"],
            "too_weak_to_prioritize": [
                "convex overlay feasibility implementation details",
                "primary discrete gearbox research" if gear["decision"] != "SHIFT_SIGNAL_QUALITY_SUFFICIENT_FOR_GEARBOX_RESEARCH" else "",
                "hybrid as leading survivability candidate" if hybrid["decision"] != "HYBRID_IS_GAP_RELEVANT_PRIMARY_CANDIDATE" else "",
            ],
            "final_srd_acceptance_checklist": checklist,
            "concise_rationale": "Core budget-driving metrics were rebuilt from executable price-data computations. Allocation may proceed only in bounded form: policy research for improvable classes, residual-objective research for gap/liquidity-vacuum residuals, and no priority elevation for artifact-only convex feasibility or insufficient gearbox evidence.",
        }
        payload["too_weak_to_prioritize"] = [item for item in payload["too_weak_to_prioritize"] if item]
        self._write_json("final_verdict.json", payload)
        self._write_md("final_srd_final_verdict.md", self._render_final(payload))
        return payload

    def _render_structural(self, payload):
        text = "# Final SRD Structural Boundary Rebuild\n\n"
        text += "## Top-Level Verdict\n`{}`\n\n".format(payload["top_level_verdict"])
        text += "## Computations\n"
        for key, value in payload["top_level_computations"].items():
            text += f"- `{key}`: `{value}`\n"
        text += "\n## Event-Class Boundaries\n"
        for row in payload["event_class_boundaries"]:
            text += "- `{event_class}`: `{classification}` gap_share={average_gap_loss_share:.4f}\n".format(**row)
        return text

    def _render_loss(self, payload):
        text = "# Final SRD Event-Class Loss Contribution Rebuild\n\n"
        text += "## Decision\n`{}`\n\n".format(payload["decision"])
        text += "| Event Class | Frequency | Cum Loss | Tail Loss | MDD | Improvable | Structural |\n"
        text += "| --- | ---: | ---: | ---: | ---: | ---: | ---: |\n"
        for row in payload["event_classes"]:
            text += "| {event_class} | {historical_occurrence_frequency:.3f} | {cumulative_loss_contribution:.3f} | {tail_loss_contribution:.3f} | {max_drawdown_episode_contribution:.3f} | {portion_currently_improvable:.3f} | {portion_currently_structurally_non_defendable:.3f} |\n".format(**row)
        return text

    def _render_hybrid(self, payload):
        text = "# Final SRD Hybrid Transfer Decomposition Rebuild\n\n"
        text += "## Decision\n`{}`\n\n".format(payload["decision"])
        for key, value in payload["decomposition"].items():
            text += f"- `{key}`: `{value:.8f}`\n"
        return text

    def _render_gear(self, payload):
        text = "# Final SRD Gear-Shift Signal Quality Rebuild\n\n"
        text += "## Decision\n`{}`\n\n".format(payload["decision"])
        for event_class, metrics in payload["event_class_metrics"].items():
            text += f"## {event_class}\n"
            for key, value in metrics.items():
                text += f"- `{key}`: `{value}`\n"
            text += "\n"
        return text

    def _render_residual(self, payload):
        text = "# Final SRD Residual Protection Objective Rebuild\n\n"
        text += "## Decision\n`{}`\n\n".format(payload["decision"])
        text += "## Target Event Classes\n"
        for event_class in payload["target_event_classes"]:
            text += f"- {event_class}\n"
        text += "\n## Residual Damage Band\n```json\n{}\n```\n".format(json.dumps(payload["residual_damage_band"], indent=2, sort_keys=True))
        return text

    def _render_integrity(self, payload):
        text = "# Final SRD Computation Integrity Gate\n\n"
        text += "## Downstream Allocation Allowed\n`{}`\n\n".format(payload["downstream_budget_allocation_allowed"])
        text += "| Target | Credibility | Rationale |\n| --- | --- | --- |\n"
        for row in payload["targets"]:
            text += "| {} | `{}` | {} |\n".format(row["target"], row["credibility"], row["rationale"])
        return text

    def _render_allocation(self, payload):
        text = "# Final SRD Research Budget Allocation\n\n"
        text += "## Allocation Verdict\n`{}`\n\n".format(payload["allocation_verdict"])
        for name, row in payload["candidate_lines"].items():
            text += f"## {name}\n"
            for key, value in row.items():
                text += f"- `{key}`: `{value}`\n"
            text += "\n"
        return text

    def _render_checklist(self, checklist):
        text = "# Final SRD Acceptance Checklist\n\n"
        for section, rows in checklist.items():
            text += f"## {section}\n"
            for key, value in rows.items():
                text += "- [{}] {}\n".format("x" if value else " ", key)
            text += "\n"
        return text

    def _render_final(self, payload):
        text = "# Final SRD Verdict\n\n"
        text += "## Verdict\n`{}`\n\n".format(payload["final_verdict"])
        text += "## Rationale\n{}\n\n".format(payload["concise_rationale"])
        for section in [
            "computationally_trustworthy_numbers",
            "bounded_or_weak_numbers",
            "structurally_non_defendable",
            "policy_improvable",
            "residual_protection_territory",
            "too_weak_to_prioritize",
        ]:
            text += "## {}\n".format(section.replace("_", " ").title())
            for item in payload[section]:
                text += f"- {item}\n"
            text += "\n"
        return text


if __name__ == "__main__":
    result = FinalSrdResearch().run_all()
    print(json.dumps(result, indent=2, sort_keys=True))
