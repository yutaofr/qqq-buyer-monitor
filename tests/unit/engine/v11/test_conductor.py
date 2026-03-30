from __future__ import annotations

import json

import pandas as pd
import pytest

from src.engine.v11.conductor import V11Conductor


def test_conductor_persists_posterior_back_into_prior_state(tmp_path):
    regime_path = tmp_path / "regimes.csv"
    macro_path = tmp_path / "macro.csv"
    prior_path = tmp_path / "prior_state.json"

    dates = pd.date_range("2024-01-01", periods=320, freq="D")
    macro_df = pd.DataFrame(
        {
            "observation_date": dates,
            "erp_pct": [0.03 + i * 0.0001 for i in range(len(dates))],
            "real_yield_10y_pct": [0.015 + i * 0.00005 for i in range(len(dates))],
            "credit_spread_bps": [350.0 + (i % 25) for i in range(len(dates))],
            "net_liquidity_usd_bn": [4000.0 + i * 2.0 for i in range(len(dates))],
        }
    )
    regime_df = pd.DataFrame(
        {
            "observation_date": dates,
            "regime": ["MID_CYCLE"] * 160 + ["LATE_CYCLE"] * 80 + ["BUST"] * 80,
        }
    )

    macro_df.to_csv(macro_path, index=False)
    regime_df.to_csv(regime_path, index=False)

    conductor = V11Conductor(
        macro_data_path=str(macro_path),
        regime_data_path=str(regime_path),
        prior_state_path=str(prior_path),
    )

    t0 = macro_df.tail(1).set_index("observation_date")
    result = conductor.daily_run(t0)

    assert sum(result["probabilities"].values()) == pytest.approx(1.0)
    assert prior_path.exists()

    payload = json.loads(prior_path.read_text())
    assert payload["last_observation_date"] == str(t0.index[-1].date())
    assert payload["last_posterior"]
    assert "bucket_evidence" in payload["execution_state"]
