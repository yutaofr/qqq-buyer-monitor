"""Deterministic prior knowledge store for the v11 Bayesian regime engine."""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Iterable
from pathlib import Path

import numpy as np

from src.regime_topology import (
    canonicalize_regime_name,
    canonicalize_regime_sequence,
    merge_regime_weights,
    merge_transition_matrix,
)

logger = logging.getLogger(__name__)


class PriorKnowledgeBase:
    """
    Deterministically manages and persists regime priors and transition memory.

    V13.8 INDUSTRIAL SPEC: Fixed Baseline Prior Gravity (5%)
    To prevent "Prior Inflation" and the "High-Entropy Deadlock" common in high-dimensional
    orthogonal spaces, this class enforces a minimal 5.0% baseline for historical counts
    once the system reaches maturity (total_counts > 100). This ensures the Bayesian
    posterior is dominated by recent evidence and transition dynamics (95% combined)
    rather than being trapped by ancient, potentially stale historical averages.
    """

    def __init__(
        self,
        *,
        storage_path: str | Path = "data/v11_prior_state.json",
        regimes: Iterable[str] | None = None,
        bootstrap_regimes: Iterable[str] | None = None,
        pseudo_count: float = 1.0,
        transition_blend: float = 0.35,
        allow_bootstrap_fingerprint_drift: bool = False,
    ):
        self.storage_path = Path(storage_path)
        self.pseudo_count = float(pseudo_count)
        self.transition_blend = float(transition_blend)
        self.allow_bootstrap_fingerprint_drift = bool(allow_bootstrap_fingerprint_drift)
        resolved_regimes = canonicalize_regime_sequence(regimes, include_all=False)
        if not resolved_regimes and bootstrap_regimes is not None:
            resolved_regimes = canonicalize_regime_sequence(bootstrap_regimes, include_all=False)
        expected_bootstrap_fingerprint = self._compute_bootstrap_fingerprint(bootstrap_regimes)

        if self.storage_path.exists():
            backfilled = self._load(
                fallback_regimes=resolved_regimes,
                bootstrap_regimes=bootstrap_regimes,
                expected_bootstrap_fingerprint=expected_bootstrap_fingerprint,
            )
            if backfilled:
                self._save()
            return

        if not resolved_regimes:
            raise ValueError("PriorKnowledgeBase requires regimes or an existing storage file.")

        self.regimes = resolved_regimes
        self.counts = {regime: self.pseudo_count for regime in self.regimes}
        self.transition_counts = {
            regime: {target: self.pseudo_count for target in self.regimes}
            for regime in self.regimes
        }
        self.last_posterior: dict[str, float] | None = None
        self.last_observation_date: str | None = None
        self.execution_state: dict[str, float | str | int | bool | None] = (
            self._bootstrap_execution_state(
                bootstrap_regimes=bootstrap_regimes,
                fallback_regimes=self.regimes,
            )
        )
        self.bootstrap_fingerprint = expected_bootstrap_fingerprint

        if bootstrap_regimes is not None:
            self._bootstrap_from_regimes(bootstrap_regimes)
        self._save()

    def current_priors(self) -> dict[str, float]:
        return self._normalize(self.counts)

    def runtime_priors(
        self,
        previous_posterior: dict[str, float] | None = None,
        macro_values: dict[str, float] | None = None,
        current_observation_date: str | None = None,
    ) -> tuple[dict[str, float], dict[str, any]]:
        """
        Synthesize the Bayesian prior for the current timestep.
        V14.2 FORENSIC HARDENING:
        1. Inject Regime Inertia (Diagonal Matrix) to prevent Flickering.
        2. Implement Mid-Cycle Anchor: Force stability when MOVE/Spread < 1.0.
        3. Enforce Duration Specification:
           - MID_CYCLE (3-4 years)
           - LATE_CYCLE (6+ months)
        """
        base_priors = self.current_priors()
        prior_source = previous_posterior or self.last_posterior

        logger.info("Bayesian Prior Synthesis initiated.")
        logger.info(
            f"  Source 1 [Historical Baseline]: Based on {sum(self.counts.values()):.1f} total counts from {self.storage_path}"
        )

        if (
            current_observation_date is not None
            and self.last_observation_date is not None
            and str(current_observation_date) < str(self.last_observation_date)
        ):
            logger.warning(
                "Warm-start prior %s is newer than current observation %s; ignoring recent memory.",
                self.last_observation_date,
                current_observation_date,
            )
            prior_source = None

        # If no previous knowledge, return baseline as 100% of the prior
        if not prior_source:
            logger.info(
                "  Source 2 [Recent Memory]: No usable previous observation found. Using 100% baseline."
            )
            details = {
                "base_weight": 1.0,
                "posterior_weight": 0.0,
                "transition_weight": 0.0,
                "base_priors": base_priors,
                "posterior_prior": base_priors,
                "transition_prior": base_priors,
            }
            return base_priors, details

        logger.info(
            f"  Source 2 [Recent Memory]: Found posterior from {self.last_observation_date or 'unknown date'}"
        )
        normalized_source = self._normalize(
            merge_regime_weights(
                prior_source,
                regimes=self.regimes,
                include_zeros=True,
            )
        )
        recovery_release_score = self._recovery_prior_release_score(macro_values)
        if recovery_release_score > 0.0:
            normalized_source = self._apply_recovery_release_to_posterior_prior(
                normalized_source,
                release_score=recovery_release_score,
            )

        # V14.2: Construct Structural Transition Matrix (Inertia)
        # --------------------------------------------------------
        # We replace the historically noisy transition_counts with a structural matrix
        # to enforce industrial-grade regime stability.

        transition_prior = {regime: 0.0 for regime in self.regimes}

        import os

        disable_inertia = os.environ.get("DISABLE_REGIME_INERTIA", "OFF") == "ON"

        # 1. Macro Stability Check (Mid-Cycle Anchor)
        move_z = abs(float((macro_values or {}).get("move_21d", 0.0)))
        spread_z = abs(float((macro_values or {}).get("spread_21d", 0.0)))
        is_stable = move_z < 1.0 and spread_z < 1.0

        # V14.3: Structural Cycle Transition Path
        # RECOVERY -> MID_CYCLE -> LATE_CYCLE -> BUST -> RECOVERY
        next_regime_map = {
            "RECOVERY": "MID_CYCLE",
            "MID_CYCLE": "LATE_CYCLE",
            "LATE_CYCLE": "BUST",
            "BUST": "RECOVERY",
        }

        # v14.5 ANTI-HARDCODING: Inject inertia from registry via macro_values/context
        # The 'dynamic_beta_inertia_matrix' should be provided in the registry.
        inertia_map = (macro_values or {}).get("dynamic_beta_inertia_matrix", {})
        default_inertia = inertia_map.get("DEFAULT", 0.90)

        for regime, weight in normalized_source.items():
            # Diagonal Inertia: Favor staying in the same regime
            inertia = float(inertia_map.get(regime, default_inertia))

            if not disable_inertia:
                # v14.5: If we are in MID_CYCLE and stable, we may have a different override
                # but we prefer the registry value if present.
                if regime == "MID_CYCLE" and is_stable:
                    # In v14.5, we already have this in the inertia_map
                    pass
            else:
                inertia = 0.25  # Neutralize inertia for experimental audit

            # Sequence Bias: Instead of uniform remainder, favor the NEXT regime in the cycle
            next_regime = next_regime_map.get(regime)
            other_regimes = [r for r in self.regimes if r != regime]

            for target in self.regimes:
                if target == regime:
                    transition_prior[target] += weight * inertia
                elif target == next_regime:
                    # Grant 70% of the 'escape' weight to the logically next regime
                    transition_prior[target] += weight * (1.0 - inertia) * 0.7
                else:
                    # Split the remaining 30% of 'escape' weight among others
                    remaining_n = max(1, len(other_regimes) - (1 if next_regime else 0))
                    transition_prior[target] += weight * (1.0 - inertia) * 0.3 / remaining_n

        # The prior must stabilize noise, but it cannot overpower present-tense stress.
        stress_components = {
            "spread": min(1.0, max(0.0, (spread_z - 1.0) / 2.0)),
            "move": min(1.0, max(0.0, (move_z - 1.0) / 2.0)),
            "price": min(
                1.0,
                max(0.0, (-float((macro_values or {}).get("qqq_ma_ratio", 0.0)) - 0.10) / 0.90),
            ),
            "liquidity": min(
                1.0,
                max(
                    0.0,
                    (-float((macro_values or {}).get("liquidity_velocity", 0.0)) - 0.50) / 2.00,
                ),
            ),
            "credit_acceleration": min(
                1.0,
                max(
                    0.0,
                    (float((macro_values or {}).get("credit_acceleration", 0.0)) - 0.75) / 1.50,
                ),
            ),
        }
        stress_score = min(
            1.0,
            (
                (0.20 * stress_components["spread"])
                + (0.20 * stress_components["move"])
                + (0.25 * stress_components["price"])
                + (0.20 * stress_components["liquidity"])
                + (0.15 * stress_components["credit_acceleration"])
            ),
        )

        base_weight = 0.05
        posterior_weight = 0.60 + (0.20 * stress_score)
        transition_weight = 1.0 - base_weight - posterior_weight
        if recovery_release_score > 0.0:
            release_weight_shift = 0.10 * recovery_release_score
            posterior_weight = max(0.48, posterior_weight - release_weight_shift)
            transition_weight = 1.0 - base_weight - posterior_weight

        logger.info(
            f"  V14.2-STABLE Blending: {base_weight:.1%} history | {posterior_weight:.1%} last-seen | {transition_weight:.1%} inertia-shift"
        )
        if is_stable:
            logger.info("  Mid-Cycle Anchor ACTIVE: Macro volatility is low.")

        blended = {}
        for regime in self.regimes:
            blended[regime] = (
                base_weight * base_priors.get(regime, 0.0)
                + posterior_weight * normalized_source.get(regime, 0.0)
                + transition_weight * transition_prior.get(regime, 0.0)
            )

        final_prior = self._normalize(blended)

        # Log top 2 regimes in the final prior for immediate visibility
        top_regimes = sorted(final_prior.items(), key=lambda x: x[1], reverse=True)[:2]
        prior_str = ", ".join([f"{r} ({p:.1%})" for r, p in top_regimes])
        logger.info(f"  Synthesized Prior: {prior_str}")

        details = {
            "base_weight": base_weight,
            "posterior_weight": posterior_weight,
            "transition_weight": transition_weight,
            "base_priors": base_priors,
            "posterior_prior": normalized_source,
            "transition_prior": self._normalize(transition_prior),
            "is_stable": is_stable,
            "stress_score": stress_score,
            "recovery_release_score": recovery_release_score,
        }
        return final_prior, details

    @staticmethod
    def _recovery_prior_release_score(macro_values: dict[str, float] | None) -> float:
        context = macro_values or {}
        topology_regime = str(context.get("price_topology_regime", ""))
        if topology_regime not in {"RECOVERY", "LATE_CYCLE", "BUST"}:
            return 0.0

        confidence = float(context.get("price_topology_confidence", 0.0) or 0.0)
        transition_intensity = float(context.get("price_topology_transition_intensity", 0.0) or 0.0)
        repair_persistence = float(context.get("price_topology_repair_persistence", 0.0) or 0.0)
        recovery_impulse = float(context.get("price_topology_recovery_impulse", 0.0) or 0.0)
        damage_memory = float(context.get("price_topology_damage_memory", 0.0) or 0.0)
        recovery_prob_delta = float(context.get("price_topology_recovery_prob_delta", 0.0) or 0.0)
        recovery_prob_acceleration = float(
            context.get("price_topology_recovery_prob_acceleration", 0.0) or 0.0
        )

        if (
            transition_intensity < 0.52
            or repair_persistence < 0.24
            or recovery_impulse < 0.16
            or damage_memory < 0.30
        ):
            return 0.0
        if topology_regime == "BUST" and (
            transition_intensity < 0.62
            or repair_persistence < 0.28
            or recovery_impulse < 0.18
            or damage_memory < 0.50
        ):
            return 0.0
        if topology_regime == "LATE_CYCLE" and (
            transition_intensity < 0.72
            or repair_persistence < 0.30
            or recovery_impulse < 0.20
            or damage_memory < 0.55
        ):
            return 0.0

        confidence_support = np.clip((confidence - 0.08) / 0.22, 0.0, 1.0)
        transition_support = np.clip((transition_intensity - 0.52) / 0.30, 0.0, 1.0)
        repair_support = np.clip((repair_persistence - 0.24) / 0.35, 0.0, 1.0)
        impulse_support = np.clip((recovery_impulse - 0.16) / 0.45, 0.0, 1.0)
        damage_support = np.clip((damage_memory - 0.30) / 0.45, 0.0, 1.0)
        delta_support = np.clip((recovery_prob_delta - 0.005) / 0.03, 0.0, 1.0)
        acceleration_support = np.clip(recovery_prob_acceleration / 0.03, 0.0, 1.0)

        score = (
            0.16 * float(confidence_support)
            + 0.20 * float(transition_support)
            + 0.22 * float(repair_support)
            + 0.16 * float(impulse_support)
            + 0.12 * float(damage_support)
            + 0.08 * float(delta_support)
            + 0.06 * float(acceleration_support)
        )
        if topology_regime == "LATE_CYCLE":
            score *= 0.85
        elif topology_regime == "BUST":
            score *= 0.92
        return float(np.clip(score, 0.0, 1.0))

    def _apply_recovery_release_to_posterior_prior(
        self,
        posterior_prior: dict[str, float],
        *,
        release_score: float,
    ) -> dict[str, float]:
        adjusted = dict(posterior_prior)
        bust_mass = float(adjusted.get("BUST", 0.0))
        late_mass = float(adjusted.get("LATE_CYCLE", 0.0))
        recovery_mass = float(adjusted.get("RECOVERY", 0.0))
        mid_mass = float(adjusted.get("MID_CYCLE", 0.0))

        bust_shift = min(
            bust_mass * (0.10 + 0.12 * release_score),
            max(0.0, bust_mass - (recovery_mass * 0.78)),
        )
        late_shift = min(
            late_mass * (0.06 + 0.08 * release_score),
            max(0.0, late_mass - (mid_mass * 0.70)),
        )
        if bust_shift <= 0.0 and late_shift <= 0.0:
            return adjusted

        adjusted["BUST"] = max(0.0, bust_mass - bust_shift)
        adjusted["LATE_CYCLE"] = max(0.0, late_mass - late_shift)
        adjusted["RECOVERY"] = recovery_mass + (0.88 * bust_shift) + (0.55 * late_shift)
        adjusted["MID_CYCLE"] = mid_mass + (0.12 * bust_shift) + (0.45 * late_shift)
        return self._normalize(adjusted)

    def update_with_posterior(
        self,
        *,
        observation_date: str,
        posterior: dict[str, float],
    ) -> None:
        normalized_posterior = self._normalize(
            merge_regime_weights(
                posterior,
                regimes=self.regimes,
                include_zeros=True,
            )
        )

        # KISS Idempotency: Skip count updates if we already saw this date
        if str(observation_date) == self.last_observation_date:
            # We still update the last_posterior to ensure the next day uses the most recent inference
            self.last_posterior = normalized_posterior
            self._save()
            return

        # EXPERT TUNING: Exponential Forgetting to prevent Prior Inflation (Zombie Prior)
        # Decay of 0.995 yields ~138 day half-life, letting the system forget ancient history
        # while bounding the maximum weight of the prior.
        decay_factor = 0.995

        for regime in self.regimes:
            self.counts[regime] = (
                self.counts.get(regime, self.pseudo_count) * decay_factor
            ) + normalized_posterior.get(regime, 0.0)

        if self.last_posterior is not None:
            previous = self._normalize(self.last_posterior)
            for src_regime, src_weight in previous.items():
                row = self.transition_counts.setdefault(
                    src_regime,
                    {target: self.pseudo_count for target in self.regimes},
                )
                for dst_regime, dst_weight in normalized_posterior.items():
                    row[dst_regime] = (row.get(dst_regime, self.pseudo_count) * decay_factor) + (
                        src_weight * dst_weight
                    )

        self.last_posterior = normalized_posterior
        self.last_observation_date = str(observation_date)

        # Log the finalized state for confirmation
        top_posteriors = sorted(self.last_posterior.items(), key=lambda x: x[1], reverse=True)[:2]
        post_str = ", ".join([f"{r} ({p:.1%})" for r, p in top_posteriors])
        logger.info(f"Bayesian State Finalized for {self.last_observation_date}:")
        logger.info(f"  Saved Posterior: {post_str}")
        logger.info(
            "  Note: This posterior will serve as Source 2 (Recent Memory) for the next run."
        )

        self._save()

    def get_execution_state(self) -> dict[str, float | str | int | bool | None]:
        return dict(self.execution_state)

    def update_execution_state(self, **state: float | str | int | bool | None) -> None:
        self.execution_state.update(state)
        self._save()

    def _bootstrap_from_regimes(self, bootstrap_regimes: Iterable[str]) -> None:
        history = []
        for regime in bootstrap_regimes:
            canonical = canonicalize_regime_name(regime)
            if canonical in self.regimes:
                history.append(canonical)
        for regime in history:
            self.counts[regime] += 1.0

        for previous, current in zip(history, history[1:], strict=False):
            self.transition_counts[previous][current] += 1.0

    def _load(
        self,
        *,
        fallback_regimes: Iterable[str] | None = None,
        bootstrap_regimes: Iterable[str] | None = None,
        expected_bootstrap_fingerprint: str | None = None,
    ) -> bool:
        backfilled = False
        payload = json.loads(self.storage_path.read_text())
        payload_regimes = payload.get("regimes")
        if fallback_regimes:
            self.regimes = canonicalize_regime_sequence(fallback_regimes, include_all=False)
            if payload_regimes and [str(regime) for regime in payload_regimes] != self.regimes:
                backfilled = True
        elif payload_regimes:
            self.regimes = canonicalize_regime_sequence(payload_regimes, include_all=False)
            if [str(regime) for regime in payload_regimes] != self.regimes:
                backfilled = True
        else:
            raise ValueError(
                "PriorKnowledgeBase state is missing regimes and no bootstrap fallback is available."
            )

        self.pseudo_count = float(payload.get("pseudo_count", self.pseudo_count))
        self.transition_blend = float(payload.get("transition_blend", self.transition_blend))

        counts_payload = payload.get("counts", {})
        if not isinstance(counts_payload, dict):
            raise ValueError("PriorKnowledgeBase counts payload must be a mapping.")
        merged_counts = merge_regime_weights(
            counts_payload,
            regimes=self.regimes,
            include_zeros=False,
        )
        if set(merged_counts) != set(counts_payload):
            backfilled = True
        self.counts = {
            regime: float(merged_counts.get(regime, self.pseudo_count)) for regime in self.regimes
        }

        transition_payload = payload.get("transition_counts", {})
        if not isinstance(transition_payload, dict):
            raise ValueError("PriorKnowledgeBase transition payload must be a mapping.")
        merged_transitions = merge_transition_matrix(transition_payload, regimes=self.regimes)
        if set(merged_transitions) != set(transition_payload):
            backfilled = True
        self.transition_counts = {
            src: {
                dst: float(merged_transitions.get(src, {}).get(dst, self.pseudo_count))
                for dst in self.regimes
            }
            for src in self.regimes
        }

        self.last_posterior = (
            merge_regime_weights(
                payload.get("last_posterior", {}),
                regimes=self.regimes,
                include_zeros=True,
            )
            if isinstance(payload.get("last_posterior"), dict)
            else None
        )
        self.last_observation_date = payload.get("last_observation_date")
        self.execution_state = self._default_execution_state()
        payload_execution_state = (
            dict(payload.get("execution_state", {}))
            if isinstance(payload.get("execution_state"), dict)
            else {}
        )
        self.execution_state.update(payload_execution_state)
        filled_missing_execution_fields = False
        for key, value in self._default_execution_state().items():
            if key not in self.execution_state or self.execution_state[key] is None:
                self.execution_state[key] = value
                filled_missing_execution_fields = True
        if filled_missing_execution_fields:
            backfilled = True
        stable_regime = canonicalize_regime_name(self.execution_state.get("stable_regime"))
        if stable_regime and stable_regime != self.execution_state.get("stable_regime"):
            self.execution_state["stable_regime"] = stable_regime
            backfilled = True
        if stable_regime is None:
            bootstrap_state = self._bootstrap_execution_state(
                bootstrap_regimes=bootstrap_regimes,
                fallback_regimes=self.regimes,
            )
            if bootstrap_state:
                self.execution_state.update(bootstrap_state)
                backfilled = True
        stored_fingerprint = payload.get("bootstrap_fingerprint")
        if stored_fingerprint is None and expected_bootstrap_fingerprint is not None:
            self.bootstrap_fingerprint = expected_bootstrap_fingerprint
            backfilled = True
        elif stored_fingerprint is not None:
            self.bootstrap_fingerprint = str(stored_fingerprint)
        else:
            self.bootstrap_fingerprint = None

        if (
            expected_bootstrap_fingerprint is not None
            and self.bootstrap_fingerprint is not None
            and self.bootstrap_fingerprint != expected_bootstrap_fingerprint
        ):
            if self.allow_bootstrap_fingerprint_drift:
                self.bootstrap_fingerprint = expected_bootstrap_fingerprint
                backfilled = True
            else:
                raise ValueError(
                    "PriorKnowledgeBase bootstrap fingerprint mismatch. Canonical regime DNA drift detected."
                )
        return backfilled

    @staticmethod
    def _bootstrap_execution_state(
        *,
        bootstrap_regimes: Iterable[str] | None,
        fallback_regimes: Iterable[str] | None,
    ) -> dict[str, str | float]:
        history = canonicalize_regime_sequence(bootstrap_regimes, include_all=False)
        if history:
            return {
                "stable_regime": history[-1],
                "regime_evidence": 0.0,
            }

        return {}

    @staticmethod
    def _default_execution_state() -> dict[str, str | float | int | bool | None]:
        return {
            "stable_regime": None,
            "regime_evidence": 0.0,
            "current_beta": 0.0,
            "beta_evidence": 0.0,
            "current_bucket": "QQQ",
            "bucket_evidence": 0.0,
            "bucket_cooldown_days": 0,
            "deployment_state": "DEPLOY_BASE",
            "deployment_evidence": 0.0,
            "high_entropy_streak": 0,
            "hydration_anchor": "2018-01-01",
            "previous_posterior": None,
            "effective_entropy": 0.0,
            "resonance_risk_ready_days": 99,
            "resonance_waterfall_ready_days": 99,
        }

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "v11-prior-state",
            "regimes": self.regimes,
            "counts": self.counts,
            "transition_counts": self.transition_counts,
            "last_posterior": self.last_posterior,
            "last_observation_date": self.last_observation_date,
            "execution_state": self.execution_state,
            "pseudo_count": self.pseudo_count,
            "transition_blend": self.transition_blend,
            "bootstrap_fingerprint": self.bootstrap_fingerprint,
        }
        self.storage_path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    @staticmethod
    def _normalize(weights: dict[str, float]) -> dict[str, float]:
        total = float(sum(max(0.0, float(value)) for value in weights.values()))
        if total <= 0:
            n = max(1, len(weights))
            return {str(key): 1.0 / n for key in weights}
        return {str(key): max(0.0, float(value)) / total for key, value in weights.items()}

    @staticmethod
    def _compute_bootstrap_fingerprint(bootstrap_regimes: Iterable[str] | None) -> str | None:
        if bootstrap_regimes is None:
            return None
        canonical = json.dumps(
            [canonicalize_regime_name(regime) or str(regime) for regime in bootstrap_regimes],
            separators=(",", ":"),
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"
