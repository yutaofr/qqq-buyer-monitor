"""QLD permission gate for binding sell signals and guarded sub-1x re-entry."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


def _clip01(value: float | None) -> float:
    return float(np.clip(float(value or 0.0), 0.0, 1.0))


def _coerce_float(value: Any, default: float = 0.0) -> float:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric) or not np.isfinite(float(numeric)):
        return float(default)
    return float(numeric)


def _valid_status(result: dict[str, Any] | None) -> bool:
    status = str((result or {}).get("status", "unknown"))
    return status.startswith("success")


def _topology_metric(topology_state: dict[str, Any] | Any, key: str, default: float = 0.0) -> float:
    if isinstance(topology_state, dict):
        return _coerce_float(topology_state.get(key, default), default)
    return _coerce_float(getattr(topology_state, key, default), default)


def _extract_series(context_df: pd.DataFrame, column: str) -> pd.Series:
    frame = context_df.copy()
    if "observation_date" in frame.columns:
        frame = frame.set_index("observation_date")
    if column not in frame.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").dropna()


def _delta(series: pd.Series, periods: int) -> float:
    if series.shape[0] < periods + 1:
        return 0.0
    return float(series.iloc[-1] - series.iloc[-(periods + 1)])


@dataclass(frozen=True)
class QLDPermissionDecision:
    qld_allowed: bool
    allow_sub1x_qld: bool
    forced_bucket: str | None
    entry_mode: str
    reason_code: str
    reason: str
    resonance_action: str
    relaxed_entry_signal: float
    calm_risk: bool
    effective_entropy_ok: bool
    topology_recovery: bool
    tractor_valid: bool
    sidecar_valid: bool
    tractor_prob: float
    sidecar_prob: float
    fundamental_override: dict[str, Any]
    left_side_kernel: dict[str, Any]
    regime_specific_override: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class QLDPermissionEvaluator:
    """Separate permission layer so QLD availability is auditable and replayable."""

    def __init__(
        self,
        *,
        bind_resonance_sell: bool = True,
        enable_fundamental_override: bool = True,
        enable_sub1x_guard: bool = True,
        calm_risk_threshold: float = 0.05,
        risk_ready_tractor_threshold: float = 0.15,
        risk_ready_sidecar_threshold: float = 0.20,
        sub1x_force_beta_threshold: float = 0.70,
        entropy_threshold: float = 0.72,
        topology_confidence_threshold: float = 0.75,
        topology_expected_beta_threshold: float = 0.80,
        input_quality_threshold: float = 0.75,
        fundamental_score_threshold: float = 0.50,
        override_signal_floor: float = 0.85,
        buy_bonus: float = 0.15,
        enable_left_side_probe: bool = True,
        left_side_entropy_threshold: float = 0.82,
        left_side_tractor_threshold: float = 0.18,
        left_side_sidecar_threshold: float = 0.24,
        left_side_risk_delta_ceiling: float = 0.02,
        left_side_force_beta_threshold: float = 0.62,
        left_side_signal_floor: float = 0.72,
        left_side_damage_threshold: float = 0.45,
        left_side_impulse_threshold: float = 0.18,
        left_side_repair_threshold: float = 0.24,
        left_side_bust_pressure_threshold: float = 0.55,
        left_side_delta_floor: float = 0.0,
        left_side_acceleration_floor: float = -0.002,
        left_side_score_threshold: float = 0.70,
    ):
        self.bind_resonance_sell = bool(bind_resonance_sell)
        self.enable_fundamental_override = bool(enable_fundamental_override)
        self.enable_sub1x_guard = bool(enable_sub1x_guard)
        self.calm_risk_threshold = float(calm_risk_threshold)
        self.risk_ready_tractor_threshold = float(risk_ready_tractor_threshold)
        self.risk_ready_sidecar_threshold = float(risk_ready_sidecar_threshold)
        self.sub1x_force_beta_threshold = float(sub1x_force_beta_threshold)
        self.entropy_threshold = float(entropy_threshold)
        self.topology_confidence_threshold = float(topology_confidence_threshold)
        self.topology_expected_beta_threshold = float(topology_expected_beta_threshold)
        self.input_quality_threshold = float(input_quality_threshold)
        self.fundamental_score_threshold = float(fundamental_score_threshold)
        self.override_signal_floor = float(override_signal_floor)
        self.buy_bonus = float(buy_bonus)
        self.enable_left_side_probe = bool(enable_left_side_probe)
        self.left_side_entropy_threshold = float(left_side_entropy_threshold)
        self.left_side_tractor_threshold = float(left_side_tractor_threshold)
        self.left_side_sidecar_threshold = float(left_side_sidecar_threshold)
        self.left_side_risk_delta_ceiling = float(left_side_risk_delta_ceiling)
        self.left_side_force_beta_threshold = float(left_side_force_beta_threshold)
        self.left_side_signal_floor = float(left_side_signal_floor)
        self.left_side_damage_threshold = float(left_side_damage_threshold)
        self.left_side_impulse_threshold = float(left_side_impulse_threshold)
        self.left_side_repair_threshold = float(left_side_repair_threshold)
        self.left_side_bust_pressure_threshold = float(left_side_bust_pressure_threshold)
        self.left_side_delta_floor = float(left_side_delta_floor)
        self.left_side_acceleration_floor = float(left_side_acceleration_floor)
        self.left_side_score_threshold = float(left_side_score_threshold)

    def evaluate(
        self,
        *,
        context_df: pd.DataFrame,
        baseline_result: dict[str, Any] | None,
        resonance_result: dict[str, Any] | None,
        overlay: dict[str, Any] | None,
        effective_entropy: float,
        topology_state: dict[str, Any] | Any,
        quality_audit: dict[str, Any] | None,
        base_reentry_signal: float,
        target_beta: float,
    ) -> QLDPermissionDecision:
        baseline_result = baseline_result or {}
        resonance_result = resonance_result or {}
        overlay = overlay or {}
        quality_audit = quality_audit or {}

        tractor = dict(baseline_result.get("tractor", {}))
        sidecar = dict(baseline_result.get("sidecar", {}))
        tractor_prob = _clip01(tractor.get("prob", 0.0))
        sidecar_prob = _clip01(sidecar.get("prob", 0.0))
        tractor_delta = _coerce_float(tractor.get("delta_1d", 0.0))
        sidecar_delta = _coerce_float(sidecar.get("delta_1d", 0.0))
        tractor_valid = _valid_status(tractor)
        sidecar_valid = _valid_status(sidecar)

        calm_risk = (
            tractor_valid
            and sidecar_valid
            and tractor_prob <= self.calm_risk_threshold
            and sidecar_prob <= self.calm_risk_threshold
        )
        effective_entropy_ok = float(effective_entropy) <= self.entropy_threshold

        topo_regime = (
            str(topology_state.get("regime", ""))
            if isinstance(topology_state, dict)
            else str(getattr(topology_state, "regime", ""))
        )
        topo_confidence = _clip01(_topology_metric(topology_state, "confidence"))
        topo_expected_beta = _coerce_float(_topology_metric(topology_state, "expected_beta"))
        topology_recovery = (
            topo_regime == "RECOVERY"
            and (
                topo_confidence >= self.topology_confidence_threshold
                or topo_expected_beta >= self.topology_expected_beta_threshold
            )
        )
        risk_ready = (
            tractor_valid
            and sidecar_valid
            and tractor_prob <= self.risk_ready_tractor_threshold
            and sidecar_prob <= self.risk_ready_sidecar_threshold
        )

        fundamental_override = self._evaluate_fundamental_override(
            context_df=context_df,
            quality_audit=quality_audit,
        )
        left_side_kernel = self._evaluate_generic_left_side_kernel(
            topology_state=topology_state,
            effective_entropy=effective_entropy,
            tractor_valid=tractor_valid,
            sidecar_valid=sidecar_valid,
            tractor_prob=tractor_prob,
            sidecar_prob=sidecar_prob,
            tractor_delta=tractor_delta,
            sidecar_delta=sidecar_delta,
        )
        regime_specific_override = self._evaluate_regime_specific_override(
            context_df=context_df,
            overlay=overlay,
            topology_state=topology_state,
            fundamental_override=fundamental_override,
        )

        resonance_action = str(resonance_result.get("action", "HOLD") or "HOLD")
        sell_override_release = (
            self.enable_fundamental_override
            and bool(fundamental_override.get("active", False))
            and topology_recovery
            and risk_ready
            and effective_entropy_ok
        )
        left_side_sell_release = (
            self.enable_left_side_probe
            and bool(left_side_kernel.get("active", False))
            and bool(regime_specific_override.get("active", False))
            and float(target_beta) >= self.left_side_force_beta_threshold
        )
        if (
            self.bind_resonance_sell
            and resonance_action == "SELL_QLD"
            and not (sell_override_release or left_side_sell_release)
        ):
            return QLDPermissionDecision(
                qld_allowed=False,
                allow_sub1x_qld=False,
                forced_bucket="QQQ",
                entry_mode="BLOCKED",
                reason_code="RESONANCE_SELL_BINDING",
                reason="SELL_QLD resonance revoked QLD permission.",
                resonance_action=resonance_action,
                relaxed_entry_signal=0.0,
                calm_risk=calm_risk,
                effective_entropy_ok=effective_entropy_ok,
                topology_recovery=topology_recovery,
                tractor_valid=tractor_valid,
                sidecar_valid=sidecar_valid,
                tractor_prob=tractor_prob,
                sidecar_prob=sidecar_prob,
                fundamental_override=fundamental_override,
                left_side_kernel=left_side_kernel,
                regime_specific_override=regime_specific_override,
            )

        left_side_probe_active = (
            self.enable_left_side_probe
            and not topology_recovery
            and bool(left_side_kernel.get("active", False))
            and bool(regime_specific_override.get("active", False))
        )

        if left_side_probe_active:
            relaxed_entry_signal = max(
                _clip01(base_reentry_signal),
                self.left_side_signal_floor,
            )
            if resonance_action == "BUY_QLD":
                relaxed_entry_signal = _clip01(relaxed_entry_signal + (0.5 * self.buy_bonus))
            forced_bucket = (
                "QLD"
                if float(target_beta) >= self.left_side_force_beta_threshold
                else None
            )
            return QLDPermissionDecision(
                qld_allowed=True,
                allow_sub1x_qld=True,
                forced_bucket=forced_bucket,
                entry_mode="LEFT_SIDE_PROBE",
                reason_code="LEFT_SIDE_PROBE",
                reason="Left-side probe opened on exhaustion plus stage-specific support.",
                resonance_action=resonance_action,
                relaxed_entry_signal=relaxed_entry_signal,
                calm_risk=calm_risk,
                effective_entropy_ok=effective_entropy_ok,
                topology_recovery=topology_recovery,
                tractor_valid=tractor_valid,
                sidecar_valid=sidecar_valid,
                tractor_prob=tractor_prob,
                sidecar_prob=sidecar_prob,
                fundamental_override=fundamental_override,
                left_side_kernel=left_side_kernel,
                regime_specific_override=regime_specific_override,
            )

        if self.enable_sub1x_guard:
            allow_sub1x_qld = all(
                (
                    risk_ready,
                    effective_entropy_ok,
                    topology_recovery,
                    bool(fundamental_override.get("active", False)),
                )
            )
        else:
            allow_sub1x_qld = True

        relaxed_entry_signal = 0.0
        if allow_sub1x_qld:
            relaxed_entry_signal = max(
                _clip01(base_reentry_signal),
                self.override_signal_floor if bool(fundamental_override.get("active", False)) else 0.0,
            )
            if resonance_action == "BUY_QLD":
                relaxed_entry_signal = _clip01(relaxed_entry_signal + self.buy_bonus)
        forced_bucket = (
            "QLD"
            if allow_sub1x_qld and float(target_beta) >= self.sub1x_force_beta_threshold
            else None
        )

        blockers: list[str] = []
        if self.enable_sub1x_guard:
            if not risk_ready:
                blockers.append("risk_not_ready_or_sidecar_invalid")
            if not effective_entropy_ok:
                blockers.append("entropy_too_high")
            if not topology_recovery:
                blockers.append("recovery_topology_not_confirmed")
            if not bool(fundamental_override.get("active", False)):
                blockers.append("fundamental_override_inactive")

        if sell_override_release:
            return QLDPermissionDecision(
                qld_allowed=True,
                allow_sub1x_qld=allow_sub1x_qld,
                forced_bucket=forced_bucket,
                entry_mode="RECOVERY_EXPANSION",
                reason_code="FUNDAMENTAL_OVERRIDE_RELEASE",
                reason="Fundamental override released SELL_QLD under confirmed recovery.",
                resonance_action=resonance_action,
                relaxed_entry_signal=relaxed_entry_signal,
                calm_risk=calm_risk,
                effective_entropy_ok=effective_entropy_ok,
                topology_recovery=topology_recovery,
                tractor_valid=tractor_valid,
                sidecar_valid=sidecar_valid,
                tractor_prob=tractor_prob,
                sidecar_prob=sidecar_prob,
                fundamental_override=fundamental_override,
                left_side_kernel=left_side_kernel,
                regime_specific_override=regime_specific_override,
            )

        return QLDPermissionDecision(
            qld_allowed=True,
            allow_sub1x_qld=allow_sub1x_qld,
            forced_bucket=forced_bucket,
            entry_mode="RECOVERY_EXPANSION" if allow_sub1x_qld and topology_recovery else "BLOCKED",
            reason_code=(
                "SUB1X_QLD_AUTHORIZED"
                if forced_bucket == "QLD"
                else ("SUB1X_READY" if allow_sub1x_qld else "SUB1X_BLOCKED")
            ),
            reason="QLD sub-1x gate open with direct QLD authorization."
            if forced_bucket == "QLD"
            else (
                "QLD sub-1x gate open."
                if allow_sub1x_qld
                else f"QLD sub-1x gate blocked: {', '.join(blockers) or 'guard_disabled'}"
            ),
            resonance_action=resonance_action,
            relaxed_entry_signal=relaxed_entry_signal,
            calm_risk=calm_risk,
            effective_entropy_ok=effective_entropy_ok,
            topology_recovery=topology_recovery,
            tractor_valid=tractor_valid,
            sidecar_valid=sidecar_valid,
            tractor_prob=tractor_prob,
            sidecar_prob=sidecar_prob,
            fundamental_override=fundamental_override,
            left_side_kernel=left_side_kernel,
            regime_specific_override=regime_specific_override,
        )

    def _evaluate_fundamental_override(
        self,
        *,
        context_df: pd.DataFrame,
        quality_audit: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.enable_fundamental_override:
            return {
                "active": True,
                "source_ready": True,
                "score": 1.0,
                "reasons": ["fundamental_override_disabled"],
                "metrics": {},
            }

        fields = dict(quality_audit.get("fields", {}))
        erp_state = dict(fields.get("erp_ttm", {}))
        capex_state = dict(fields.get("core_capex", {}))
        source_ready = all(
            (
                bool(erp_state.get("available", False)),
                bool(capex_state.get("available", False)),
                float(erp_state.get("quality", 0.0) or 0.0) >= self.input_quality_threshold,
                float(capex_state.get("quality", 0.0) or 0.0) >= self.input_quality_threshold,
            )
        )
        if not source_ready:
            return {
                "active": False,
                "source_ready": False,
                "score": 0.0,
                "reasons": ["missing_or_degraded_inputs"],
                "metrics": {},
            }

        frame = context_df.copy()
        if "observation_date" in frame.columns:
            frame = frame.set_index("observation_date")
        erp_series = pd.to_numeric(frame.get("erp_ttm_pct"), errors="coerce").dropna()
        capex_series = pd.to_numeric(frame.get("core_capex_mm"), errors="coerce").dropna()

        if erp_series.shape[0] < 126 or capex_series.shape[0] < 126:
            return {
                "active": False,
                "source_ready": True,
                "score": 0.0,
                "reasons": ["insufficient_history"],
                "metrics": {
                    "erp_obs": int(erp_series.shape[0]),
                    "capex_obs": int(capex_series.shape[0]),
                },
            }

        erp_window = erp_series.tail(252)
        capex_window = capex_series.tail(126)
        capex_fast = float(capex_series.ewm(span=21, min_periods=21).mean().iloc[-1])
        capex_slow = float(capex_series.ewm(span=63, min_periods=63).mean().iloc[-1])
        erp_latest = float(erp_window.iloc[-1])
        erp_delta_21d = float(erp_window.iloc[-1] - erp_window.iloc[-22]) if erp_window.shape[0] >= 22 else 0.0

        checks = {
            "capex_trend": capex_fast > capex_slow,
            "capex_high_percentile": float((capex_window <= capex_window.iloc[-1]).mean()) >= 0.60,
            "erp_not_compressed": float((erp_window <= erp_latest).mean()) >= 0.25,
            "erp_stable": erp_delta_21d >= -0.0015,
        }
        score = float(sum(bool(value) for value in checks.values()) / len(checks))
        reasons = [name for name, passed in checks.items() if not passed]
        active = score >= self.fundamental_score_threshold

        return {
            "active": active,
            "source_ready": True,
            "score": score,
            "reasons": reasons or ["all_checks_passed"],
            "metrics": {
                "capex_fast": capex_fast,
                "capex_slow": capex_slow,
                "erp_latest": erp_latest,
                "erp_delta_21d": erp_delta_21d,
            },
        }

    def _evaluate_generic_left_side_kernel(
        self,
        *,
        topology_state: dict[str, Any] | Any,
        effective_entropy: float,
        tractor_valid: bool,
        sidecar_valid: bool,
        tractor_prob: float,
        sidecar_prob: float,
        tractor_delta: float,
        sidecar_delta: float,
    ) -> dict[str, Any]:
        regime = (
            str(topology_state.get("regime", ""))
            if isinstance(topology_state, dict)
            else str(getattr(topology_state, "regime", ""))
        )
        damage_memory = _topology_metric(topology_state, "damage_memory")
        recovery_impulse = _topology_metric(topology_state, "recovery_impulse")
        repair_persistence = _topology_metric(topology_state, "repair_persistence")
        bust_pressure = _topology_metric(topology_state, "bust_pressure")
        recovery_prob_delta = _topology_metric(topology_state, "recovery_prob_delta")
        recovery_prob_acceleration = _topology_metric(
            topology_state, "recovery_prob_acceleration"
        )

        risk_stabilizing = all(
            (
                tractor_valid,
                sidecar_valid,
                tractor_prob <= self.left_side_tractor_threshold,
                sidecar_prob <= self.left_side_sidecar_threshold,
                tractor_delta <= self.left_side_risk_delta_ceiling,
                sidecar_delta <= self.left_side_risk_delta_ceiling,
            )
        )
        checks = {
            "regime_ok": regime in {"BUST", "LATE_CYCLE"},
            "damage_memory": damage_memory >= self.left_side_damage_threshold,
            "recovery_impulse": recovery_impulse >= self.left_side_impulse_threshold,
            "repair_persistence": repair_persistence >= self.left_side_repair_threshold,
            "recovery_prob_delta": recovery_prob_delta >= self.left_side_delta_floor,
            "recovery_prob_acceleration": (
                recovery_prob_acceleration >= self.left_side_acceleration_floor
            ),
            "bust_pressure_relief": bust_pressure <= self.left_side_bust_pressure_threshold,
            "entropy_contained": float(effective_entropy) <= self.left_side_entropy_threshold,
            "risk_stabilizing": risk_stabilizing,
        }
        score = float(sum(bool(value) for value in checks.values()) / len(checks))
        active = bool(checks["regime_ok"]) and score >= self.left_side_score_threshold
        reasons = [name for name, passed in checks.items() if not passed]
        return {
            "active": active,
            "score": score,
            "reasons": reasons or ["all_checks_passed"],
            "checks": checks,
            "metrics": {
                "damage_memory": damage_memory,
                "recovery_impulse": recovery_impulse,
                "repair_persistence": repair_persistence,
                "bust_pressure": bust_pressure,
                "recovery_prob_delta": recovery_prob_delta,
                "recovery_prob_acceleration": recovery_prob_acceleration,
                "tractor_prob": tractor_prob,
                "sidecar_prob": sidecar_prob,
                "tractor_delta": tractor_delta,
                "sidecar_delta": sidecar_delta,
                "effective_entropy": float(effective_entropy),
            },
        }

    def _evaluate_regime_specific_override(
        self,
        *,
        context_df: pd.DataFrame,
        overlay: dict[str, Any],
        topology_state: dict[str, Any] | Any,
        fundamental_override: dict[str, Any],
    ) -> dict[str, Any]:
        real_yield_series = _extract_series(context_df, "real_yield_10y_pct")
        credit_spread_series = _extract_series(context_df, "credit_spread_bps")
        real_yield_delta_21d = _delta(real_yield_series, 21)
        credit_spread_delta_21d = _delta(credit_spread_series, 21)
        positive_score = _clip01(overlay.get("positive_score", 0.0))
        negative_score = _clip01(overlay.get("negative_score", 0.0))
        bullish_divergence = _topology_metric(topology_state, "bullish_divergence")

        clusters = {
            "fundamental_support": bool(fundamental_override.get("active", False)),
            "macro_relief": (
                real_yield_series.shape[0] >= 22
                and credit_spread_series.shape[0] >= 22
                and real_yield_delta_21d <= 0.05
                and credit_spread_delta_21d <= 0.0
            ),
            "capitulation_reversal": (
                bullish_divergence >= 0.12
                and positive_score >= max(0.60, negative_score + 0.10)
            ),
        }
        score = float(sum(bool(value) for value in clusters.values()) / len(clusters))
        reasons = [name for name, passed in clusters.items() if not passed]
        return {
            "active": any(clusters.values()),
            "score": score,
            "reasons": reasons or ["all_checks_passed"],
            "clusters": clusters,
            "metrics": {
                "real_yield_delta_21d": real_yield_delta_21d,
                "credit_spread_delta_21d": credit_spread_delta_21d,
                "bullish_divergence": bullish_divergence,
                "positive_score": positive_score,
                "negative_score": negative_score,
            },
        }
