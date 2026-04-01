from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sklearn.naive_bayes import GaussianNB

from src.engine.v11.conductor import V11Conductor


@pytest.fixture
def mock_audit_data():
    from src.engine.v11.probability_seeder import ProbabilitySeeder
    seeder = ProbabilitySeeder()
    return {
        "base_betas": {"MID_CYCLE": 1.0, "LATE_CYCLE": 0.8, "BUST": 0.0, "RECOVERY": 1.2},
        "regime_sharpes": {"MID_CYCLE": 1.0, "LATE_CYCLE": 0.5, "BUST": -1.0, "RECOVERY": 1.5},
        "model_hyperparameters": {
            "gaussian_nb_var_smoothing": 1e-2,
            "posterior_mode": "runtime_reweight",
            "sentinel": {
                "alpha_decay": 0.05,
                "span_base": 252,
                "vol_floor": 0.005
            }
        },
        "feature_contract": {
            "seeder_config_hash": seeder.contract_hash(),
            "feature_names": seeder.feature_names()
        }
    }

def test_conductor_integration_with_sentinel(mock_audit_data):
    # Mocking files and dependencies
    with patch("builtins.open", MagicMock()):
        with patch("json.load", return_value=mock_audit_data):
            with patch("src.engine.v11.conductor.Path.exists", return_value=True):
                with patch("src.engine.v11.conductor.PriorKnowledgeBase") as mock_prior_kb:
                    # Configure mock prior_kb
                    mock_prior_instance = mock_prior_kb.return_value
                    mock_prior_instance.get_execution_state.return_value = {}
                    mock_prior_instance.runtime_priors.return_value = ({}, {})
                    mock_prior_instance.current_priors.return_value = {}

                    with patch("src.engine.v11.conductor.V11Conductor._initialize_model") as mock_init_model:
                        mock_init_model.return_value = MagicMock(spec=GaussianNB)
                        mock_init_model.return_value.classes_ = ["BOOM", "MID_CYCLE", "LATE_CYCLE", "BUST"]

                        with patch("pandas.read_csv") as mock_read_csv:
                            # Mock regime history and macro history
                            mock_read_csv.return_value = pd.DataFrame({
                                "observation_date": pd.to_datetime(["2024-01-01"]),
                                "regime": ["MID_CYCLE"],
                                "effective_date": pd.to_datetime(["2024-01-01"])
                            })

                            conductor = V11Conductor()

                            # Mock price history for Sentinel
                            price_hist = pd.DataFrame({
                                "Close": [100.0, 101.0],
                                "Volume": [1000, 1100]
                            }, index=pd.to_datetime(["2024-01-01", "2024-01-02"]))

                            # Mock raw_t0_data
                            raw_t0 = pd.DataFrame([{
                                "observation_date": "2024-01-02",
                                "effective_date": "2024-01-02",
                                "credit_spread_bps": 350.0
                            }])
                            raw_t0.attrs["history"] = price_hist

                            # Mock dependencies of daily_run
                            conductor.seeder.generate_features = MagicMock(return_value=pd.DataFrame({"f1": [0.5], "f2": [0.5]}, index=["2024-01-02"]))
                            conductor.inference_engine.infer_gaussian_nb_posterior = MagicMock(return_value={"MID_CYCLE": 1.0})

                            # Run it
                            res = conductor.daily_run(raw_t0)

                            assert "target_beta" in res
                            assert "raw_target_beta" in res
                            # Since MID_CYCLE beta is 1.0, and JSD multiplier can go up to ~2.0
                            assert 0.5 < res["target_beta"] <= 2.0
