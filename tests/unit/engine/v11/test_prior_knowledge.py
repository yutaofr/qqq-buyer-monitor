import json

import pytest

from src.engine.v11.core.prior_knowledge import PriorKnowledgeBase


@pytest.fixture
def bootstrap_history():
    return [
        "MID_CYCLE",
        "MID_CYCLE",
        "LATE_CYCLE",
        "BUST",
        "RECOVERY",
        "MID_CYCLE",
    ]


def test_prior_knowledge_bootstrap_is_deterministic(tmp_path, bootstrap_history):
    storage_path = tmp_path / "prior_state.json"

    library = PriorKnowledgeBase(
        storage_path=storage_path,
        regimes=["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"],
        bootstrap_regimes=bootstrap_history,
    )

    priors = library.current_priors()

    assert sum(priors.values()) == pytest.approx(1.0)
    assert priors["MID_CYCLE"] > priors["BUST"]
    assert library.execution_state["stable_regime"] == "RECOVERY"
    assert storage_path.exists()


def test_prior_knowledge_bootstrap_anchors_latest_regime(tmp_path):
    storage_path = tmp_path / "prior_state.json"
    bootstrap_history = [
        "MID_CYCLE",
        "MID_CYCLE",
        "LATE_CYCLE",
        "LATE_CYCLE",
    ]

    library = PriorKnowledgeBase(
        storage_path=storage_path,
        regimes=["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"],
        bootstrap_regimes=bootstrap_history,
    )

    assert library.execution_state["stable_regime"] == "LATE_CYCLE"
    assert library.execution_state["regime_evidence"] == pytest.approx(0.0)


def test_prior_knowledge_persists_posterior_updates(tmp_path, bootstrap_history):
    storage_path = tmp_path / "prior_state.json"

    library = PriorKnowledgeBase(
        storage_path=storage_path,
        regimes=["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"],
        bootstrap_regimes=bootstrap_history,
    )
    base_priors = library.current_priors()

    library.update_with_posterior(
        observation_date="2026-03-30",
        posterior={"MID_CYCLE": 0.10, "LATE_CYCLE": 0.15, "BUST": 0.70, "RECOVERY": 0.05},
    )

    reloaded = PriorKnowledgeBase(storage_path=storage_path)
    updated_priors = reloaded.current_priors()

    assert updated_priors["BUST"] > base_priors["BUST"]

    priors_2, _ = reloaded.runtime_priors()
    assert priors_2["BUST"] > priors_2["MID_CYCLE"]

    payload = json.loads(storage_path.read_text())
    assert payload["last_observation_date"] == "2026-03-30"


def test_runtime_priors_ignore_future_memory_when_current_date_is_earlier(tmp_path):
    storage_path = tmp_path / "prior_state.json"
    storage_path.write_text(
        json.dumps(
            {
                "version": "v11-prior-state",
                "regimes": ["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"],
                "counts": {
                    "MID_CYCLE": 10.0,
                    "LATE_CYCLE": 10.0,
                    "BUST": 10.0,
                    "RECOVERY": 10.0,
                },
                "transition_counts": {},
                "last_posterior": {
                    "MID_CYCLE": 0.05,
                    "LATE_CYCLE": 0.05,
                    "BUST": 0.05,
                    "RECOVERY": 0.85,
                },
                "last_observation_date": "2099-12-31",
                "execution_state": {"stable_regime": "RECOVERY"},
                "bootstrap_fingerprint": "sha256:test",
            }
        )
    )

    library = PriorKnowledgeBase(storage_path=storage_path)
    priors, details = library.runtime_priors(
        current_observation_date="2026-03-30",
        macro_values={"move_21d": 0.0, "spread_21d": 0.0},
    )

    assert details["posterior_weight"] == pytest.approx(0.0)
    assert priors["RECOVERY"] == pytest.approx(0.25)
    assert priors["MID_CYCLE"] == pytest.approx(0.25)


def test_prior_knowledge_loads_legacy_payload_with_default_injection(tmp_path, bootstrap_history):
    storage_path = tmp_path / "prior_state.json"
    storage_path.write_text(
        json.dumps(
            {
                "version": "v11-prior-state",
                "regimes": ["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"],
                "counts": {"MID_CYCLE": 4.0},
                "transition_counts": {
                    "MID_CYCLE": {"MID_CYCLE": 2.0},
                },
            }
        )
    )

    library = PriorKnowledgeBase(
        storage_path=storage_path,
        bootstrap_regimes=bootstrap_history,
        allow_bootstrap_fingerprint_drift=True,
    )

    assert library.counts["MID_CYCLE"] == 4.0
    assert library.counts["LATE_CYCLE"] == pytest.approx(1.0)
    assert library.transition_counts["MID_CYCLE"]["BUST"] == pytest.approx(1.0)
    assert library.execution_state["stable_regime"] == "RECOVERY"
    assert library.execution_state["regime_evidence"] == pytest.approx(0.0)
    payload = json.loads(storage_path.read_text())
    assert payload["bootstrap_fingerprint"].startswith("sha256:")
    assert payload["execution_state"]["stable_regime"] == "RECOVERY"


def test_prior_knowledge_backfills_warm_start_execution_schema(tmp_path, bootstrap_history):
    storage_path = tmp_path / "prior_state.json"
    storage_path.write_text(
        json.dumps(
            {
                "version": "v11-prior-state",
                "regimes": ["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"],
                "counts": {"MID_CYCLE": 4.0, "LATE_CYCLE": 3.0, "BUST": 2.0, "RECOVERY": 1.0},
                "transition_counts": {},
                "execution_state": {"stable_regime": "RECOVERY"},
                "bootstrap_fingerprint": "sha256:test",
            }
        )
    )

    library = PriorKnowledgeBase(
        storage_path=storage_path,
        bootstrap_regimes=bootstrap_history,
        allow_bootstrap_fingerprint_drift=True,
    )

    expected_keys = {
        "stable_regime",
        "regime_evidence",
        "current_beta",
        "beta_evidence",
        "current_bucket",
        "bucket_evidence",
        "bucket_cooldown_days",
        "deployment_state",
        "deployment_evidence",
        "high_entropy_streak",
        "hydration_anchor",
        "previous_posterior",
        "effective_entropy",
        "resonance_risk_ready_days",
        "resonance_waterfall_ready_days",
    }

    assert expected_keys.issubset(library.execution_state.keys())
    assert library.execution_state["current_bucket"] == "QQQ"
    assert library.execution_state["deployment_state"] == "DEPLOY_BASE"
    assert library.execution_state["high_entropy_streak"] == 0


def test_recovery_prior_release_score_can_start_inside_bust_when_repair_is_confirmed():
    score = PriorKnowledgeBase._recovery_prior_release_score(
        {
            "price_topology_regime": "BUST",
            "price_topology_confidence": 0.18,
            "price_topology_transition_intensity": 0.70,
            "price_topology_repair_persistence": 0.34,
            "price_topology_recovery_impulse": 0.22,
            "price_topology_damage_memory": 0.72,
            "price_topology_recovery_prob_delta": 0.012,
            "price_topology_recovery_prob_acceleration": 0.005,
        }
    )

    assert score > 0.0


def test_prior_knowledge_rejects_bootstrap_fingerprint_drift(tmp_path, bootstrap_history):
    storage_path = tmp_path / "prior_state.json"
    PriorKnowledgeBase(
        storage_path=storage_path,
        regimes=["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"],
        bootstrap_regimes=bootstrap_history,
    )
    payload = json.loads(storage_path.read_text())
    payload["bootstrap_fingerprint"] = "sha256:bad"
    storage_path.write_text(json.dumps(payload))

    with pytest.raises(ValueError, match="bootstrap fingerprint"):
        PriorKnowledgeBase(storage_path=storage_path, bootstrap_regimes=bootstrap_history)


def test_prior_knowledge_migrates_legacy_capitulation_payload_into_recovery(
    tmp_path, bootstrap_history
):
    storage_path = tmp_path / "prior_state.json"
    storage_path.write_text(
        json.dumps(
            {
                "version": "v11-prior-state",
                "regimes": ["MID_CYCLE", "LATE_CYCLE", "BUST", "CAPITULATION", "RECOVERY"],
                "counts": {
                    "MID_CYCLE": 5.0,
                    "LATE_CYCLE": 4.0,
                    "BUST": 3.0,
                    "CAPITULATION": 2.0,
                    "RECOVERY": 7.0,
                },
                "transition_counts": {
                    "MID_CYCLE": {
                        "MID_CYCLE": 2.0,
                        "CAPITULATION": 1.5,
                        "RECOVERY": 1.0,
                    },
                    "CAPITULATION": {
                        "RECOVERY": 3.0,
                        "BUST": 0.5,
                    },
                },
                "last_posterior": {
                    "MID_CYCLE": 0.2,
                    "CAPITULATION": 0.3,
                    "RECOVERY": 0.1,
                    "BUST": 0.4,
                },
                "execution_state": {
                    "stable_regime": "CAPITULATION",
                },
            }
        )
    )

    library = PriorKnowledgeBase(
        storage_path=storage_path,
        regimes=["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"],
        bootstrap_regimes=bootstrap_history,
    )

    assert library.regimes == ["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"]
    assert "CAPITULATION" not in library.counts
    assert library.counts["RECOVERY"] == pytest.approx(9.0)
    assert library.last_posterior["RECOVERY"] == pytest.approx(0.4)
    assert library.execution_state["stable_regime"] == "RECOVERY"
    payload = json.loads(storage_path.read_text())
    assert payload["regimes"] == ["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"]
    assert "CAPITULATION" not in payload["counts"]


def test_prior_knowledge_cold_start_does_not_use_default_regime(tmp_path):
    """
    Test that a cold start without a bootstrap history does not use the default
    regime for execution state. stable_regime should be None so the first
    inference can correctly anchor it instead of being pulled by an arbitrary default.
    """
    storage_path = tmp_path / "v11_prior_state.json"
    library = PriorKnowledgeBase(
        storage_path=storage_path,
        regimes=["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"],
        bootstrap_regimes=None,
    )

    # Before the fix, this would default to "MID_CYCLE" (fallback[0])
    assert library.execution_state.get("stable_regime") is None


def test_runtime_priors_reduce_transition_gravity_under_market_stress(tmp_path):
    storage_path = tmp_path / "v11_prior_state.json"
    library = PriorKnowledgeBase(
        storage_path=storage_path,
        regimes=["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"],
        bootstrap_regimes=["MID_CYCLE"] * 12 + ["LATE_CYCLE"] * 4,
    )
    library.last_posterior = {
        "MID_CYCLE": 0.90,
        "LATE_CYCLE": 0.08,
        "BUST": 0.01,
        "RECOVERY": 0.01,
    }

    priors, details = library.runtime_priors(
        macro_values={
            "spread_21d": 2.5,
            "move_21d": 2.2,
            "qqq_ma_ratio": -1.0,
            "liquidity_velocity": -2.5,
            "credit_acceleration": 1.8,
            "dynamic_beta_inertia_matrix": {
                "MID_CYCLE": 0.80,
                "LATE_CYCLE": 0.80,
                "BUST": 0.70,
                "RECOVERY": 0.70,
                "DEFAULT": 0.80,
            },
        }
    )

    assert details["posterior_weight"] > details["transition_weight"]
    assert details["transition_weight"] < 0.35
    assert priors["MID_CYCLE"] < 0.90


def test_runtime_priors_release_stale_bust_memory_during_repair_confirmed_recovery(tmp_path):
    storage_path = tmp_path / "v11_prior_state.json"
    library = PriorKnowledgeBase(
        storage_path=storage_path,
        regimes=["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"],
        bootstrap_regimes=["BUST"] * 10 + ["LATE_CYCLE"] * 4 + ["MID_CYCLE"] * 3 + ["RECOVERY"],
    )
    library.counts = {
        "MID_CYCLE": 17.34328128490912,
        "LATE_CYCLE": 18.566178068448966,
        "BUST": 56.71070629086742,
        "RECOVERY": 7.379834355774499,
    }
    library.last_posterior = {
        "MID_CYCLE": 0.0,
        "LATE_CYCLE": 0.06898884113292443,
        "BUST": 0.5588,
        "RECOVERY": 0.2820,
    }

    without_release, without_details = library.runtime_priors(
        macro_values={
            "spread_21d": 0.9,
            "move_21d": 0.8,
            "qqq_ma_ratio": -0.18,
            "liquidity_velocity": -0.2,
            "credit_acceleration": 0.2,
            "dynamic_beta_inertia_matrix": {
                "MID_CYCLE": 0.80,
                "LATE_CYCLE": 0.80,
                "BUST": 0.70,
                "RECOVERY": 0.70,
                "DEFAULT": 0.80,
            },
        }
    )

    with_release, with_details = library.runtime_priors(
        macro_values={
            "spread_21d": 0.9,
            "move_21d": 0.8,
            "qqq_ma_ratio": -0.18,
            "liquidity_velocity": -0.2,
            "credit_acceleration": 0.2,
            "dynamic_beta_inertia_matrix": {
                "MID_CYCLE": 0.80,
                "LATE_CYCLE": 0.80,
                "BUST": 0.70,
                "RECOVERY": 0.70,
                "DEFAULT": 0.80,
            },
            "price_topology_regime": "RECOVERY",
            "price_topology_confidence": 0.11,
            "price_topology_transition_intensity": 0.94,
            "price_topology_repair_persistence": 0.51,
            "price_topology_recovery_impulse": 0.62,
            "price_topology_damage_memory": 0.88,
            "price_topology_recovery_prob_delta": 0.031,
            "price_topology_recovery_prob_acceleration": 0.014,
        }
    )

    assert without_details["recovery_release_score"] == pytest.approx(0.0)
    assert with_details["recovery_release_score"] > 0.45
    assert with_details["posterior_weight"] < without_details["posterior_weight"]
    assert with_release["RECOVERY"] > without_release["RECOVERY"]
    assert with_release["BUST"] < without_release["BUST"]
    assert with_release["RECOVERY"] > 0.35


def test_runtime_priors_release_recovery_memory_during_late_cycle_transition_window(tmp_path):
    storage_path = tmp_path / "v11_prior_state.json"
    library = PriorKnowledgeBase(
        storage_path=storage_path,
        regimes=["MID_CYCLE", "LATE_CYCLE", "BUST", "RECOVERY"],
        bootstrap_regimes=["BUST"] * 8 + ["LATE_CYCLE"] * 4 + ["RECOVERY"] * 3,
    )
    library.counts = {
        "MID_CYCLE": 12.0,
        "LATE_CYCLE": 16.0,
        "BUST": 30.0,
        "RECOVERY": 18.0,
    }
    library.last_posterior = {
        "MID_CYCLE": 0.16,
        "LATE_CYCLE": 0.31,
        "BUST": 0.13,
        "RECOVERY": 0.40,
    }

    without_release, without_details = library.runtime_priors(
        macro_values={
            "spread_21d": 0.7,
            "move_21d": 0.6,
            "qqq_ma_ratio": -0.14,
            "liquidity_velocity": -0.12,
            "credit_acceleration": 0.18,
            "dynamic_beta_inertia_matrix": {
                "MID_CYCLE": 0.80,
                "LATE_CYCLE": 0.80,
                "BUST": 0.70,
                "RECOVERY": 0.70,
                "DEFAULT": 0.80,
            },
        }
    )

    with_release, with_details = library.runtime_priors(
        macro_values={
            "spread_21d": 0.7,
            "move_21d": 0.6,
            "qqq_ma_ratio": -0.14,
            "liquidity_velocity": -0.12,
            "credit_acceleration": 0.18,
            "dynamic_beta_inertia_matrix": {
                "MID_CYCLE": 0.80,
                "LATE_CYCLE": 0.80,
                "BUST": 0.70,
                "RECOVERY": 0.70,
                "DEFAULT": 0.80,
            },
            "price_topology_regime": "LATE_CYCLE",
            "price_topology_confidence": 0.28,
            "price_topology_transition_intensity": 0.88,
            "price_topology_repair_persistence": 0.41,
            "price_topology_recovery_impulse": 0.36,
            "price_topology_damage_memory": 0.79,
            "price_topology_recovery_prob_delta": -0.008,
            "price_topology_recovery_prob_acceleration": 0.011,
        }
    )

    assert without_details["recovery_release_score"] == pytest.approx(0.0)
    assert with_details["recovery_release_score"] > 0.20
    assert with_release["RECOVERY"] > without_release["RECOVERY"]
    assert with_release["LATE_CYCLE"] < without_release["LATE_CYCLE"]
