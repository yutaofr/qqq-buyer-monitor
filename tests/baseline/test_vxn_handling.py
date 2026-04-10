from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from src.engine.baseline.execution import run_baseline_inference


@pytest.fixture
def mock_macro(monkeypatch):
    """Fixture to mock local dependencies."""
    mock = MagicMock()
    monkeypatch.setattr("src.engine.baseline.data_loader.fetch_fred_data", mock)
    # yf.download also needs mocking
    mock_yf = MagicMock()
    monkeypatch.setattr("yfinance.download", mock_yf)
    return mock, mock_yf


def test_vxn_missing_degradation(mock_macro):
    """
    Verify that if ^VXN is missing, calculation enters DEGRADED mode.
    """
    mock_fred, mock_yf = mock_macro

    # Dates from 2010 to 2020 (~2500 business days)
    dates = pd.date_range("2010-01-01", "2020-01-01", freq="B")

    mock_fred.side_effect = lambda sid, **kwargs: pd.DataFrame(
        {"observation_date": dates, sid: np.random.randn(len(dates)) + 100.0}
    )

    # Also mock QQQ and SPY download
    def yf_mock(ticker, **kwargs):
        if ticker == "^VXN":
            return pd.DataFrame()  # Missing

        # We need some 1s in y_sidecar.
        # generate_sidecar_target uses close. 10% drawdown triggers y=1.
        close = np.ones(len(dates)) * 100.0
        # Inject some sharp drops
        close[500:520] = 80.0
        close[1000:1020] = 80.0

        return pd.DataFrame(
            {
                "Close": close,
                "Open": close,
                "High": close,
                "Low": close,
                "Adj Close": close,
            },
            index=dates,
        )

    mock_yf.side_effect = yf_mock

    # 3. Running baseline inference
    # We don't need qqq_hist here as it will fetch via mock_yf
    results = run_baseline_inference()

    # 4. Verify sidecar status
    status = results["sidecar"]["status"]
    assert status == "degraded_missing_vxn", (
        f"Sidecar status expected 'degraded_missing_vxn', got '{status}'"
    )


def test_run_baseline_inference_tolerates_existing_qqq_close_column(monkeypatch):
    dates = pd.date_range("2020-01-01", periods=260, freq="B")
    baseline_data = pd.DataFrame(
        {
            "qqq_close": np.linspace(100.0, 120.0, len(dates)),
            "VIXCLS": np.linspace(18.0, 22.0, len(dates)),
            "^VXN": np.linspace(20.0, 24.0, len(dates)),
        },
        index=dates,
    )
    baseline_data.attrs["metadata"] = {"degraded": []}
    tech = pd.DataFrame(
        {
            "qqq_ma_cross": np.zeros(len(dates)),
            "qqq_close": np.linspace(101.0, 121.0, len(dates)),
        },
        index=dates,
    )

    class _DummyModel:
        coef_ = np.array([[0.5, -0.2, -0.1]])

    monkeypatch.setattr(
        "src.engine.baseline.execution.load_all_baseline_data",
        lambda timeout=10: baseline_data.copy(),
    )
    monkeypatch.setattr(
        "src.engine.baseline.execution.fetch_qqq_technical_signals",
        lambda: tech.copy(),
    )
    monkeypatch.setattr(
        "src.engine.baseline.execution.calculate_composites",
        lambda frame: pd.DataFrame(
            {
                "stress_composite": np.zeros(len(frame)),
                "growth_composite": np.zeros(len(frame)),
                "liquidity_composite": np.zeros(len(frame)),
            },
            index=frame.index,
        ),
    )
    monkeypatch.setattr(
        "src.engine.baseline.execution.calculate_sidecar_composites",
        lambda frame: pd.DataFrame(
            {
                "stress_composite": np.zeros(len(frame)),
                "growth_composite": np.zeros(len(frame)),
                "liquidity_composite": np.zeros(len(frame)),
            },
            index=frame.index,
        ),
    )
    monkeypatch.setattr(
        "src.engine.baseline.execution.generate_baseline_target",
        lambda close, vix: pd.Series(0, index=close.index),
    )
    monkeypatch.setattr(
        "src.engine.baseline.execution.generate_sidecar_target",
        lambda close, vxn: pd.Series(0, index=close.index),
    )
    monkeypatch.setattr(
        "src.engine.baseline.execution.train_baseline_model",
        lambda *args, **kwargs: _DummyModel(),
    )
    monkeypatch.setattr(
        "src.engine.baseline.execution.train_sidecar_model",
        lambda *args, **kwargs: _DummyModel(),
    )
    monkeypatch.setattr(
        "src.engine.baseline.execution.predict_baseline_crisis_prob",
        lambda model, frame: pd.Series([0.2] * len(frame), index=frame.index),
    )
    monkeypatch.setattr(
        "yfinance.download",
        lambda *args, **kwargs: pd.DataFrame(
            {"Close": np.linspace(100.0, 120.0, len(dates))}, index=dates
        ),
    )

    results = run_baseline_inference()

    assert not results.get("status", "").startswith("error:")
    assert results["tractor"]["status"].startswith("success")
    assert results["sidecar"]["status"] == "success"
