"""Deterministic prior knowledge store for the v11 Bayesian regime engine."""
from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Iterable
from pathlib import Path

logger = logging.getLogger(__name__)


class PriorKnowledgeBase:
    """Persist regime priors and transition memory across runs."""

    def __init__(
        self,
        *,
        storage_path: str | Path = "data/v11_prior_state.json",
        regimes: Iterable[str] | None = None,
        bootstrap_regimes: Iterable[str] | None = None,
        pseudo_count: float = 1.0,
        transition_blend: float = 0.35,
    ):
        self.storage_path = Path(storage_path)
        self.pseudo_count = float(pseudo_count)
        self.transition_blend = float(transition_blend)
        resolved_regimes = list(regimes or [])
        if not resolved_regimes and bootstrap_regimes is not None:
            resolved_regimes = sorted({str(regime) for regime in bootstrap_regimes})
        expected_bootstrap_fingerprint = self._compute_bootstrap_fingerprint(bootstrap_regimes)

        if self.storage_path.exists():
            backfilled = self._load(
                fallback_regimes=resolved_regimes,
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
        self.execution_state: dict[str, float | str | int | bool | None] = {}
        self.bootstrap_fingerprint = expected_bootstrap_fingerprint

        if bootstrap_regimes is not None:
            self._bootstrap_from_regimes(bootstrap_regimes)
        self._save()

    def current_priors(self) -> dict[str, float]:
        return self._normalize(self.counts)

    def runtime_priors(
        self, previous_posterior: dict[str, float] | None = None
    ) -> tuple[dict[str, float], dict[str, any]]:
        base_priors = self.current_priors()
        prior_source = previous_posterior or self.last_posterior

        logger.info("Bayesian Prior Synthesis initiated.")
        logger.info(f"  Source 1 [Historical Baseline]: Based on {sum(self.counts.values()):.1f} total counts from {self.storage_path}")

        # If no previous knowledge, return baseline as 100% of the prior
        if not prior_source:
             logger.info("  Source 2 [Recent Memory]: No previous observation found. Using 100% baseline.")
             details = {
                "base_weight": 1.0,
                "posterior_weight": 0.0,
                "transition_weight": 0.0,
                "base_priors": base_priors,
                "posterior_prior": base_priors,
                "transition_prior": base_priors
            }
             return base_priors, details

        logger.info(f"  Source 2 [Recent Memory]: Found posterior from {self.last_observation_date or 'unknown date'}")
        normalized_source = self._normalize(prior_source)
        transition_prior = {regime: 0.0 for regime in self.regimes}
        for regime, weight in normalized_source.items():
            row = self.transition_counts.get(regime)
            if not row:
                continue
            normalized_row = self._normalize(row)
            for target, target_weight in normalized_row.items():
                transition_prior[target] += weight * target_weight

        # Blending logic constants
        posterior_weight = self.transition_blend * 0.5
        transition_weight = self.transition_blend * 0.5
        base_weight = 1.0 - posterior_weight - transition_weight

        logger.info(f"  Blending weights: {base_weight:.1%} history | {posterior_weight:.1%} last-seen | {transition_weight:.1%} predicted-shift")

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
            "transition_prior": self._normalize(transition_prior)
        }
        return final_prior, details

    def update_with_posterior(
        self,
        *,
        observation_date: str,
        posterior: dict[str, float],
    ) -> None:
        normalized_posterior = self._normalize(posterior)

        # KISS Idempotency: Skip count updates if we already saw this date
        if str(observation_date) == self.last_observation_date:
            # We still update the last_posterior to ensure the next day uses the most recent inference
            self.last_posterior = normalized_posterior
            self._save()
            return

        for regime in self.regimes:
            self.counts[regime] = self.counts.get(regime, self.pseudo_count) + normalized_posterior.get(
                regime, 0.0
            )

        if self.last_posterior is not None:
            previous = self._normalize(self.last_posterior)
            for src_regime, src_weight in previous.items():
                row = self.transition_counts.setdefault(
                    src_regime,
                    {target: self.pseudo_count for target in self.regimes},
                )
                for dst_regime, dst_weight in normalized_posterior.items():
                    row[dst_regime] = row.get(dst_regime, self.pseudo_count) + (
                        src_weight * dst_weight
                    )

        self.last_posterior = normalized_posterior
        self.last_observation_date = str(observation_date)

        # Log the finalized state for confirmation
        top_posteriors = sorted(self.last_posterior.items(), key=lambda x: x[1], reverse=True)[:2]
        post_str = ", ".join([f"{r} ({p:.1%})" for r, p in top_posteriors])
        logger.info(f"Bayesian State Finalized for {self.last_observation_date}:")
        logger.info(f"  Saved Posterior: {post_str}")
        logger.info("  Note: This posterior will serve as Source 2 (Recent Memory) for the next run.")

        self._save()

    def get_execution_state(self) -> dict[str, float | str | int | bool | None]:
        return dict(self.execution_state)

    def update_execution_state(self, **state: float | str | int | bool | None) -> None:
        self.execution_state.update(state)
        self._save()

    def _bootstrap_from_regimes(self, bootstrap_regimes: Iterable[str]) -> None:
        history = [str(regime) for regime in bootstrap_regimes if str(regime) in self.regimes]
        for regime in history:
            self.counts[regime] += 1.0

        for previous, current in zip(history, history[1:], strict=False):
            self.transition_counts[previous][current] += 1.0

    def _load(
        self,
        *,
        fallback_regimes: Iterable[str] | None = None,
        expected_bootstrap_fingerprint: str | None = None,
    ) -> bool:
        backfilled = False
        payload = json.loads(self.storage_path.read_text())
        payload_regimes = payload.get("regimes")
        if payload_regimes:
            self.regimes = [str(regime) for regime in payload_regimes]
        elif fallback_regimes:
            self.regimes = [str(regime) for regime in fallback_regimes]
            backfilled = True
        else:
            raise ValueError("PriorKnowledgeBase state is missing regimes and no bootstrap fallback is available.")

        self.pseudo_count = float(payload.get("pseudo_count", self.pseudo_count))
        self.transition_blend = float(payload.get("transition_blend", self.transition_blend))

        counts_payload = payload.get("counts", {})
        if not isinstance(counts_payload, dict):
            raise ValueError("PriorKnowledgeBase counts payload must be a mapping.")
        self.counts = {
            regime: float(counts_payload.get(regime, self.pseudo_count))
            for regime in self.regimes
        }

        transition_payload = payload.get("transition_counts", {})
        if not isinstance(transition_payload, dict):
            raise ValueError("PriorKnowledgeBase transition payload must be a mapping.")
        self.transition_counts = {}
        for src in self.regimes:
            row_payload = transition_payload.get(src, {})
            if not isinstance(row_payload, dict):
                row_payload = {}
            self.transition_counts[src] = {
                dst: float(row_payload.get(dst, self.pseudo_count))
                for dst in self.regimes
            }

        self.last_posterior = (
            {
                regime: float(payload.get("last_posterior", {}).get(regime, 0.0))
                for regime in self.regimes
            }
            if isinstance(payload.get("last_posterior"), dict)
            else None
        )
        self.last_observation_date = payload.get("last_observation_date")
        self.execution_state = (
            dict(payload.get("execution_state", {}))
            if isinstance(payload.get("execution_state"), dict)
            else {}
        )
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
            raise ValueError(
                "PriorKnowledgeBase bootstrap fingerprint mismatch. Canonical regime DNA drift detected."
            )
        return backfilled

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
        canonical = json.dumps([str(regime) for regime in bootstrap_regimes], separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"
