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
    assert storage_path.exists()


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
    assert reloaded.runtime_priors()["BUST"] > reloaded.runtime_priors()["MID_CYCLE"]

    payload = json.loads(storage_path.read_text())
    assert payload["last_observation_date"] == "2026-03-30"
