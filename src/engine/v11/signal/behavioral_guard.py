"""v11 Signal: downstream behavior constraints for execution stability."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from src.engine.v11.core.position_sizer import PositionSizingResult


@dataclass(frozen=True)
class ExecutionDecision:
    target_bucket: str
    target_exposure: str
    action_required: bool
    reason: str
    lock_active: bool
    cooldown_days_remaining: int
    target_beta: float
    raw_target_beta: float
    qqq_dollars: float
    qld_notional_dollars: float
    cash_dollars: float

    def to_dict(self) -> dict:
        return asdict(self)


class BehavioralGuard:
    """Apply execution stability after continuous sizing without hard-coded deadbands."""

    _BUCKET_ORDER = {"CASH": 0, "QQQ": 1, "QLD": 2}
    _BOUNDARIES = (0.5, 1.0)

    def __init__(
        self,
        *,
        initial_bucket: str = "QQQ",
        settlement_days: int = 1,
        evidence: float = 0.0,
    ):
        self.current_bucket = initial_bucket
        self.settlement_days = settlement_days
        self.cooldown_days_remaining = 0
        self.last_target_beta: float | None = None
        self.evidence = float(evidence)

    def apply(
        self,
        sizing: PositionSizingResult,
        *,
        forced_bucket: str | None = None,
        forced_reason: str | None = None,
        kill_switch_active: bool = False,
    ) -> ExecutionDecision:
        previous_bucket = self.current_bucket

        if kill_switch_active and self.current_bucket != "QLD":
            self.current_bucket = "QLD"
            self.cooldown_days_remaining = 30
            self.last_target_beta = sizing.target_beta
            self.evidence = 0.0
            return self._decision(
                previous_bucket,
                sizing,
                reason="RESURRECTION: probabilistic guard released QLD.",
                lock_active=False,
            )

        if self.cooldown_days_remaining > 0:
            remaining = self.cooldown_days_remaining
            self.cooldown_days_remaining -= 1
            self.last_target_beta = sizing.target_beta
            self.evidence = 0.0
            return ExecutionDecision(
                target_bucket=self.current_bucket,
                target_exposure=self.current_bucket,
                action_required=False,
                reason=f"SETTLEMENT_LOCKED ({remaining} days left)",
                lock_active=True,
                cooldown_days_remaining=remaining,
                target_beta=sizing.target_beta,
                raw_target_beta=sizing.raw_target_beta,
                qqq_dollars=sizing.qqq_dollars,
                qld_notional_dollars=sizing.qld_notional_dollars,
                cash_dollars=sizing.cash_dollars,
            )

        if forced_bucket is not None:
            self.current_bucket = forced_bucket
            if self.current_bucket != previous_bucket:
                self.cooldown_days_remaining = self.settlement_days
            self.last_target_beta = sizing.target_beta
            self.evidence = 0.0
            return self._decision(
                previous_bucket,
                sizing,
                reason=forced_reason or "FORCED SAFETY OVERRIDE",
                lock_active=False,
            )

        desired_bucket = self._bucket_from_beta(sizing.target_beta)
        if desired_bucket != previous_bucket:
            self.evidence += self._switch_margin(previous_bucket, desired_bucket, sizing.target_beta)
            barrier = self._entropy_barrier(
                sizing.entropy,
                bucket_count=len(self._BUCKET_ORDER),
            )
            if self.evidence < barrier:
                self.current_bucket = previous_bucket
                self.last_target_beta = sizing.target_beta
                return self._decision(
                    previous_bucket,
                    sizing,
                    reason=(
                        f"EVIDENCE_HOLD: candidate={desired_bucket} "
                        f"evidence={self.evidence:.3f}/{barrier:.3f}"
                    ),
                    lock_active=False,
                )
            self.current_bucket = desired_bucket
            self.cooldown_days_remaining = self.settlement_days
            self.evidence = 0.0
        else:
            self.current_bucket = desired_bucket
            self.evidence = 0.0
        self.last_target_beta = sizing.target_beta
        return self._decision(
            previous_bucket,
            sizing,
            reason=self._reason_for_transition(previous_bucket, self.current_bucket, sizing.target_beta),
            lock_active=False,
        )

    def sync_to_bucket(self, bucket: str, *, settlement_lock: bool = True) -> None:
        if bucket != self.current_bucket and settlement_lock:
            self.cooldown_days_remaining = self.settlement_days
        self.current_bucket = bucket
        self.evidence = 0.0

    def _bucket_from_beta(self, target_beta: float) -> str:
        if target_beta > 1.0:
            return "QLD"
        if target_beta >= 0.5:
            return "QQQ"
        return "CASH"

    @staticmethod
    def _reason_for_transition(previous: str, current: str, target_beta: float) -> str:
        if previous == current:
            return "BUCKET_HOLD"
        if current == "CASH":
            return f"DEFENSIVE_EXIT: target_beta {target_beta:.2f}"
        if current == "QQQ":
            return f"DELEVERAGE: target_beta {target_beta:.2f}"
        return f"RISK_REENGAGE: target_beta {target_beta:.2f}"

    @classmethod
    def _switch_margin(cls, current_bucket: str, desired_bucket: str, target_beta: float) -> float:
        current_idx = cls._BUCKET_ORDER.get(current_bucket, 1)
        desired_idx = cls._BUCKET_ORDER.get(desired_bucket, 1)
        if current_idx == desired_idx:
            return 0.0

        lower = min(current_idx, desired_idx)
        upper = max(current_idx, desired_idx)
        crossed_boundaries = cls._BOUNDARIES[lower:upper]
        return float(sum(abs(float(target_beta) - boundary) for boundary in crossed_boundaries))

    @classmethod
    def _entropy_barrier(cls, entropy: float, *, bucket_count: int | None = None) -> float:
        h = min(0.999, max(0.0, float(entropy)))
        states = max(1, int(bucket_count or len(cls._BUCKET_ORDER)))
        return (h / max(1e-6, 1.0 - h)) / states

    def _decision(
        self,
        previous_bucket: str,
        sizing: PositionSizingResult,
        *,
        reason: str,
        lock_active: bool,
    ) -> ExecutionDecision:
        return ExecutionDecision(
            target_bucket=self.current_bucket,
            target_exposure=self.current_bucket,
            action_required=self.current_bucket != previous_bucket,
            reason=reason,
            lock_active=lock_active,
            cooldown_days_remaining=self.cooldown_days_remaining,
            target_beta=sizing.target_beta,
            raw_target_beta=sizing.raw_target_beta,
            qqq_dollars=sizing.qqq_dollars,
            qld_notional_dollars=sizing.qld_notional_dollars,
            cash_dollars=sizing.cash_dollars,
        )
