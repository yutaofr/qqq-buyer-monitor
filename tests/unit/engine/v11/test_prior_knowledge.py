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

    library = PriorKnowledgeBase(storage_path=storage_path, bootstrap_regimes=bootstrap_history)

    assert library.counts["MID_CYCLE"] == 4.0
    assert library.counts["LATE_CYCLE"] == pytest.approx(1.0)
    assert library.transition_counts["MID_CYCLE"]["BUST"] == pytest.approx(1.0)
    assert library.execution_state["stable_regime"] == "RECOVERY"
    assert library.execution_state["regime_evidence"] == pytest.approx(0.0)
    payload = json.loads(storage_path.read_text())
    assert payload["bootstrap_fingerprint"].startswith("sha256:")
    assert payload["execution_state"]["stable_regime"] == "RECOVERY"


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
