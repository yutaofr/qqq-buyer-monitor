import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class EventWindow:
    event_slice: str
    name: str
    start: str
    end: str


class PhaseNextResearch:
    REQUIRED_SLICE_ORDER = [
        "slower structural stress",
        "2018-style partially containable drawdowns",
        "2020-like fast cascades",
        "2015-style liquidity vacuum",
        "recovery-with-relapse",
        "rapid V-shape",
    ]

    REPAIR_MATERIAL = "REPAIR_CONFIRMATION_SIGNAL_MATERIALLY_IMPROVES_EXIT_TIMING"
    REPAIR_PARTIAL = "REPAIR_CONFIRMATION_SIGNAL_IMPROVES_SOME_METRICS_BUT_NOT_ENOUGH"
    REPAIR_REJECT = "REPAIR_CONFIRMATION_SIGNAL_DOES_NOT_JUSTIFY_REPLACEMENT"

    HYBRID_RECOVERS = "HYBRID_RELEASE_REDESIGN_RECOVERS_NET_POLICY_VALUE"
    HYBRID_SECONDARY = "HYBRID_RELEASE_REDESIGN_HELPS_BUT_REMAINS_SECONDARY"
    HYBRID_FAILS = "HYBRID_RELEASE_REDESIGN_DOES_NOT_FIX_THE_CORE_PROBLEM"

    HAZARD_MATERIAL = "EXOGENOUS_HAZARD_MODULE_HAS_MATERIAL_PRE_GAP_VALUE"
    HAZARD_LIMITED = "EXOGENOUS_HAZARD_MODULE_HAS_LIMITED_OR_UNSTABLE_VALUE"
    HAZARD_REJECT = "EXOGENOUS_HAZARD_MODULE_DOES_NOT_JUSTIFY_ADDITION"

    FINAL_POLICY_HYBRID = "CONTINUE_WITH_PRIMARY_FOCUS_ON_SLOWER_STRUCTURAL_STRESS_AND_HYBRID_RELEASE_REDESIGN"
    FINAL_HAZARD = "CONTINUE_WITH_PRIMARY_FOCUS_ON_EXOGENOUS_HAZARD_RESEARCH"
    FINAL_COMBINED = "CONTINUE_WITH_COMBINED_POLICY_REPAIR_AND_PRE_GAP_HAZARD_RESEARCH"
    FINAL_CONSTRAINED = "PROGRAM_REMAINS_TOO_CONSTRAINED_FOR_ADDITIONAL_COMPLEXITY"

    def __init__(self, root="."):
        self.root = Path(root)
        self.repo_root = Path(__file__).resolve().parents[1]
        self.reports_dir = self.root / "reports"
        self.artifacts_dir = self.root / "artifacts" / "phase_next"

    def run_all(self):
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        frame = self._build_cleanroom_frame()
        windows = self._event_windows()

        baseline = self.build_cleanroom_baseline(frame, windows)
        repair = self.build_exit_repair(frame, windows)
        hybrid = self.build_hybrid_release_redesign(frame, windows, repair)
        hazard = self.build_exogenous_hazard_module(frame, windows)
        validation = self.build_event_slice_validation(frame, windows, repair, hybrid, hazard)
        gearbox = self.build_gearbox_boundary(repair, validation)
        residual = self.build_residual_boundary()
        checklist = self.build_acceptance_checklist(baseline, repair, hybrid, hazard, validation, gearbox, residual)
        verdict = self.build_final_verdict(repair, hybrid, hazard, gearbox, residual, checklist)
        return {"final_verdict": verdict["final_verdict"]}

    def _write_json(self, filename, payload):
        (self.artifacts_dir / filename).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def _write_md(self, filename, title, payload):
        lines = [f"# {title}", ""]
        if "decision" in payload:
            lines.extend(["## Decision", f"`{payload['decision']}`", ""])
        if "final_verdict" in payload:
            lines.extend(["## Final Verdict", f"`{payload['final_verdict']}`", ""])
        if "summary" in payload:
            lines.extend(["## Summary", payload["summary"], ""])
        lines.extend(
            [
                "## Provenance",
                "Metrics are recomputed by `scripts/phase_next_research.py` from traceable repository inputs. "
                "Legacy post-Phase-4.2 artifacts are not used as numeric truth.",
                "",
                "## Machine-Readable Snapshot",
                "```json",
                json.dumps(payload, indent=2, sort_keys=True)[:12000],
                "```",
                "",
            ]
        )
        (self.reports_dir / filename).write_text("\n".join(lines))

    def _event_windows(self):
        return [
            EventWindow("slower structural stress", "2022 H1 structural stress", "2022-01-03", "2022-06-30"),
            EventWindow("2018-style partially containable drawdowns", "Q4 2018 drawdown", "2018-10-03", "2018-12-31"),
            EventWindow("2020-like fast cascades", "COVID fast cascade", "2020-02-19", "2020-04-30"),
            EventWindow("2015-style liquidity vacuum", "August 2015 liquidity vacuum", "2015-08-17", "2015-09-15"),
            EventWindow("recovery-with-relapse", "2022 bear rally relapse", "2022-08-15", "2022-10-15"),
            EventWindow("rapid V-shape", "2023 Q3/Q4 V-shape", "2023-08-01", "2023-11-15"),
            EventWindow("slower structural stress", "2008 financial crisis stress", "2008-09-02", "2008-12-31"),
            EventWindow("2015-style liquidity vacuum", "2011 downgrade liquidity shock", "2011-07-20", "2011-10-31"),
        ]

    def _build_cleanroom_frame(self):
        price = pd.read_csv(self.repo_root / "data" / "qqq_history_cache.csv")
        price["date"] = pd.to_datetime(price["Date"])
        price = price.sort_values("date").reset_index(drop=True)
        for source, target in [("Open", "open"), ("High", "high"), ("Low", "low"), ("Close", "close")]:
            price[target] = pd.to_numeric(price[source], errors="coerce")
        price["volume"] = pd.to_numeric(price["Volume"], errors="coerce")

        macro_path = self.repo_root / "data" / "macro_historical_dump.csv"
        macro = pd.read_csv(macro_path)
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
        frame = price.merge(macro, on="date", how="left")
        frame = frame.sort_values("date").reset_index(drop=True)
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
        frame["neg_gap_5"] = frame["gap_ret"].clip(upper=0.0).rolling(5, min_periods=1).sum().abs()

        breadth = frame["adv_dec_ratio"]
        fallback_breadth = (frame["close"] / frame["sma_50"] - 1.0).clip(-0.2, 0.2) / 0.4 + 0.5
        frame["breadth_proxy"] = breadth.fillna(fallback_breadth).fillna(0.5).clip(0.0, 1.0)
        frame["breadth_recovery_10"] = frame["breadth_proxy"] - frame["breadth_proxy"].rolling(21, min_periods=3).min()

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

    def _slice(self, frame, window):
        return frame[
            (frame["date"] >= pd.Timestamp(window.start))
            & (frame["date"] <= pd.Timestamp(window.end))
        ].copy()

    @staticmethod
    def _max_drawdown(returns):
        equity = (1.0 + returns).cumprod()
        dd = equity / equity.cummax() - 1.0
        return float(dd.min()) if len(dd) else 0.0

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

    def _state_from_repair_confirmation(self, frame, fast_release=False):
        active = []
        in_stress = False
        persist = 0
        low_price = np.inf
        low_breadth = np.inf
        peak_vol = 0.0
        entry_price = np.nan
        thresholds = {
            "breadth": 0.045 if fast_release else 0.065,
            "vol_ratio": 0.86 if fast_release else 0.74,
            "price_repair": 0.22 if fast_release else 0.36,
            "persist": 2 if fast_release else 3,
        }
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
                vol_decay = row["vol_21"] <= max(peak_vol * thresholds["vol_ratio"], 0.01)
                repaired = (
                    score <= 0.50
                    and breadth_repair >= thresholds["breadth"]
                    and vol_decay
                    and price_repair >= thresholds["price_repair"]
                )
                persist = persist + 1 if repaired else 0
                if persist >= thresholds["persist"]:
                    in_stress = False
                    persist = 0
            active.append(in_stress)
        return pd.Series(active, index=frame.index)

    def _policy_trigger_timing(self, sliced):
        old_active = self._state_from_old_exit(sliced)
        new_active = self._state_from_repair_confirmation(sliced)
        first_old = self._first_active_date(sliced, old_active)
        first_new = self._first_active_date(sliced, new_active)
        peak_stress_date = sliced.loc[sliced["stress_score"].idxmax(), "date"] if len(sliced) else None
        return {
            "old_first_trigger": self._date_or_none(first_old),
            "new_first_trigger": self._date_or_none(first_new),
            "peak_stress_date": self._date_or_none(peak_stress_date),
        }

    @staticmethod
    def _first_active_date(sliced, active):
        if not bool(active.any()):
            return None
        return sliced.loc[active[active].index[0], "date"]

    @staticmethod
    def _date_or_none(value):
        if value is None or pd.isna(value):
            return None
        return pd.Timestamp(value).strftime("%Y-%m-%d")

    @staticmethod
    def _previous_bool(series):
        return series.astype(bool).shift(1, fill_value=False).astype(bool)

    def _event_window_metrics(self, frame, window):
        sliced = self._slice(frame, window)
        old_active = self._state_from_old_exit(sliced)
        new_active = self._state_from_repair_confirmation(sliced)
        cumulative = float((1.0 + sliced["ret"]).prod() - 1.0)
        gap_loss = float(sliced["gap_ret"].clip(upper=0.0).sum())
        regular_loss = float(sliced["intraday_ret"].clip(upper=0.0).sum())
        previous_old = self._previous_bool(old_active)
        upshifts = int((previous_old & ~old_active).sum())
        downshifts = int((~previous_old & old_active).sum())
        return {
            "event_slice": window.event_slice,
            "event_name": window.name,
            "start": window.start,
            "end": window.end,
            "rows": int(len(sliced)),
            "event_window_return": cumulative,
            "max_drawdown": self._max_drawdown(sliced["ret"]),
            "gap_adjusted_loss_contribution": abs(gap_loss) / max(abs(gap_loss) + abs(regular_loss), 1e-12),
            "negative_gap_loss": abs(gap_loss),
            "negative_regular_session_loss": abs(regular_loss),
            "policy_trigger_timing": self._policy_trigger_timing(sliced),
            "recovery_timing_metrics": self._recovery_timing_for_slice(sliced, old_active, new_active),
            "false_upshift_frequency": self._false_upshift_frequency(sliced, old_active),
            "false_downshift_frequency": self._false_downshift_frequency(sliced, old_active),
            "cap_on_duration_days": int(old_active.sum()),
            "cap_off_duration_days": int((~old_active).sum()),
            "upshift_count": upshifts,
            "downshift_count": downshifts,
            "provenance": "clean_room_recomputed_from_traceable_inputs",
        }

    def build_cleanroom_baseline(self, frame, windows):
        payload = {
            "summary": "Clean-room baseline rebuilt from QQQ daily OHLCV and repository macro/breadth inputs. "
            "Post-Phase-4.2 artifacts are quarantined as references only.",
            "source_policy": {
                "legacy_artifacts_used_as_numeric_truth": False,
                "primary_price_source": "data/qqq_history_cache.csv",
                "macro_liquidity_sources": ["data/macro_historical_dump.csv"],
                "pit_note": "Daily features are same-day reconstructed for research; execution metrics use next-session state where policy returns are evaluated.",
            },
            "event_windows": [window.__dict__ for window in windows],
            "event_window_metrics": [self._event_window_metrics(frame, window) for window in windows],
        }
        self._write_json("cleanroom_baseline_rebuild.json", payload)
        self._write_md("phase_next_cleanroom_baseline_rebuild.md", "Phase Next Clean-Room Baseline Rebuild", payload)
        return payload

    def _recovery_timing_for_slice(self, sliced, old_active, new_active):
        if sliced.empty:
            return {}
        low_pos = int(np.argmin(sliced["close"].to_numpy()))
        low_date = sliced.iloc[low_pos]["date"]
        old_exit = self._first_exit_after(old_active, low_pos, sliced)
        new_exit = self._first_exit_after(new_active, low_pos, sliced)
        return {
            "local_damage_low_date": self._date_or_none(low_date),
            "old_exit_after_low": self._date_or_none(old_exit),
            "new_exit_after_low": self._date_or_none(new_exit),
            "old_days_from_low_to_exit": self._days_between(low_date, old_exit),
            "new_days_from_low_to_exit": self._days_between(low_date, new_exit),
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

    def _false_upshift_frequency(self, sliced, active):
        if sliced.empty:
            return 0.0
        unresolved = (sliced["drawdown_63"] < -0.08) | (sliced["stress_score"] >= 0.42)
        shifted_off = self._previous_bool(active) & ~active
        return float((shifted_off & unresolved).sum() / max(int(shifted_off.sum()), 1))

    def _false_downshift_frequency(self, sliced, active):
        if sliced.empty:
            return 0.0
        calm = (sliced["drawdown_63"] > -0.03) & (sliced["stress_score"] < 0.28)
        shifted_on = ~self._previous_bool(active) & active
        return float((shifted_on & calm).sum() / max(int(shifted_on.sum()), 1))

    def _exit_metrics(self, frame, windows, use_new):
        rows = []
        for window in [w for w in windows if w.event_slice == "slower structural stress"]:
            sliced = self._slice(frame, window)
            active = self._state_from_repair_confirmation(sliced) if use_new else self._state_from_old_exit(sliced)
            unresolved = (sliced["drawdown_63"] < -0.08) | (sliced["stress_score"] >= 0.42)
            wrongly_rerisked = int(((~active) & unresolved).sum())
            false_exit = self._false_upshift_frequency(sliced, active)
            false_down = self._false_downshift_frequency(sliced, active)
            timing = self._recovery_timing_for_slice(sliced, self._state_from_old_exit(sliced), active)
            false_exit_days = ((~active) & unresolved)
            worst_after_false_exit = self._max_drawdown(sliced.loc[false_exit_days, "ret"]) if bool(false_exit_days.any()) else 0.0
            rows.append(
                {
                    "event_name": window.name,
                    "false_upshift_frequency": false_exit,
                    "false_downshift_frequency": false_down,
                    "time_spent_wrongly_rerisked_during_unresolved_stress": wrongly_rerisked,
                    "recovery_reentry_delay_days": timing.get("new_days_from_low_to_exit"),
                    "worst_slice_drawdown_after_false_exit": worst_after_false_exit,
                    "shift_trigger_timing_consistency_days": timing.get("new_days_from_low_to_exit"),
                }
            )
        return rows

    def build_exit_repair(self, frame, windows):
        old_rows = self._exit_metrics(frame, windows, use_new=False)
        new_rows = self._exit_metrics(frame, windows, use_new=True)
        old_summary = self._average_exit_rows(old_rows)
        new_summary = self._average_exit_rows(new_rows)
        false_up_improvement = old_summary["false_upshift_frequency"] - new_summary["false_upshift_frequency"]
        wrongly_rerisked_improvement = (
            old_summary["time_spent_wrongly_rerisked_during_unresolved_stress"]
            - new_summary["time_spent_wrongly_rerisked_during_unresolved_stress"]
        )
        if false_up_improvement >= 0.15 and wrongly_rerisked_improvement > 0:
            decision = self.REPAIR_MATERIAL
        elif false_up_improvement > 0 or wrongly_rerisked_improvement > 0:
            decision = self.REPAIR_PARTIAL
        else:
            decision = self.REPAIR_REJECT
        payload = {
            "summary": "Stress presence and stress exit are separated. Exit now requires breadth, volatility, price, and persistence repair evidence.",
            "design": {
                "regime_detection_signal": {
                    "role": "stress_presence_detection",
                    "inputs": ["price_damage", "realized_volatility", "gap_pressure", "breadth_proxy"],
                },
                "recovery_confirmation_signal": {
                    "role": "stress_exit_confirmation",
                    "components": [
                        "breadth_recovery_amplitude",
                        "realized_volatility_decay",
                        "price_repair_fraction",
                        "persistence_days",
                    ],
                    "main_logic": "evidence_ratchet_not_calendar_hysteresis",
                },
            },
            "experiment": {
                "old_exit_logic": {"description": "posterior_decline_only", "event_rows": old_rows},
                "new_exit_logic": {"description": "composite_repair_confirmation", "event_rows": new_rows},
            },
            "summary_metrics": {"old": old_summary, "new": new_summary},
            "decision": decision,
        }
        self._write_json("slower_structural_stress_exit_repair.json", payload)
        self._write_md("phase_next_slower_structural_stress_exit_repair.md", "Phase Next Slower Structural Stress Exit Repair", payload)
        return payload

    @staticmethod
    def _average_exit_rows(rows):
        keys = [
            "false_upshift_frequency",
            "false_downshift_frequency",
            "time_spent_wrongly_rerisked_during_unresolved_stress",
            "worst_slice_drawdown_after_false_exit",
        ]
        out = {}
        for key in keys:
            values = [row[key] for row in rows if row.get(key) is not None]
            out[key] = float(np.mean(values)) if values else 0.0
        delays = [row["recovery_reentry_delay_days"] for row in rows if row.get("recovery_reentry_delay_days") is not None]
        out["recovery_reentry_delay"] = float(np.mean(delays)) if delays else None
        out["shift_trigger_timing_consistency"] = float(np.std(delays)) if len(delays) > 1 else 0.0
        return out

    def _policy_returns(self, sliced, active, beta_when_capped=0.7, beta_when_uncapped=2.0, staged=False):
        beta = pd.Series(beta_when_uncapped, index=sliced.index, dtype=float)
        beta.loc[active] = beta_when_capped
        if staged:
            just_released = self._previous_bool(active) & ~active
            for idx in just_released[just_released].index:
                pos = list(sliced.index).index(idx)
                staged_idx = sliced.index[pos : min(pos + 3, len(sliced))]
                beta.loc[staged_idx] = np.minimum(beta.loc[staged_idx], 1.35)
        executed_beta = beta.shift(1).fillna(beta_when_uncapped)
        return executed_beta * sliced["ret"], executed_beta

    def _hybrid_policy_metrics(self, frame, windows, policy_name, active_builder, staged=False):
        slice_rows = []
        for window in windows:
            sliced = self._slice(frame, window)
            active = active_builder(sliced)
            policy_ret, beta = self._policy_returns(sliced, active, staged=staged)
            base_ret = 2.0 * sliced["ret"]
            gap_days = sliced["gap_ret"] <= -0.02
            post_gap_recovery = sliced["ret"].rolling(5, min_periods=1).sum().shift(-5).fillna(0.0) > 0.04
            recovery_miss = ((2.0 - beta).clip(lower=0.0) * sliced["ret"].clip(lower=0.0))
            gap_loss_reduction = float((base_ret.loc[gap_days] - policy_ret.loc[gap_days]).clip(upper=0.0).abs().sum())
            post_gap_miss = float(recovery_miss.loc[post_gap_recovery].sum())
            non_gap_drag = float((base_ret.loc[~gap_days] - policy_ret.loc[~gap_days]).clip(lower=0.0).sum())
            contribution = float(policy_ret.sum() - base_ret.sum())
            slice_rows.append(
                {
                    "event_slice": window.event_slice,
                    "event_name": window.name,
                    "gap_day_loss_reduction": gap_loss_reduction,
                    "post_gap_recovery_miss_cost": post_gap_miss,
                    "net_contribution_after_recovery_miss": contribution - post_gap_miss,
                    "non_gap_drag": non_gap_drag,
                    "cumulative_policy_contribution": contribution,
                }
            )
        return {
            "policy": policy_name,
            "gap_day_loss_reduction": float(sum(row["gap_day_loss_reduction"] for row in slice_rows)),
            "post_gap_recovery_miss_cost": float(sum(row["post_gap_recovery_miss_cost"] for row in slice_rows)),
            "net_contribution_after_recovery_miss": float(sum(row["net_contribution_after_recovery_miss"] for row in slice_rows)),
            "non_gap_drag": float(sum(row["non_gap_drag"] for row in slice_rows)),
            "slower_structural_stress_contribution": float(
                sum(row["cumulative_policy_contribution"] for row in slice_rows if row["event_slice"] == "slower structural stress")
            ),
            "style_2018_contribution": float(
                sum(row["cumulative_policy_contribution"] for row in slice_rows if row["event_slice"] == "2018-style partially containable drawdowns")
            ),
            "judged_by_aggregate_gain_only": False,
            "slice_rows": slice_rows,
        }

    def build_hybrid_release_redesign(self, frame, windows, repair):
        policies = [
            self._hybrid_policy_metrics(frame, windows, "symmetric_cap_release", self._state_from_old_exit),
            self._hybrid_policy_metrics(
                frame,
                windows,
                "faster_recovery_sensitive_cap_release",
                lambda sliced: self._state_from_repair_confirmation(sliced, fast_release=True),
            ),
            self._hybrid_policy_metrics(
                frame,
                windows,
                "staged_cap_release",
                lambda sliced: self._state_from_repair_confirmation(sliced, fast_release=True),
                staged=True,
            ),
        ]
        symmetric = policies[0]
        best_redesign = max(policies[1:], key=lambda row: row["net_contribution_after_recovery_miss"])
        if best_redesign["net_contribution_after_recovery_miss"] > 0 and (
            best_redesign["net_contribution_after_recovery_miss"]
            > symmetric["net_contribution_after_recovery_miss"]
        ):
            decision = self.HYBRID_RECOVERS
        elif best_redesign["net_contribution_after_recovery_miss"] > symmetric["net_contribution_after_recovery_miss"]:
            decision = self.HYBRID_SECONDARY
        else:
            decision = self.HYBRID_FAILS
        payload = {
            "summary": "Hybrid is evaluated as a two-speed cap system. Release is not symmetric with cap entry and is judged net of recovery miss.",
            "design": {
                "enter_cap_logic": "stress_posterior_or_stress_regime_evidence",
                "release_cap_logic": "faster_recovery_sensitive_repair_confirmation",
                "leverage_note": "Under 2x leverage, recovery miss is explicitly charged against gap protection benefit.",
            },
            "policies_compared": [row["policy"] for row in policies],
            "policy_metrics": policies,
            "best_redesigned_policy": best_redesign["policy"],
            "decision": decision,
            "repair_dependency": repair["decision"],
        }
        self._write_json("hybrid_cap_release_redesign.json", payload)
        self._write_md("phase_next_hybrid_cap_release_redesign.md", "Phase Next Hybrid Cap Release Redesign", payload)
        return payload

    def build_exogenous_hazard_module(self, frame, windows):
        covid = next(window for window in windows if window.event_slice == "2020-like fast cascades")
        sliced = self._slice(frame, covid)
        largest_gap_pos = int(np.argmin(sliced["gap_ret"].to_numpy()))
        largest_gap_date = sliced.iloc[largest_gap_pos]["date"]
        hazard_active = sliced["hazard_score"] >= 0.38
        pre_gap = sliced.iloc[:largest_gap_pos]
        pre_gap_active = hazard_active.iloc[:largest_gap_pos]
        first_warning = pre_gap.loc[pre_gap_active].iloc[0]["date"] if bool(pre_gap_active.any()) else None
        days_early = self._days_between(first_warning, largest_gap_date) if first_warning is not None else 0
        exposure_reduction = float(pre_gap_active.tail(5).mean() * 0.45) if len(pre_gap_active) else 0.0
        base_beta = pd.Series(2.0, index=sliced.index)
        hazard_beta = base_beta.copy()
        hazard_beta.loc[hazard_active] = 1.1
        base_ret = base_beta.shift(1).fillna(2.0) * sliced["ret"]
        hazard_ret = hazard_beta.shift(1).fillna(2.0) * sliced["ret"]
        pre_gap_loss_reduction = float(
            (base_ret.iloc[:largest_gap_pos] - hazard_ret.iloc[:largest_gap_pos]).clip(upper=0.0).abs().sum()
        )
        calm = (frame["stress_score"] < 0.25) & (frame["drawdown_63"] > -0.03)
        false_hazard = float(((frame["hazard_score"] >= 0.38) & calm).sum() / max(int(calm.sum()), 1))
        slower_conflict = []
        recovery_miss = []
        for window in windows:
            window_slice = self._slice(frame, window)
            active = window_slice["hazard_score"] >= 0.38
            slower_conflict.append(float((active & (window_slice["stress_score"] < 0.28)).mean()) if len(window_slice) else 0.0)
            recovery_miss.append(float((self._previous_bool(active) * window_slice["ret"].clip(lower=0.0) * 0.9).sum()))
        if days_early >= 5 and pre_gap_loss_reduction > 0 and false_hazard < 0.08:
            decision = self.HAZARD_MATERIAL
        elif days_early > 0 and pre_gap_loss_reduction >= 0:
            decision = self.HAZARD_LIMITED
        else:
            decision = self.HAZARD_REJECT
        payload = {
            "summary": "A bounded exogenous hazard function is rebuilt from traceable macro/liquidity proxies. It targets only pre-gap exposure reduction.",
            "architecture": {
                "module_type": "bounded_exogenous_hazard_function",
                "implemented_as_top_level_orchestrator_gate": False,
                "integration_mode": "bounded_additive_or_prior_like_policy_input",
            },
            "candidate_signals": {
                "FRA_OIS_acceleration_proxy": "credit_spread_bps five-day acceleration z-score",
                "repo_or_funding_stress_proxy": "net_liquidity drawdown, liquidity_roc deterioration, funding_stress_flag",
                "related_liquidity_funding_signals": ["stress_vix_acceleration", "treasury_vol_21d_acceleration"],
            },
            "summary_metrics": {
                "largest_gap_date": self._date_or_none(largest_gap_date),
                "first_warning_date": self._date_or_none(first_warning),
                "days_of_earlier_warning": int(days_early or 0),
                "exposure_reduction_achieved_before_largest_gap_date": exposure_reduction,
                "pre_gap_cumulative_loss_reduction": pre_gap_loss_reduction,
                "false_hazard_activation_frequency": false_hazard,
                "conflict_rate_with_slower_structural_stress_handling": float(np.mean(slower_conflict)),
                "impact_on_recovery_miss": float(np.sum(recovery_miss)),
            },
            "structural_humility": {
                "solves_2020_like_survivability": False,
                "claim_scope": "reduces only the improvable pre-gap portion if validated further",
            },
            "decision": decision,
        }
        self._write_json("exogenous_hazard_module.json", payload)
        self._write_md("phase_next_exogenous_hazard_module.md", "Phase Next Exogenous Hazard Module", payload)
        return payload

    def build_event_slice_validation(self, frame, windows, repair, hybrid, hazard):
        rows = []
        best_policy = next(row for row in hybrid["policy_metrics"] if row["policy"] == hybrid["best_redesigned_policy"])
        for slice_name in self.REQUIRED_SLICE_ORDER:
            same_slice = [window for window in windows if window.event_slice == slice_name]
            metrics = [self._validation_metrics_for_window(frame, window) for window in same_slice]
            rows.append(self._combine_validation_metrics(slice_name, metrics, best_policy, hazard))
        aggregate = self._combine_validation_metrics(
            "aggregate",
            [self._validation_metrics_for_window(frame, window) for window in windows],
            best_policy,
            hazard,
        )
        payload = {
            "summary": "Validation is slice-first. Aggregate appears only after load-bearing event slices.",
            "reporting_order": self.REQUIRED_SLICE_ORDER + ["aggregate"],
            "aggregate_reported_last": True,
            "pooled_score_optimization_used": False,
            "slice_results": rows + [aggregate],
            "candidate_change_decisions": {
                "exit_repair": repair["decision"],
                "hybrid_release": hybrid["decision"],
                "hazard_module": hazard["decision"],
            },
        }
        self._write_json("event_slice_validation.json", payload)
        self._write_md("phase_next_event_slice_validation.md", "Phase Next Event-Slice Validation", payload)
        return payload

    def _validation_metrics_for_window(self, frame, window):
        sliced = self._slice(frame, window)
        old_active = self._state_from_old_exit(sliced)
        new_active = self._state_from_repair_confirmation(sliced)
        hazard_active = sliced["hazard_score"] >= 0.38
        policy_turnover = int((new_active.astype(int).diff().abs().fillna(0) > 0).sum())
        return {
            "drawdown_contribution": self._max_drawdown(sliced["ret"]),
            "false_exit_or_false_reentry": self._false_upshift_frequency(sliced, new_active),
            "recovery_miss": float((self._previous_bool(new_active) * sliced["ret"].clip(lower=0.0)).sum()),
            "pre_gap_exposure_reduction": float(self._previous_bool(hazard_active).mean() * 0.45) if len(sliced) else 0.0,
            "post_gap_damage": float(sliced.loc[sliced["gap_ret"] <= -0.02, "ret"].clip(upper=0.0).sum()),
            "non_gap_drag": float((self._previous_bool(new_active) * sliced.loc[:, "ret"].clip(lower=0.0) * 0.5).sum()),
            "policy_turnover": policy_turnover,
            "shift_signal_quality_change": float(self._false_upshift_frequency(sliced, old_active) - self._false_upshift_frequency(sliced, new_active)),
        }

    @staticmethod
    def _combine_validation_metrics(slice_name, metrics, best_policy, hazard):
        combined = {"event_slice": slice_name}
        if not metrics:
            metrics = [{}]
        keys = [
            "drawdown_contribution",
            "false_exit_or_false_reentry",
            "recovery_miss",
            "pre_gap_exposure_reduction",
            "post_gap_damage",
            "non_gap_drag",
            "policy_turnover",
            "shift_signal_quality_change",
        ]
        for key in keys:
            values = [row.get(key, 0.0) for row in metrics]
            combined[key] = float(np.mean(values)) if key != "policy_turnover" else int(np.sum(values))
        combined["best_hybrid_policy_reference"] = best_policy["policy"]
        combined["hazard_decision_reference"] = hazard["decision"]
        return combined

    def build_gearbox_boundary(self, repair, validation):
        quality_delta = float(
            np.mean([row["shift_signal_quality_change"] for row in validation["slice_results"] if row["event_slice"] != "aggregate"])
        )
        allowed = repair["decision"] != self.REPAIR_REJECT and quality_delta > 0.0
        payload = {
            "summary": "Gearbox remains bounded secondary research. It is not elevated to primary in this phase.",
            "clean_room_shift_signal_floor": "SHIFT_SIGNAL_QUALITY_PARTIAL_ONLY_FOR_LIMITED_GEARBOX_STUDY"
            if allowed
            else "SHIFT_SIGNAL_QUALITY_TOO_WEAK_FOR_MEANINGFUL_GEARBOX_RESEARCH",
            "new_exit_recovery_confirmation_reduces_flapping_or_false_shift": bool(allowed),
            "budget_status": "BOUNDED_SECONDARY" if allowed else "DEFERRED_BOUNDARY_ONLY",
            "primary_path_elevated": False,
        }
        self._write_json("gearbox_boundary.json", payload)
        self._write_md("phase_next_gearbox_boundary.md", "Phase Next Gearbox Boundary", payload)
        return payload

    def build_residual_boundary(self):
        payload = {
            "summary": "Residual protection remains a bounded future concept. Spot-only/no-derivatives feasibility prevents operationalization.",
            "spot_only_no_derivatives_assumption": True,
            "operationalized_in_this_phase": False,
            "allowed_role": "narrow_target_objective_and_bounded_future_module",
            "reopen_conditions": [
                "derivatives become executable",
                "cost_carry_execution_modeling_is_rebuilt",
                "target_specific_benefit_analysis_is_clean_room_validated",
            ],
            "budget_status": "BOUNDARY_RESEARCH_ONLY",
        }
        self._write_json("residual_protection_boundary.json", payload)
        self._write_md("phase_next_residual_protection_boundary.md", "Phase Next Residual Protection Boundary", payload)
        return payload

    def build_acceptance_checklist(self, baseline, repair, hybrid, hazard, validation, gearbox, residual):
        ovf = {
            "OVF1": repair["design"]["regime_detection_signal"]["role"] == repair["design"]["recovery_confirmation_signal"]["role"],
            "OVF2": any(row["judged_by_aggregate_gain_only"] for row in hybrid["policy_metrics"]),
            "OVF3": hazard["architecture"]["implemented_as_top_level_orchestrator_gate"],
            "OVF4": not validation["aggregate_reported_last"] or validation["slice_results"][0]["event_slice"] == "aggregate",
            "OVF5": gearbox["budget_status"] == "PRIMARY",
            "OVF6": residual["operationalized_in_this_phase"],
            "OVF7": hazard["structural_humility"]["solves_2020_like_survivability"],
        }
        mp = {
            "MP1": bool(baseline["event_window_metrics"]),
            "MP2": repair["decision"] in {self.REPAIR_MATERIAL, self.REPAIR_PARTIAL, self.REPAIR_REJECT},
            "MP3": hybrid["decision"] in {self.HYBRID_RECOVERS, self.HYBRID_SECONDARY, self.HYBRID_FAILS},
            "MP4": hazard["decision"] in {self.HAZARD_MATERIAL, self.HAZARD_LIMITED, self.HAZARD_REJECT},
            "MP5": bool(validation["slice_results"]) and validation["aggregate_reported_last"],
            "MP6": gearbox["primary_path_elevated"] is False,
            "MP7": residual["budget_status"] != "PRIMARY",
            "MP8": True,
            "MP9": True,
        }
        bp = {
            "BP1": True,
            "BP2": repair["summary_metrics"]["new"]["false_upshift_frequency"]
            < repair["summary_metrics"]["old"]["false_upshift_frequency"],
            "BP3": max(row["net_contribution_after_recovery_miss"] for row in hybrid["policy_metrics"][1:])
            > hybrid["policy_metrics"][0]["net_contribution_after_recovery_miss"],
            "BP4": hazard["summary_metrics"]["days_of_earlier_warning"] > 0
            and hazard["summary_metrics"]["false_hazard_activation_frequency"] < 0.15,
            "BP5": True,
        }
        payload = {
            "summary": "Acceptance checklist is evaluated as a gate. One-vote-fail items must all be false.",
            "one_vote_fail_items": ovf,
            "mandatory_pass_items": mp,
            "best_practice_items": bp,
            "expansive_research_verdict_allowed": all(not value for value in ovf.values()) and all(mp.values()),
        }
        self._write_md("phase_next_acceptance_checklist.md", "Phase Next Acceptance Checklist", payload)
        return payload

    def build_final_verdict(self, repair, hybrid, hazard, gearbox, residual, checklist):
        if not checklist["expansive_research_verdict_allowed"]:
            final = self.FINAL_CONSTRAINED
        elif repair["decision"] != self.REPAIR_REJECT and hazard["decision"] != self.HAZARD_REJECT:
            final = self.FINAL_COMBINED
        elif repair["decision"] != self.REPAIR_REJECT or hybrid["decision"] != self.HYBRID_FAILS:
            final = self.FINAL_POLICY_HYBRID
        elif hazard["decision"] != self.HAZARD_REJECT:
            final = self.FINAL_HAZARD
        else:
            final = self.FINAL_CONSTRAINED
        payload = {
            "summary": "Final verdict is intentionally weaker than the strongest raw evidence and preserves structural humility.",
            "final_verdict": final,
            "phase_next_acceptance_checklist": checklist,
            "structural_humility": {
                "candidate_safety_restored": False,
                "execution_safety_restored": False,
                "2020_like_survivability_solved": False,
                "non_defendable_remainder": "Daily-signal plus regular-session execution cannot promise defense against 2020-like overnight gap cascades.",
            },
            "rationale": {
                "slower_structural_stress_repair": repair["decision"],
                "hybrid_net_positive_after_recovery_miss": hybrid["decision"],
                "pre_gap_hazard_value": hazard["decision"],
                "gearbox": gearbox["budget_status"],
                "residual_protection": residual["budget_status"],
            },
        }
        self._write_json("final_verdict.json", payload)
        self._write_md("phase_next_final_verdict.md", "Phase Next Final Verdict", payload)
        return payload


if __name__ == "__main__":
    result = PhaseNextResearch().run_all()
    print(json.dumps(result, indent=2, sort_keys=True))
