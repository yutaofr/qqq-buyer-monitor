"""QLD permission gate for binding sell signals and guarded sub-1x re-entry."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


def _clip01(value: float | None) -> float:
    return float(np.clip(float(value or 0.0), 0.0, 1.0))


def _valid_status(result: dict[str, Any] | None) -> bool:
    status = str((result or {}).get("status", "unknown"))
    return status.startswith("success")


@dataclass(frozen=True)
class QLDPermissionDecision:
    qld_allowed: bool
    allow_sub1x_qld: bool
    forced_bucket: str | None
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
        topo_confidence = (
            _clip01(topology_state.get("confidence", 0.0))
            if isinstance(topology_state, dict)
            else _clip01(getattr(topology_state, "confidence", 0.0))
        )
        topo_expected_beta = (
            float(topology_state.get("expected_beta", 0.0) or 0.0)
            if isinstance(topology_state, dict)
            else float(getattr(topology_state, "expected_beta", 0.0) or 0.0)
        )
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

        resonance_action = str(resonance_result.get("action", "HOLD") or "HOLD")
        sell_override_release = (
            self.enable_fundamental_override
            and bool(fundamental_override.get("active", False))
            and topology_recovery
            and risk_ready
            and effective_entropy_ok
        )
        if self.bind_resonance_sell and resonance_action == "SELL_QLD" and not sell_override_release:
            return QLDPermissionDecision(
                qld_allowed=False,
                allow_sub1x_qld=False,
                forced_bucket="QQQ",
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
            )

        return QLDPermissionDecision(
            qld_allowed=True,
            allow_sub1x_qld=allow_sub1x_qld,
            forced_bucket=forced_bucket,
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
