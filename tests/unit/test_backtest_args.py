import pytest
from src.backtest import main

def test_backtest_can_parse_no_canonical_pipeline_flag():
    # Test that --no-canonical-pipeline is recognized to DISABLE it
    args = ["--evaluation-start", "2026-01-01", "--no-canonical-pipeline", "--acceptance", "--price-cache-path", "data/test.csv", "--price-end-date", "2026-03-31"]
    import unittest.mock as mock
    with mock.patch("src.backtest.run_v11_audit") as mock_audit:
        main(args)
        called_args, called_kwargs = mock_audit.call_args
        experiment_config = called_kwargs.get("experiment_config", {})
        assert experiment_config.get("use_canonical_pipeline") is False

def test_backtest_canonical_pipeline_defaults_to_true():
    args = ["--evaluation-start", "2026-01-01", "--acceptance", "--price-cache-path", "data/test.csv", "--price-end-date", "2026-03-31"]
    import unittest.mock as mock
    with mock.patch("src.backtest.run_v11_audit") as mock_audit:
        main(args)
        called_args, called_kwargs = mock_audit.call_args
        experiment_config = called_kwargs.get("experiment_config", {})
        assert experiment_config.get("use_canonical_pipeline", False) is True
