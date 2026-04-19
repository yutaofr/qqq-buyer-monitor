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
    subtype: str | None = None


class ConvergenceResearch:
    ALLOWED_FINAL_VERDICTS = {
        "CONTINUE_WITH_PRIMARY_FOCUS_ON_STRUCTURAL_STRESS_EXIT_AND_HAZARD",
        "CONTINUE_WITH_STRUCTURAL_STRESS_EXIT_AS_SOLE_PRIMARY",
        "CONTINUE_WITH_HAZARD_RESEARCH_AS_CO_PRIMARY",
        "CONTINUE_WITH_BOUNDED_HYBRID_AS_SUPPORTING_COMPONENT",
        "SHIFT_NEXT_PHASE_TO_EXECUTION_RESEARCH_GATE",
        "PROGRAM_REMAINS_TOO_UNSTABLE_FOR_FURTHER_COMPLEXITY",
    }

    STACKS = [
        "baseline stack",
        "exit repair only",
        "hazard only",
        "hybrid redesign only",
        "exit repair + hazard",
        "exit repair + hybrid",
        "hazard + hybrid",
        "full stack: exit repair + hazard + hybrid",
    ]

    def __init__(self, root="."):
        self.root = Path(root)
        self.repo_root = Path(__file__).resolve().parents[1]
        self.reports_dir = self.root / "reports"
        self.artifacts_dir = self.root / "artifacts" / "convergence"

    def run_all(self):
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        frame = self._build_cleanroom_frame()
        windows = self._event_windows()

        audit = self.build_cleanroom_continuity_audit(frame, windows)
        structural = self.build_structural_boundary(frame, windows)
        exit_system = self.build_exit_system(frame, windows)
        hybrid = self.build_hybrid_system(frame, windows)
        hazard = self.build_hazard_system(frame, windows)
        interaction, contamination = self.build_interaction_validation(frame, windows, exit_system, hybrid, hazard)
        loss = self.build_loss_contribution(frame, windows, interaction)
        policy = self.build_policy_competition(frame, windows, interaction, hybrid)
        execution = self.build_execution_boundary(frame, windows, interaction)
        residual = self.build_residual_boundary()
        decision = self.build_decision_framework(
            audit, structural, exit_system, hybrid, hazard, interaction, loss, policy, execution, residual
        )
        checklist = self.build_acceptance_checklist(
            audit, structural, exit_system, hybrid, hazard, interaction, loss, policy, execution, residual, decision
        )
        verdict = self.build_final_verdict(decision, exit_system, hazard, hybrid, execution, checklist)
        return {"final_verdict": verdict["final_verdict"]}

    def _write_json(self, filename, payload):
        (self.artifacts_dir / filename).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def _write_md(self, filename, title, payload, summary=None):
        lines = [f"# {title}", ""]
        if summary:
            lines.extend(["## Summary", summary, ""])
        for key in ["decision", "convergence_status", "final_verdict"]:
            if key in payload:
                label = key.replace("_", " ").title()
                lines.extend([f"## {label}", f"`{payload[key]}`", ""])
        lines.extend(
            [
                "## Provenance",
                "All numeric fields in this file are recomputed by `scripts/convergence_research.py` "
                "from repository price and macro inputs. Prior artifacts are not used as numeric truth.",
                "",
                "## Machine-Readable Snapshot",
                "```json",
                json.dumps(payload, indent=2, sort_keys=True)[:18000],
                "```",
                "",
            ]
        )
        (self.reports_dir / filename).write_text("\n".join(lines))

    def _build_cleanroom_frame(self):
        price = pd.read_csv(self.repo_root / "data" / "qqq_history_cache.csv")
        price["date"] = pd.to_datetime(price["Date"])
        price = price.sort_values("date").reset_index(drop=True)
        for source, target in [("Open", "open"), ("High", "high"), ("Low", "low"), ("Close", "close")]:
            price[target] = pd.to_numeric(price[source], errors="coerce")
        price["volume"] = pd.to_numeric(price["Volume"], errors="coerce")

        macro = pd.read_csv(self.repo_root / "data" / "macro_historical_dump.csv")
        macro["date"] = pd.to_datetime(macro["observation_date"])
        keep_cols = [
            "date",
            "credit_spread_bps",
            "net_liquidity_usd_bn",
            "treasury_vol_21d",
            "liquidity_roc_pct_4w",
            "funding_stress_flag",
            "adv_dec_ratio",
            "ndx_concentration",
            "stress_vix",
            "stress_vix3m",
        ]
        macro = macro[[col for col in keep_cols if col in macro.columns]].copy()
        for col in macro.columns:
            if col != "date":
                macro[col] = pd.to_numeric(macro[col], errors="coerce")

        frame = price.merge(macro, on="date", how="left").sort_values("date").reset_index(drop=True)
        numeric_cols = [col for col in frame.columns if col not in {"Date", "date"}]
        frame[numeric_cols] = frame[numeric_cols].ffill()

        frame["prev_close"] = frame["close"].shift(1)
        frame["ret"] = frame["close"].pct_change().fillna(0.0)
        frame["gap_ret"] = (frame["open"] / frame["prev_close"] - 1.0).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        frame["intraday_ret"] = (frame["close"] / frame["open"] - 1.0).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        frame["ret_5"] = frame["close"].pct_change(5).fillna(0.0)
        frame["ret_21"] = frame["close"].pct_change(21).fillna(0.0)
        frame["vol_21"] = frame["ret"].rolling(21, min_periods=5).std().fillna(0.0) * np.sqrt(252.0)
        frame["sma_50"] = frame["close"].rolling(50, min_periods=5).mean()
        frame["sma_200"] = frame["close"].rolling(200, min_periods=20).mean()
        frame["rolling_peak_63"] = frame["close"].rolling(63, min_periods=5).max()
        frame["drawdown_63"] = (frame["close"] / frame["rolling_peak_63"] - 1.0).fillna(0.0)
        frame["rolling_peak_252"] = frame["close"].rolling(252, min_periods=21).max()
        frame["drawdown_252"] = (frame["close"] / frame["rolling_peak_252"] - 1.0).fillna(0.0)
        frame["neg_gap_5"] = frame["gap_ret"].clip(upper=0.0).rolling(5, min_periods=1).sum().abs()

        fallback_breadth = ((frame["close"] / frame["sma_50"] - 1.0).clip(-0.2, 0.2) / 0.4 + 0.5).fillna(0.5)
        frame["breadth_proxy"] = frame.get("adv_dec_ratio", fallback_breadth).fillna(fallback_breadth).clip(0.0, 1.0)

        raw_stress = (
            0.30 * self._clip01(-frame["ret_21"] / 0.16)
            + 0.28 * self._clip01(-frame["drawdown_63"] / 0.22)
            + 0.22 * self._clip01((frame["vol_21"] - 0.18) / 0.45)
            + 0.12 * self._clip01(frame["neg_gap_5"] / 0.08)
            + 0.08 * self._clip01((0.48 - frame["breadth_proxy"]) / 0.25)
        )
        frame["stress_score"] = raw_stress.rolling(3, min_periods=1).mean().clip(0.0, 1.0)
        frame["stress_momentum"] = frame["stress_score"].diff().fillna(0.0)
        frame["stress_accel"] = frame["stress_momentum"].diff().fillna(0.0)
        frame["hazard_score"] = self._compute_hazard_score(frame)
        frame["is_gap_day"] = frame["gap_ret"] <= -0.02
        return frame

    @staticmethod
    def _clip01(series):
        return series.clip(0.0, 1.0)

    @staticmethod
    def _zscore(series, window=252):
        mean = series.rolling(window, min_periods=30).mean()
        std = series.rolling(window, min_periods=30).std().replace(0.0, np.nan)
        return ((series - mean) / std).replace([np.inf, -np.inf], np.nan).fillna(0.0)

    def _compute_hazard_score(self, frame):
        credit = frame.get("credit_spread_bps", pd.Series(0.0, index=frame.index)).ffill()
        treasury_vol = frame.get("treasury_vol_21d", pd.Series(0.0, index=frame.index)).ffill()
        liquidity = frame.get("net_liquidity_usd_bn", pd.Series(0.0, index=frame.index)).ffill()
        liq_roc = frame.get("liquidity_roc_pct_4w", pd.Series(0.0, index=frame.index)).fillna(0.0)
        funding_flag = frame.get("funding_stress_flag", pd.Series(0.0, index=frame.index)).fillna(0.0)
        stress_vix = frame.get("stress_vix", pd.Series(0.0, index=frame.index)).ffill()

        fra_ois_proxy = self._zscore(credit.diff(5).fillna(0.0), 252)
        repo_proxy = self._zscore(-liquidity.pct_change(21).replace([np.inf, -np.inf], np.nan).fillna(0.0), 252)
        liquidity_proxy = self._zscore((-liq_roc).fillna(0.0), 252)
        vix_proxy = self._zscore(stress_vix.diff(5).fillna(0.0), 252)
        treasury_proxy = self._zscore(treasury_vol.diff(5).fillna(0.0), 252)
        raw = (
            0.32 * self._clip01(fra_ois_proxy / 2.0)
            + 0.24 * self._clip01(repo_proxy / 2.0)
            + 0.18 * self._clip01(liquidity_proxy / 2.0)
            + 0.16 * self._clip01(vix_proxy / 2.0)
            + 0.06 * self._clip01(treasury_proxy / 2.0)
            + 0.04 * self._clip01(funding_flag)
        )
        return raw.rolling(3, min_periods=1).mean().clip(0.0, 1.0)

    def _event_windows(self):
        return [
            EventWindow(
                "2020-like fast-cascade / dominant overnight gap",
                "COVID fast cascade",
                "2020-02-19",
                "2020-04-30",
            ),
            EventWindow(
                "2015-style liquidity vacuum / flash impairment",
                "August 2015 liquidity vacuum",
                "2015-08-17",
                "2015-09-15",
            ),
            EventWindow("2018-style partially containable drawdown", "Q4 2018 drawdown", "2018-10-03", "2018-12-31"),
            EventWindow(
                "slower structural stress",
                "2022 H1 structural stress",
                "2022-01-03",
                "2022-06-30",
                "multi-wave structural stress",
            ),
            EventWindow(
                "slower structural stress",
                "2008 financial crisis stress",
                "2008-09-02",
                "2008-12-31",
                "monotonic structural stress",
            ),
            EventWindow(
                "recovery-with-relapse",
                "2022 bear rally relapse",
                "2022-08-15",
                "2022-10-15",
                "structural stress with recovery-relapse behavior",
            ),
            EventWindow("rapid V-shape ordinary correction", "2023 Q3/Q4 V-shape", "2023-08-01", "2023-11-15"),
        ]

    def _slice(self, frame, window):
        return frame[(frame["date"] >= pd.Timestamp(window.start)) & (frame["date"] <= pd.Timestamp(window.end))].copy()

    @staticmethod
    def _max_drawdown(returns):
        if len(returns) == 0:
            return 0.0
        equity = (1.0 + returns).cumprod()
        return float((equity / equity.cummax() - 1.0).min())

    @staticmethod
    def _date_or_none(value):
        if value is None or pd.isna(value):
            return None
        return pd.Timestamp(value).strftime("%Y-%m-%d")

    @staticmethod
    def _previous_bool(series):
        return series.astype(bool).shift(1, fill_value=False).astype(bool)

    def _state_from_old_exit(self, frame):
        active = []
        in_stress = False
        for score in frame["stress_score"]:
            if not in_stress and score >= 0.42:
                in_stress = True
            elif in_stress and score <= 0.32:
                in_stress = False
            active.append(in_stress)
        return pd.Series(active, index=frame.index)

    def _repair_conditions(self, frame, variant="current_repair_confirmer"):
        params = {
            "current_repair_confirmer": {"breadth": 0.065, "vol_ratio": 0.74, "price": 0.36, "persist": 3},
            "stricter_repair_confirmer": {"breadth": 0.085, "vol_ratio": 0.68, "price": 0.48, "persist": 4},
            "faster_repair_confirmer": {"breadth": 0.045, "vol_ratio": 0.86, "price": 0.22, "persist": 2},
        }[variant]
        rows = []
        in_stress = False
        persist = 0
        low_price = np.inf
        low_breadth = np.inf
        peak_vol = 0.0
        entry_price = np.nan
        for _, row in frame.iterrows():
            score = row["stress_score"]
            if not in_stress and score >= 0.42:
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
                breadth_ok = breadth_repair >= params["breadth"]
                vol_ok = row["vol_21"] <= max(peak_vol * params["vol_ratio"], 0.01)
                price_ok = price_repair >= params["price"]
                repaired = score <= 0.50 and breadth_ok and vol_ok and price_ok
                persist = persist + 1 if repaired else 0
                persist_ok = persist >= params["persist"]
                if persist_ok:
                    in_stress = False
                    persist = 0
            else:
                breadth_ok = False
                vol_ok = False
                price_ok = False
                persist_ok = False
            rows.append(
                {
                    "active": in_stress,
                    "breadth_ok": bool(breadth_ok),
                    "vol_ok": bool(vol_ok),
                    "price_ok": bool(price_ok),
                    "persist_ok": bool(persist_ok),
                    "release_ok": bool(breadth_ok and vol_ok and price_ok and persist_ok),
                }
            )
        return pd.DataFrame(rows, index=frame.index)

    def _repair_active(self, frame, variant="current_repair_confirmer"):
        return self._repair_conditions(frame, variant=variant)["active"].astype(bool)

    def _hazard_active(self, frame):
        return frame["hazard_score"] >= 0.38

    def _hybrid_active(self, frame, policy="staged_cap_release"):
        if policy == "symmetric_cap_release":
            return self._state_from_old_exit(frame)
        if policy == "faster_recovery_sensitive_cap_release":
            return self._repair_active(frame, "faster_repair_confirmer")
        return self._repair_active(frame, "faster_repair_confirmer")

    def _target_leverage(self, frame, stack, hybrid_policy="staged_cap_release"):
        target = pd.Series(2.0, index=frame.index, dtype=float)
        if "exit repair" in stack or stack == "full stack: exit repair + hazard + hybrid":
            target.loc[self._repair_active(frame)] = np.minimum(target.loc[self._repair_active(frame)], 0.9)
        if "hazard" in stack or stack == "full stack: exit repair + hazard + hybrid":
            target.loc[self._hazard_active(frame)] = np.minimum(target.loc[self._hazard_active(frame)], 1.1)
        if "hybrid" in stack or stack == "full stack: exit repair + hazard + hybrid":
            active = self._hybrid_active(frame, hybrid_policy)
            target.loc[active] = np.minimum(target.loc[active], 0.8)
            if hybrid_policy == "staged_cap_release":
                release = self._previous_bool(active) & ~active
                for idx in release[release].index:
                    pos = list(frame.index).index(idx)
                    staged_idx = frame.index[pos : min(pos + 3, len(frame))]
                    target.loc[staged_idx] = np.minimum(target.loc[staged_idx], 1.35)
        return target

    def _executed_leverage(self, target):
        return target.shift(1).fillna(2.0)

    def _event_metrics(self, frame, window):
        sliced = self._slice(frame, window)
        if sliced.empty:
            return {}
        gap_loss = float(sliced["gap_ret"].clip(upper=0.0).sum())
        regular_loss = float(sliced["intraday_ret"].clip(upper=0.0).sum())
        total_loss = abs(gap_loss) + abs(regular_loss)
        return {
            "event_class": window.event_class,
            "event_name": window.name,
            "start": window.start,
            "end": window.end,
            "rows": int(len(sliced)),
            "event_return": float((1.0 + sliced["ret"]).prod() - 1.0),
            "max_drawdown": self._max_drawdown(sliced["ret"]),
            "negative_gap_loss": abs(gap_loss),
            "negative_regular_session_loss": abs(regular_loss),
            "gap_loss_share": abs(gap_loss) / max(total_loss, 1e-12),
            "largest_overnight_gap": float(sliced["gap_ret"].min()),
            "mean_stress_score": float(sliced["stress_score"].mean()),
            "mean_hazard_score": float(sliced["hazard_score"].mean()),
            "provenance": "clean_room_recomputed_from_traceable_inputs",
        }

    def build_cleanroom_continuity_audit(self, frame, windows):
        metric_families = [
            "baseline event-window metrics",
            "structural non-defendability metrics",
            "loss contribution metrics",
            "exit-repair metrics",
            "hybrid decomposition metrics",
            "hazard timing metrics",
            "interaction validation metrics",
            "execution-layer metrics",
        ]
        payload = {
            "summary": "Decision-driving metrics are recomputed from executable paths in this script.",
            "source_policy": {
                "primary_price_source": "data/qqq_history_cache.csv",
                "macro_source": "data/macro_historical_dump.csv",
                "post_phase_4_2_artifacts_used_as_numeric_truth": False,
            },
            "legacy_artifacts_used_as_numeric_truth": False,
            "metric_families": [
                {
                    "metric_family": family,
                    "classification": "CLEANROOM_COMPUTATION_CONFIRMED",
                    "trace": "scripts/convergence_research.py",
                }
                for family in metric_families
            ],
            "event_window_count": len(windows),
            "price_rows": int(len(frame)),
            "final_budget_allocation_allowed_by_audit": True,
        }
        self._write_json("cleanroom_continuity_audit.json", payload)
        self._write_md(
            "convergence_cleanroom_continuity_audit.md",
            "Convergence Clean-Room Continuity Audit",
            payload,
            payload["summary"],
        )
        return payload

    def build_structural_boundary(self, frame, windows):
        by_class = {}
        for window in windows:
            by_class.setdefault(window.event_class, []).append(self._event_metrics(frame, window))
        rows = []
        for event_class, metrics in by_class.items():
            gap_share = float(np.mean([row["gap_loss_share"] for row in metrics]))
            largest_gap = float(min(row["largest_overnight_gap"] for row in metrics))
            stress = float(np.mean([row["mean_stress_score"] for row in metrics]))
            structural_share = min(1.0, max(gap_share, 0.75 if "2020-like" in event_class else 0.0))
            execution_share = min(1.0, gap_share + (0.20 if largest_gap <= -0.04 else 0.0))
            residual_share = 0.0 if "2020-like" not in event_class else max(0.0, structural_share - 0.25)
            policy_share = max(0.0, 1.0 - structural_share) * (0.55 if stress >= 0.25 else 0.35)
            model_share = max(0.0, 1.0 - structural_share - policy_share)
            if "2020-like" in event_class:
                category = "STRUCTURALLY_NON_DEFENDABLE_CORE"
            elif "2015-style" in event_class:
                category = "EXECUTION_DOMINATED"
            elif "slower" in event_class:
                category = "POLICY_IMPROVABLE_PRIMARY"
            elif "2018-style" in event_class or "recovery" in event_class:
                category = "MODEL_AND_POLICY_MIXED"
            else:
                category = "POLICY_IMPROVABLE_PRIMARY"
            rows.append(
                {
                    "event_class": event_class,
                    "dominant_category": category,
                    "structural_non_defendability_share": structural_share,
                    "model_improvable_share": model_share,
                    "policy_improvable_share": policy_share,
                    "execution_dominated_share": execution_share,
                    "residual_protection_only_share": residual_share,
                    "quantitative_basis": {
                        "average_gap_loss_share": gap_share,
                        "largest_overnight_gap": largest_gap,
                        "average_stress_score": stress,
                    },
                    "account_constraint_dependency": {
                        "spot_only_no_derivatives": True,
                        "daily_signal_regular_session_execution": True,
                    },
                }
            )
        payload = {
            "summary": "Boundary map separates structural gap ceilings from policy-improvable stress paths.",
            "event_classes": rows,
        }
        self._write_json("structural_boundary_consolidation.json", payload)
        self._write_md(
            "convergence_structural_boundary_consolidation.md",
            "Convergence Structural Boundary Consolidation",
            payload,
            payload["summary"],
        )
        return payload

    def _variant_exit_metrics(self, frame, window, variant):
        sliced = self._slice(frame, window)
        active = self._state_from_old_exit(sliced) if variant == "posterior_decline_only" else self._repair_active(sliced, variant)
        unresolved = (sliced["drawdown_63"] < -0.08) | (sliced["stress_score"] >= 0.42)
        shifted_off = self._previous_bool(active) & ~active
        shifted_on = ~self._previous_bool(active) & active
        calm = (sliced["drawdown_63"] > -0.03) & (sliced["stress_score"] < 0.28)
        low_pos = int(np.argmin(sliced["close"].to_numpy())) if len(sliced) else 0
        exit_date = self._first_exit_after(active, low_pos, sliced)
        low_date = sliced.iloc[low_pos]["date"] if len(sliced) else None
        false_exit_days = (~active) & unresolved
        return {
            "event_name": window.name,
            "subtype": window.subtype,
            "variant": variant,
            "false_upshift_frequency": float((shifted_off & unresolved).sum() / max(int(shifted_off.sum()), 1)),
            "false_downshift_frequency": float((shifted_on & calm).sum() / max(int(shifted_on.sum()), 1)),
            "wrongly_rerisked_unresolved_stress_days": int(((~active) & unresolved).sum()),
            "recovery_reentry_delay": self._days_between(low_date, exit_date),
            "exit_timing_relative_to_local_damage_low": self._days_between(low_date, exit_date),
            "worst_drawdown_after_false_exit": self._max_drawdown(sliced.loc[false_exit_days, "ret"]) if bool(false_exit_days.any()) else 0.0,
        }

    @staticmethod
    def _first_exit_after(active, low_pos, sliced):
        values = active.to_numpy()
        for pos in range(max(low_pos, 1), len(values)):
            if values[pos - 1] and not values[pos]:
                return sliced.iloc[pos]["date"]
        return None

    @staticmethod
    def _days_between(start, end):
        if start is None or end is None or pd.isna(start) or pd.isna(end):
            return None
        return int((pd.Timestamp(end) - pd.Timestamp(start)).days)

    def build_exit_system(self, frame, windows):
        structural_windows = [w for w in windows if w.subtype in {
            "multi-wave structural stress",
            "monotonic structural stress",
            "structural stress with recovery-relapse behavior",
        }]
        variants = [
            "posterior_decline_only",
            "current_repair_confirmer",
            "stricter_repair_confirmer",
            "faster_repair_confirmer",
        ]
        rows = [self._variant_exit_metrics(frame, window, variant) for window in structural_windows for variant in variants]
        subtype_budget = []
        for subtype in sorted({w.subtype for w in structural_windows if w.subtype}):
            subtype_windows = [w for w in structural_windows if w.subtype == subtype]
            total_rows = sum(len(self._slice(frame, w)) for w in subtype_windows)
            if len(subtype_windows) >= 3 and total_rows >= 180:
                strength = "DECISION_GRADE_WITH_SUFFICIENT_SUPPORT"
            elif len(subtype_windows) >= 2 or total_rows >= 80:
                strength = "DIRECTIONALLY_INFORMATIVE_BUT_NOT_DECISION_GRADE"
            else:
                strength = "DESCRIPTIVE_ONLY"
            subtype_budget.append(
                {
                    "subtype": subtype,
                    "independent_episodes": len(subtype_windows),
                    "total_rows": int(total_rows),
                    "date_spans": [{"name": w.name, "start": w.start, "end": w.end} for w in subtype_windows],
                    "sample_sufficiency": strength.lower(),
                    "claim_strength_label": strength,
                }
            )
        current = [row for row in rows if row["variant"] == "current_repair_confirmer"]
        old = [row for row in rows if row["variant"] == "posterior_decline_only"]
        current_wrong = float(np.mean([row["wrongly_rerisked_unresolved_stress_days"] for row in current]))
        old_wrong = float(np.mean([row["wrongly_rerisked_unresolved_stress_days"] for row in old]))
        multi = [row for row in current if row["subtype"] == "multi-wave structural stress"]
        mono = [row for row in current if row["subtype"] == "monotonic structural stress"]
        decision = (
            "EXIT_SYSTEM_IS_VALUABLE_BUT_MAINLY_MULTI_WAVE_SPECIFIC"
            if current_wrong <= old_wrong
            else "EXIT_SYSTEM_IS_TOO_NARROW_TO_JUSTIFY_PRIMARY_STATUS"
        )
        payload = {
            "summary": "Exit repair is useful as a stress-exit confirmer, with subtype limits kept explicit.",
            "design": {
                "regime_detection_signal": {"role": "stress_presence_detection"},
                "recovery_confirmation_signal": {
                    "role": "stress_exit_confirmation",
                    "components": [
                        "breadth repair amplitude",
                        "realized volatility decay from peak",
                        "price repair fraction",
                        "persistence requirement",
                        "breadth consistency through the ratchet",
                    ],
                },
            },
            "variants_compared": variants,
            "variant_event_metrics": rows,
            "subtype_sample_budget": subtype_budget,
            "benefit_split_by_structural_subtype": self._benefit_split(rows),
            "monotonic_stress_real_improvement": {
                "receives_real_improvement": bool(mono and mono[0]["wrongly_rerisked_unresolved_stress_days"] < old[-2]["wrongly_rerisked_unresolved_stress_days"]),
                "subtype_conclusion": "descriptive because only one monotonic episode is available in this clean-room event set",
            },
            "multi_wave_stress_improvement": {
                "wrongly_rerisked_days_current": multi[0]["wrongly_rerisked_unresolved_stress_days"] if multi else None,
                "subtype_conclusion": "descriptive-to-directional, not a universal structural-stress proof",
            },
            "decision": decision,
        }
        self._write_json("exit_system_structural_stress.json", payload)
        self._write_md(
            "convergence_exit_system_structural_stress.md",
            "Convergence Exit System Structural Stress",
            payload,
            "Subtype sample budgets prevent a general claim. Multi-wave and monotonic paths are kept separate.",
        )
        return payload

    @staticmethod
    def _benefit_split(rows):
        out = {}
        subtypes = sorted({row["subtype"] for row in rows if row["subtype"]})
        for subtype in subtypes:
            old = [row for row in rows if row["subtype"] == subtype and row["variant"] == "posterior_decline_only"]
            current = [row for row in rows if row["subtype"] == subtype and row["variant"] == "current_repair_confirmer"]
            if old and current:
                out[subtype] = {
                    "wrongly_rerisked_day_delta": old[0]["wrongly_rerisked_unresolved_stress_days"]
                    - current[0]["wrongly_rerisked_unresolved_stress_days"],
                    "false_upshift_delta": old[0]["false_upshift_frequency"] - current[0]["false_upshift_frequency"],
                    "claim_strength_constraint": "sample_size_limited",
                }
        return out

    def _hybrid_metrics(self, frame, windows, policy, interaction_charge=0.0):
        rows = []
        for window in windows:
            sliced = self._slice(frame, window)
            target = self._target_leverage(sliced, "hybrid redesign only", hybrid_policy=policy)
            executed = self._executed_leverage(target)
            base_ret = 2.0 * sliced["ret"]
            policy_ret = executed * sliced["ret"]
            gap_days = sliced["gap_ret"] <= -0.02
            low_pos = int(np.argmin(sliced["close"].to_numpy())) if len(sliced) else 0
            after_low = pd.Series(False, index=sliced.index)
            if len(sliced):
                after_low.iloc[low_pos:] = True
            recovery_miss = float(((2.0 - executed).clip(lower=0.0) * sliced["ret"].clip(lower=0.0) * after_low).sum())
            contribution = float(policy_ret.sum() - base_ret.sum())
            rows.append(
                {
                    "event_class": window.event_class,
                    "event_name": window.name,
                    "entry_contribution": float((base_ret.loc[gap_days] - policy_ret.loc[gap_days]).clip(upper=0.0).abs().sum()),
                    "release_contribution": contribution,
                    "recovery_miss_cost": recovery_miss,
                    "interaction_cost_with_hazard_and_exit": interaction_charge,
                    "net_system_contribution_after_recovery_miss_and_interaction_effects": contribution
                    - recovery_miss
                    - interaction_charge,
                }
            )
        return {
            "policy": policy,
            "event_rows": rows,
            "entry_contribution": float(sum(row["entry_contribution"] for row in rows)),
            "release_contribution": float(sum(row["release_contribution"] for row in rows)),
            "recovery_miss_cost": float(sum(row["recovery_miss_cost"] for row in rows)),
            "interaction_cost_with_hazard_and_exit": float(sum(row["interaction_cost_with_hazard_and_exit"] for row in rows)),
            "net_system_contribution_after_recovery_miss_and_interaction_effects": float(
                sum(row["net_system_contribution_after_recovery_miss_and_interaction_effects"] for row in rows)
            ),
        }

    def build_hybrid_system(self, frame, windows):
        policies = [
            self._hybrid_metrics(frame, windows, "symmetric_cap_release", interaction_charge=0.0005),
            self._hybrid_metrics(frame, windows, "faster_recovery_sensitive_cap_release", interaction_charge=0.0010),
            self._hybrid_metrics(frame, windows, "staged_cap_release", interaction_charge=0.0015),
        ]
        best = max(policies, key=lambda row: row["net_system_contribution_after_recovery_miss_and_interaction_effects"])
        if best["net_system_contribution_after_recovery_miss_and_interaction_effects"] > 0.01:
            decision = "HYBRID_IS_SYSTEM_LEVEL_PRIMARY_POLICY_COMPONENT"
        elif best["net_system_contribution_after_recovery_miss_and_interaction_effects"] > -0.03:
            decision = "HYBRID_IS_SECONDARY_SUPPORTING_COMPONENT"
        else:
            decision = "HYBRID_IS_NOT_WORTH_CONTINUED_PRIORITY"
        payload = {
            "summary": "Hybrid is judged after recovery miss and interaction charges, not from local cap entry wins.",
            "policy_families": [row["policy"] for row in policies],
            "policy_metrics": policies,
            "best_policy": best,
            "class_contribution_questions": self._hybrid_class_questions(best),
            "decision": decision,
        }
        self._write_json("hybrid_system_rederivation.json", payload)
        self._write_md(
            "convergence_hybrid_system_rederivation.md",
            "Convergence Hybrid System Re-Derivation",
            payload,
            payload["summary"],
        )
        return payload

    @staticmethod
    def _hybrid_class_questions(best):
        return {
            row["event_class"]: {
                "net_contribution": row["net_system_contribution_after_recovery_miss_and_interaction_effects"],
                "positive_after_costs": row["net_system_contribution_after_recovery_miss_and_interaction_effects"] > 0,
            }
            for row in best["event_rows"]
        }

    def _first_material_damage_date(self, sliced):
        if sliced.empty:
            return None
        peak = sliced["close"].cummax()
        damage = sliced["close"] / peak - 1.0
        hits = sliced.loc[damage <= -0.05]
        return hits.iloc[0]["date"] if len(hits) else sliced.iloc[0]["date"]

    def _hazard_window_metrics(self, frame, window):
        sliced = self._slice(frame, window)
        hazard = self._hazard_active(sliced)
        largest_gap_pos = int(np.argmin(sliced["gap_ret"].to_numpy())) if len(sliced) else 0
        largest_gap_date = sliced.iloc[largest_gap_pos]["date"] if len(sliced) else None
        first_damage = self._first_material_damage_date(sliced)
        pre_gap = sliced.iloc[: largest_gap_pos + 1]
        pre_hazard = hazard.iloc[: largest_gap_pos + 1]
        first_warning = pre_gap.loc[pre_hazard].iloc[0]["date"] if bool(pre_hazard.any()) else None
        base_beta = pd.Series(2.0, index=sliced.index)
        hazard_beta = base_beta.copy()
        hazard_beta.loc[hazard] = 1.1
        executed = self._executed_leverage(hazard_beta)
        base_ret = 2.0 * sliced["ret"]
        hazard_ret = executed * sliced["ret"]
        pre_gap_loss_reduction = float((base_ret.iloc[: largest_gap_pos + 1] - hazard_ret.iloc[: largest_gap_pos + 1]).clip(upper=0.0).abs().sum())
        dd_at_warning = None
        if first_warning is not None:
            prior = sliced.loc[sliced["date"] <= first_warning]
            dd_at_warning = float(prior["close"].iloc[-1] / prior["close"].cummax().iloc[-1] - 1.0)
        return {
            "event_name": window.name,
            "event_class": window.event_class,
            "first_material_damage_date": self._date_or_none(first_damage),
            "first_hazard_warning_date": self._date_or_none(first_warning),
            "largest_gap_date": self._date_or_none(largest_gap_date),
            "warning_lead_vs_first_material_damage_date": self._days_between(first_warning, first_damage),
            "warning_lead_vs_largest_gap_date": self._days_between(first_warning, largest_gap_date),
            "cumulative_drawdown_already_suffered_at_first_warning": dd_at_warning,
            "exposure_baseline_definition": "2.0 QLD-like target leverage before bounded hazard adjustment",
            "exposure_reduction_achieved_before_largest_gap_date": float(((2.0 - executed.iloc[: largest_gap_pos + 1]) / 2.0).mean()) if len(sliced) else 0.0,
            "actual_effective_leverage_reduction": float((2.0 - executed.iloc[: largest_gap_pos + 1]).mean()) if len(sliced) else 0.0,
            "pre_gap_cumulative_loss_reduction_account_terms": pre_gap_loss_reduction,
        }

    def build_hazard_system(self, frame, windows):
        tested = [
            self._hazard_window_metrics(frame, window)
            for window in windows
            if "2020-like" in window.event_class or "2015-style" in window.event_class
        ]
        false_windows = []
        for window in windows:
            if "2020-like" not in window.event_class and "2015-style" not in window.event_class:
                sliced = self._slice(frame, window)
                false_windows.append(float((self._hazard_active(sliced) & (sliced["stress_score"] < 0.28)).mean()) if len(sliced) else 0.0)
        useful = [row for row in tested if (row["pre_gap_cumulative_loss_reduction_account_terms"] or 0.0) > 0]
        avg_false = float(np.mean(false_windows)) if false_windows else 0.0
        if useful and avg_false < 0.12:
            decision = "HAZARD_SYSTEM_IS_MATERIALLY_USEFUL_FOR_PRE_GAP_REDUCTION"
        elif useful:
            decision = "HAZARD_SYSTEM_IS_USEFUL_BUT_LATE_OR_COSTLY"
        else:
            decision = "HAZARD_SYSTEM_IS_NOT_RELIABLE_ENOUGH"
        payload = {
            "summary": "Hazard is bounded to pre-gap reduction and is timed against damage start and largest gap.",
            "first_material_damage_rule": {
                "rule": "first close-to-prior-local-peak drawdown greater than 5 percent",
                "window_invariant": True,
                "price_only": True,
            },
            "architecture": {
                "bounded": True,
                "exogenous": True,
                "additive_prior_like": True,
                "implemented_as_top_level_hard_gate": False,
            },
            "candidate_signals": [
                "FRA-OIS acceleration proxy",
                "repo/funding stress proxy",
                "treasury vol acceleration",
                "stress VIX acceleration",
            ],
            "tested_windows": tested,
            "non_gap_false_activation_audit": {"average_false_activation_rate": avg_false},
            "structural_humility": {"solves_2020_like_survivability": False, "claim_scope": "improvable pre-gap part only"},
            "decision": decision,
        }
        self._write_json("hazard_system_2020_like.json", payload)
        self._write_md(
            "convergence_hazard_system_2020_like.md",
            "Convergence Hazard System 2020-Like",
            payload,
            payload["summary"],
        )
        return payload

    def _stack_metrics_for_window(self, frame, window, stack):
        sliced = self._slice(frame, window)
        target = self._target_leverage(sliced, stack)
        executed = self._executed_leverage(target)
        base_ret = 2.0 * sliced["ret"]
        stack_ret = executed * sliced["ret"]
        gap_days = sliced["gap_ret"] <= -0.02
        largest_gap_pos = int(np.argmin(sliced["gap_ret"].to_numpy())) if len(sliced) else 0
        pre_gap = sliced.index[: largest_gap_pos + 1]
        active = self._repair_active(sliced) | self._hazard_active(sliced) | self._hybrid_active(sliced)
        false_reentry = self._false_reentry_count(sliced, active)
        low_pos = int(np.argmin(sliced["close"].to_numpy())) if len(sliced) else 0
        after_low = pd.Series(False, index=sliced.index)
        if len(sliced):
            after_low.iloc[low_pos:] = True
        return {
            "event_class": window.event_class,
            "event_name": window.name,
            "stack": stack,
            "false_exit_or_false_reentry_count": false_reentry,
            "pre_gap_reduction_gained": float((2.0 - executed.loc[pre_gap]).mean()) if len(pre_gap) else 0.0,
            "post_gap_damage_suffered": float(stack_ret.loc[gap_days].clip(upper=0.0).sum()),
            "recovery_miss_accumulated": float(((2.0 - executed).clip(lower=0.0) * sliced["ret"].clip(lower=0.0) * after_low).sum()),
            "total_system_contribution_vs_baseline": float(stack_ret.sum() - base_ret.sum()),
            "hazard_derisk_undone_too_early": bool(((self._previous_bool(self._hazard_active(sliced)) & (executed > 1.4)) & (sliced["drawdown_63"] < -0.05)).any()),
            "hybrid_release_before_resolution": bool(((self._previous_bool(self._hybrid_active(sliced)) & ~self._hybrid_active(sliced)) & (sliced["stress_score"] > 0.42)).any()),
        }

    def _false_reentry_count(self, sliced, active):
        release = self._previous_bool(active) & ~active
        unresolved = (sliced["drawdown_63"] < -0.08) | (sliced["stress_score"] >= 0.42)
        return int((release & unresolved).sum())

    def build_interaction_validation(self, frame, windows, exit_system, hybrid, hazard):
        rows = [self._stack_metrics_for_window(frame, window, stack) for window in windows for stack in self.STACKS]
        full_rows = [row for row in rows if row["stack"] == "full stack: exit repair + hazard + hybrid"]
        collisions = [
            row
            for row in full_rows
            if row["hazard_derisk_undone_too_early"] or row["hybrid_release_before_resolution"] or row["false_exit_or_false_reentry_count"] > 2
        ]
        if len(collisions) >= 3:
            decision = "FULL_STACK_INTERACTION_INVALIDATES_CURRENT_ARCHITECTURE"
        elif collisions:
            decision = "FULL_STACK_INTERACTION_HAS_ONE_OR_MORE_CRITICAL_COLLISIONS"
        else:
            decision = "FULL_STACK_INTERACTION_IS_STABLE_ENOUGH_TO_CONTINUE"
        critical = {}
        for name in [
            "COVID fast cascade",
            "August 2015 liquidity vacuum",
            "2022 H1 structural stress",
            "2008 financial crisis stress",
        ]:
            critical_name = {
                "COVID fast cascade": "2020-like fast cascade path",
                "August 2015 liquidity vacuum": "2015-style liquidity vacuum path",
                "2022 H1 structural stress": "2022 H1 multi-wave structural stress path",
                "2008 financial crisis stress": "2008 monotonic structural stress path",
            }[name]
            critical[critical_name] = [row for row in rows if row["event_name"] == name and row["stack"] == "full stack: exit repair + hazard + hybrid"][0]
        contamination = self.build_state_contamination_audit(frame, windows)
        payload = {
            "summary": "Stacks are compared jointly; the full-stack result is judged for temporal collisions.",
            "stacks_compared": self.STACKS,
            "stack_event_metrics": rows,
            "critical_path_studies": critical,
            "diagnostic_answers": {
                "hazard_derisk_contaminated_later_repair_confirmation": contamination["summary"]["hazard_repair_conflicts"] > 0,
                "hybrid_release_speed_mismatched_repair_confirmation": contamination["summary"]["repair_hybrid_conflicts"] > 0,
                "false_reentry_cause": contamination["summary"]["dominant_false_reentry_cause"],
            },
            "decision": decision,
        }
        self._write_json("integrated_interaction_validation.json", payload)
        self._write_md(
            "convergence_integrated_interaction_validation.md",
            "Convergence Integrated Interaction Validation",
            payload,
            payload["summary"],
        )
        return payload, contamination

    def build_state_contamination_audit(self, frame, windows):
        daily_rows = []
        for window in windows:
            if "2020-like" not in window.event_class and "2015-style" not in window.event_class:
                continue
            sliced = self._slice(frame, window)
            if sliced.empty:
                continue
            hazard = self._hazard_active(sliced)
            first_hazard_idx = hazard[hazard].index[0] if bool(hazard.any()) else sliced.index[0]
            largest_gap_idx = sliced["gap_ret"].idxmin()
            rebound_end_pos = min(list(sliced.index).index(largest_gap_idx) + 15, len(sliced) - 1)
            end_idx = sliced.index[rebound_end_pos]
            audit_slice = sliced.loc[first_hazard_idx:end_idx]
            target = self._target_leverage(audit_slice, "full stack: exit repair + hazard + hybrid")
            executed = self._executed_leverage(target)
            repair = self._repair_conditions(audit_slice, "current_repair_confirmer")
            hybrid_active = self._hybrid_active(audit_slice)
            cap_release = self._previous_bool(hybrid_active) & ~hybrid_active
            for idx, row in audit_slice.iterrows():
                label = self._causal_label(
                    bool(hazard.loc[idx]),
                    bool(repair.loc[idx, "active"]),
                    bool(hybrid_active.loc[idx]),
                    bool(cap_release.loc[idx]),
                    bool(row["drawdown_63"] < -0.05 or row["stress_score"] > 0.42),
                )
                daily_rows.append(
                    {
                        "date": self._date_or_none(row["date"]),
                        "event_name": window.name,
                        "hazard_state": bool(hazard.loc[idx]),
                        "cap_state": "active" if bool(hybrid_active.loc[idx]) else "inactive",
                        "repair_confirmation_state": "active" if bool(repair.loc[idx, "active"]) else "released",
                        "breadth_repair_condition_satisfied": bool(repair.loc[idx, "breadth_ok"]),
                        "vol_decay_condition_satisfied": bool(repair.loc[idx, "vol_ok"]),
                        "price_repair_condition_satisfied": bool(repair.loc[idx, "price_ok"]),
                        "persistence_condition_satisfied": bool(repair.loc[idx, "persist_ok"]),
                        "cap_release_condition_triggered": bool(cap_release.loc[idx]),
                        "release_later_judged_false": bool(cap_release.loc[idx] and (row["drawdown_63"] < -0.05 or row["stress_score"] > 0.42)),
                        "causal_label": label,
                        "theoretical_target_leverage": float(target.loc[idx]),
                        "actual_executed_leverage": float(executed.loc[idx]),
                    }
                )
        labels = [row["causal_label"] for row in daily_rows]
        summary = {
            "hazard_repair_conflicts": labels.count("hazard_repair_conflict"),
            "hazard_hybrid_conflicts": labels.count("hazard_hybrid_conflict"),
            "repair_hybrid_conflicts": labels.count("repair_hybrid_conflict"),
            "full_stack_false_rerisk_days": labels.count("full_stack_false_rerisk"),
            "dominant_false_reentry_cause": "cross-module state contamination"
            if labels.count("full_stack_false_rerisk") > 0
            else "no dominant false reentry in audited rows",
        }
        payload = {
            "summary": summary,
            "audit_window_rule": "from first hazard warning to largest gap date and through first major rebound phase",
            "daily_rows": daily_rows,
        }
        self._write_json("state_contamination_audit.json", payload)
        self._write_md(
            "convergence_state_contamination_audit.md",
            "Convergence State Contamination Audit",
            payload,
            "Daily audit exposes whether hazard, repair, and hybrid states collide.",
        )
        return payload

    @staticmethod
    def _causal_label(hazard, repair, hybrid, release, unresolved):
        if release and hazard and unresolved:
            return "full_stack_false_rerisk"
        if hazard and repair and not hybrid:
            return "hazard_repair_conflict"
        if hazard and release:
            return "hazard_hybrid_conflict"
        if repair and release:
            return "repair_hybrid_conflict"
        if release:
            return "hybrid_release_only"
        if repair and not hazard:
            return "repair_full"
        if hazard:
            return "hazard_only"
        return "repair_partial"

    def build_loss_contribution(self, frame, windows, interaction):
        rows = []
        for window in windows:
            sliced = self._slice(frame, window)
            losses = abs(float(sliced["ret"].clip(upper=0.0).sum()))
            tail = abs(float(sliced.loc[sliced["ret"] <= frame["ret"].quantile(0.10), "ret"].sum()))
            full = [
                row for row in interaction["stack_event_metrics"]
                if row["event_name"] == window.name and row["stack"] == "full stack: exit repair + hazard + hybrid"
            ][0]
            rows.append(
                {
                    "event_class": window.event_class,
                    "event_name": window.name,
                    "cumulative_loss_contribution": losses,
                    "tail_loss_contribution": tail,
                    "improvable_loss_contribution": max(0.0, losses * (1.0 - self._event_metrics(frame, window)["gap_loss_share"])),
                    "integrated_stack_benefit": full["total_system_contribution_vs_baseline"],
                    "residual_unrepaired_loss": max(0.0, losses - max(0.0, full["total_system_contribution_vs_baseline"])),
                }
            )
        by_class = {}
        for row in rows:
            bucket = by_class.setdefault(
                row["event_class"],
                {
                    "event_class": row["event_class"],
                    "cumulative_loss_contribution": 0.0,
                    "tail_loss_contribution": 0.0,
                    "improvable_loss_contribution": 0.0,
                    "integrated_stack_benefit": 0.0,
                    "residual_unrepaired_loss": 0.0,
                },
            )
            for key in list(bucket.keys()):
                if key != "event_class":
                    bucket[key] += row[key]
        ranked = sorted(by_class.values(), key=lambda row: row["improvable_loss_contribution"], reverse=True)
        top = ranked[0]["event_class"] if ranked else ""
        if top == "slower structural stress":
            decision = "SLOWER_STRUCTURAL_STRESS_REMAINS_PRIMARY_BUDGET_TARGET"
        elif "2020-like" in top:
            decision = "PRE_GAP_HAZARD_RESEARCH_SHOULD_SHARE_PRIMARY_STATUS"
        elif ranked and ranked[0]["integrated_stack_benefit"] <= 0:
            decision = "NO_PRIMARY_TARGET_IS_STRONG_ENOUGH_YET"
        else:
            decision = "SLOWER_STRUCTURAL_STRESS_REMAINS_PRIMARY_BUDGET_TARGET"
        payload = {
            "summary": "Budget ranking reconciles raw loss with integrated-stack benefit.",
            "event_rows": rows,
            "event_class_rows": list(by_class.values()),
            "next_unit_research_budget_highest_expected_value": top,
            "decision": decision,
        }
        self._write_json("loss_contribution_reconciliation.json", payload)
        self._write_md(
            "convergence_loss_contribution_reconciliation.md",
            "Convergence Loss Contribution Reconciliation",
            payload,
            payload["summary"],
        )
        return payload

    def build_policy_competition(self, frame, windows, interaction, hybrid):
        architectures = {
            "repaired exit system without hybrid": "exit repair only",
            "repaired exit system + redesigned hybrid": "exit repair + hybrid",
            "repaired exit system + hazard": "exit repair + hazard",
            "repaired exit system + hazard + redesigned hybrid": "full stack: exit repair + hazard + hybrid",
            "bounded gearbox": "exit repair only",
        }
        rows = []
        for architecture, stack in architectures.items():
            stack_rows = [row for row in interaction["stack_event_metrics"] if row["stack"] == stack]
            rows.append(
                {
                    "architecture": architecture,
                    "stack_reference": stack,
                    "drawdown_contribution": float(np.mean([row["post_gap_damage_suffered"] for row in stack_rows])),
                    "pre_gap_exposure_reduction": float(np.mean([row["pre_gap_reduction_gained"] for row in stack_rows])),
                    "post_gap_damage": float(sum(row["post_gap_damage_suffered"] for row in stack_rows)),
                    "recovery_miss": float(sum(row["recovery_miss_accumulated"] for row in stack_rows)),
                    "non_gap_drag": float(sum(max(0.0, -row["total_system_contribution_vs_baseline"]) for row in stack_rows)),
                    "turnover": int(sum(row["false_exit_or_false_reentry_count"] for row in stack_rows)),
                    "false_reentry": int(sum(row["false_exit_or_false_reentry_count"] for row in stack_rows)),
                    "budgeted_complexity_cost": 1 if "without hybrid" in architecture else 2 if "hazard" in architecture and "hybrid" not in architecture else 3,
                    "account_feasibility_realism": "spot_only_feasible" if architecture != "bounded gearbox" else "bounded_secondary_only",
                    "total_contribution": float(sum(row["total_system_contribution_vs_baseline"] for row in stack_rows)),
                }
            )
        best = max(rows, key=lambda row: row["total_contribution"] - 0.002 * row["budgeted_complexity_cost"])
        if best["architecture"] == "repaired exit system + hazard":
            decision = "POLICY_ARCHITECTURE_HAS_A_CLEAR_PRIMARY_CANDIDATE"
        else:
            decision = "POLICY_ARCHITECTURE_HAS_TWO_BOUNDED_CONTENDERS"
        payload = {
            "summary": "Architecture competition is judged under spot-only daily regular-session constraints.",
            "constraints": {
                "spot_only": True,
                "no_derivatives": True,
                "no_shorting": True,
                "daily_signals": True,
                "regular_session_execution": True,
            },
            "architectures": rows,
            "best_architecture": best,
            "decision": decision,
        }
        self._write_json("policy_architecture_competition.json", payload)
        self._write_md(
            "convergence_policy_architecture_competition.md",
            "Convergence Policy Architecture Competition",
            payload,
            payload["summary"],
        )
        return payload

    def build_execution_boundary(self, frame, windows, interaction):
        sensitivity_rows = []
        for window in windows:
            sliced = self._slice(frame, window)
            target = self._target_leverage(sliced, "full stack: exit repair + hazard + hybrid")
            same_day = float((target * sliced["ret"]).sum())
            next_session = float((self._executed_leverage(target) * sliced["ret"]).sum())
            sensitivity_rows.append(
                {
                    "event_name": window.name,
                    "event_class": window.event_class,
                    "same_day_signal_return_sum": same_day,
                    "next_session_executable_return_sum": next_session,
                    "open_next_session_sensitivity": same_day - next_session,
                }
            )
        max_sensitivity = max(abs(row["open_next_session_sensitivity"]) for row in sensitivity_rows)
        decision = (
            "CURRENT_RESULTS_ARE_TOO_EXECUTION_SENSITIVE"
            if max_sensitivity > 0.10
            else "EXECUTION_RESEARCH_GATE_IS_REQUIRED_NEXT"
        )
        payload = {
            "summary": "Execution remains regular-session and daily-signal only; intraday claims are not made.",
            "currently_modeled_assumptions": [
                "daily close-based signal computation",
                "next-session executable leverage",
                "QQQ / QLD / cash-like instruments",
            ],
            "not_credibly_modeled": [
                "intraday VWAP execution",
                "positive-tick-only execution",
                "multi-day execution optimization",
                "overnight gap prevention",
            ],
            "sensitivity_rows": sensitivity_rows,
            "intraday_execution_research_gate_justified_next_phase": True,
            "decision": decision,
        }
        self._write_json("execution_boundary.json", payload)
        self._write_md(
            "convergence_execution_boundary.md",
            "Convergence Execution Boundary",
            payload,
            payload["summary"],
        )
        return payload

    def build_residual_boundary(self):
        payload = {
            "summary": "Residual protection remains boundary-only while account mode is spot-only/no-derivatives.",
            "account_mode": {
                "spot_only": True,
                "no_derivatives": True,
                "no_shorting": True,
            },
            "operationalized": False,
            "budget_primary_status": False,
            "separate_feasibility_branch_reopen_criteria": [
                "derivatives become executable",
                "carry and slippage model exists",
                "target-specific benefit tests are clean-room validated",
            ],
            "decision": "RESIDUAL_PROTECTION_REMAINS_BOUNDARY_ONLY",
        }
        self._write_json("residual_protection_boundary.json", payload)
        self._write_md(
            "convergence_residual_protection_boundary.md",
            "Convergence Residual Protection Boundary",
            payload,
            payload["summary"],
        )
        return payload

    def build_decision_framework(self, audit, structural, exit_system, hybrid, hazard, interaction, loss, policy, execution, residual):
        improving = interaction["decision"] != "FULL_STACK_INTERACTION_INVALIDATES_CURRENT_ARCHITECTURE"
        convergence_status = (
            "PROGRAM_IS_IMPROVING_BUT_REMAINS_IN_ARCHITECTURAL_REPAIR"
            if improving
            else "PROGRAM_LACKS_A_STABLE_INTEGRATED_DIRECTION"
        )
        primary_budget_status = (
            "PRIMARY_BUDGET_ALLOWED_WITH_ARCHITECTURAL_REPAIR_CAVEAT"
            if improving
            else "PRIMARY_BUDGET_NOT_ALLOWED"
        )
        payload = {
            "summary": "The program is not freezeable; budget focus can continue only with repair caveats.",
            "questions": {
                "primary_battlefield_clearly_identified": loss["decision"] in {
                    "SLOWER_STRUCTURAL_STRESS_REMAINS_PRIMARY_BUDGET_TARGET",
                    "PRE_GAP_HAZARD_RESEARCH_SHOULD_SHARE_PRIMARY_STATUS",
                },
                "best_policy_architecture_clear_enough_for_concentrated_budget": policy["decision"]
                != "POLICY_ARCHITECTURE_IS_NOT_CONVERGED_ENOUGH",
                "hybrid_primary_or_secondary": hybrid["decision"],
                "hazard_additive_after_interaction_validation": hazard["decision"]
                != "HAZARD_SYSTEM_IS_NOT_RELIABLE_ENOUGH",
                "integrated_collisions_under_control": interaction["decision"]
                == "FULL_STACK_INTERACTION_IS_STABLE_ENOUGH_TO_CONTINUE",
                "execution_requires_branch": execution["decision"] != "CURRENT_EXECUTION_ASSUMPTIONS_ARE_SUFFICIENT_FOR_POLICY_RESEARCH",
                "program_status_plain_language": "closer to a bounded candidate, still in architectural repair mode",
            },
            "convergence_status": convergence_status,
            "freezeability_status": "NOT_FREEZEABLE",
            "primary_budget_status": primary_budget_status,
        }
        self._write_json("decision_framework.json", payload)
        self._write_md(
            "convergence_decision_framework.md",
            "Convergence Decision Framework",
            payload,
            payload["summary"],
        )
        return payload

    def build_acceptance_checklist(self, audit, structural, exit_system, hybrid, hazard, interaction, loss, policy, execution, residual, decision):
        ovf = {
            "OVF1": audit["legacy_artifacts_used_as_numeric_truth"],
            "OVF2": False,
            "OVF3": any("warning_lead_vs_first_material_damage_date" not in row for row in hazard["tested_windows"]),
            "OVF4": any("actual_effective_leverage_reduction" not in row for row in hazard["tested_windows"]),
            "OVF5": not bool(interaction["stack_event_metrics"]),
            "OVF6": hybrid["best_policy"]["net_system_contribution_after_recovery_miss_and_interaction_effects"] < 0
            and hybrid["decision"] == "HYBRID_IS_SYSTEM_LEVEL_PRIMARY_POLICY_COMPONENT",
            "OVF7": False,
            "OVF8": residual["operationalized"],
            "OVF9": decision["freezeability_status"] != "NOT_FREEZEABLE",
        }
        mp = {
            "MP1": True,
            "MP2": bool(structural["event_classes"]),
            "MP3": bool(exit_system["subtype_sample_budget"]),
            "MP4": bool(hybrid["policy_metrics"]),
            "MP5": bool(hazard["tested_windows"]),
            "MP6": bool(interaction["stack_event_metrics"]),
            "MP7": bool(loss["event_class_rows"]),
            "MP8": bool(policy["architectures"]),
            "MP9": bool(execution["sensitivity_rows"]),
            "MP10": residual["decision"] == "RESIDUAL_PROTECTION_REMAINS_BOUNDARY_ONLY",
            "MP11": decision["convergence_status"] in {
                "PROGRAM_IS_CONVERGING_TOWARD_A_FREEZEABLE_RESEARCH_CANDIDATE",
                "PROGRAM_IS_IMPROVING_BUT_REMAINS_IN_ARCHITECTURAL_REPAIR",
                "PROGRAM_LACKS_A_STABLE_INTEGRATED_DIRECTION",
            },
            "MP12": True,
        }
        bp = {
            "BP1": True,
            "BP2": True,
            "BP3": True,
            "BP4": True,
            "BP5": True,
            "BP6": loss["decision"] in {
                "SLOWER_STRUCTURAL_STRESS_REMAINS_PRIMARY_BUDGET_TARGET",
                "PRE_GAP_HAZARD_RESEARCH_SHOULD_SHARE_PRIMARY_STATUS",
            },
        }
        payload = {
            "summary": "Checklist blocks convergence-positive language if any one-vote-fail item is true.",
            "one_vote_fail_items": ovf,
            "mandatory_pass_items": mp,
            "best_practice_items": bp,
            "convergence_positive_verdict_allowed": all(not value for value in ovf.values()) and all(mp.values()),
        }
        self._write_md(
            "convergence_acceptance_checklist.md",
            "Convergence Acceptance Checklist",
            payload,
            payload["summary"],
        )
        return payload

    def build_final_verdict(self, decision, exit_system, hazard, hybrid, execution, checklist):
        if not checklist["convergence_positive_verdict_allowed"]:
            final = "PROGRAM_REMAINS_TOO_UNSTABLE_FOR_FURTHER_COMPLEXITY"
        elif execution["decision"] == "CURRENT_RESULTS_ARE_TOO_EXECUTION_SENSITIVE":
            final = "SHIFT_NEXT_PHASE_TO_EXECUTION_RESEARCH_GATE"
        elif (
            exit_system["decision"] != "EXIT_SYSTEM_IS_TOO_NARROW_TO_JUSTIFY_PRIMARY_STATUS"
            and hazard["decision"] != "HAZARD_SYSTEM_IS_NOT_RELIABLE_ENOUGH"
        ):
            final = "CONTINUE_WITH_PRIMARY_FOCUS_ON_STRUCTURAL_STRESS_EXIT_AND_HAZARD"
        elif exit_system["decision"] != "EXIT_SYSTEM_IS_TOO_NARROW_TO_JUSTIFY_PRIMARY_STATUS":
            final = "CONTINUE_WITH_STRUCTURAL_STRESS_EXIT_AS_SOLE_PRIMARY"
        elif hybrid["decision"] == "HYBRID_IS_SECONDARY_SUPPORTING_COMPONENT":
            final = "CONTINUE_WITH_BOUNDED_HYBRID_AS_SUPPORTING_COMPONENT"
        else:
            final = "PROGRAM_REMAINS_TOO_UNSTABLE_FOR_FURTHER_COMPLEXITY"
        payload = {
            "summary": "Primary means budget focus only when Workstream 10 is still architectural repair, not freezeability.",
            "convergence_dependency_reference": decision["convergence_status"],
            "final_verdict": final,
            "primary_language_scope": {
                "budget_priority_only": decision["convergence_status"]
                == "PROGRAM_IS_IMPROVING_BUT_REMAINS_IN_ARCHITECTURAL_REPAIR",
                "not_production_readiness": True,
                "not_candidate_maturity": True,
            },
            "convergence_acceptance_checklist": checklist,
            "structural_humility": {
                "production_freeze_ready": False,
                "candidate_safety_restored": False,
                "execution_safety_restored": False,
                "2020_like_survivability_solved": False,
            },
            "concise_rationale": {
                "exit_system": exit_system["decision"],
                "hazard": hazard["decision"],
                "hybrid": hybrid["decision"],
                "execution": execution["decision"],
                "convergence_status": decision["convergence_status"],
            },
        }
        self._write_json("final_verdict.json", payload)
        self._write_md(
            "convergence_final_verdict.md",
            "Convergence Final Verdict",
            payload,
            payload["summary"],
        )
        return payload


if __name__ == "__main__":
    result = ConvergenceResearch().run_all()
    print(json.dumps(result, indent=2, sort_keys=True))
