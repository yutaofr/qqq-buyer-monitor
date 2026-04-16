import numpy as np
import pandas as pd
import pytest

from src.liquidity.config import load_config
from src.liquidity.engine.pipeline import LiquidityPipeline


@pytest.fixture
def config():
    cfg = load_config()
    cfg["aema"]["circuit_breaker"] = 0.8
    # Turn on Vol Guard to ensure its serialization is covered
    cfg["regime_vol_guard"] = {"enabled": True}
    return cfg


def test_bit_identical_recovery(config):
    """Prove that dumping and reloading state via base64/savez achieves perfect float parity."""
    # Pipeline A: Continuous
    pipeline_a = LiquidityPipeline(config, burn_in=10)

    # Pipeline B: Will be paused and resumed
    pipeline_b = LiquidityPipeline(config, burn_in=10)

    # Generate 100 days of random synthetic market data
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="B")

    ticks = []
    for _ in range(100):
        # We inject some NaNs randomly into the constituent returns and spread inputs
        # to ensure the NaN Marginalization and resilient correlation is exercised.
        rets = np.random.normal(0, 0.01, 50)
        if np.random.rand() < 0.1:
            rets[0:5] = np.nan

        vix = np.random.normal(15, 2)
        if np.random.rand() < 0.05:
            vix = np.nan

        ticks.append({
            "vix": vix,
            "walcl": np.random.normal(4e6, 1e4),
            "rrp": np.random.normal(5e5, 1e4),
            "tga": np.random.normal(3e5, 1e4),
            "sofr": 0.05,
            "constituent_returns": rets
        })

    # ── Phase 1: Run both up to day 50 ──
    for i in range(50):
        pipeline_a.step(dates[i], ticks[i])
        pipeline_b.step(dates[i], ticks[i])

    # Pause Pipeline B. Save its state.
    state_dump = pipeline_b.dump_state()

    # Intentionally ruin Pipeline B's memory to prove it recovers from the dump
    pipeline_b._alloc._weight = 999.0
    pipeline_b._bocpd._probs[:] = 0.0

    # Restore Pipeline B
    pipeline_b.load_state(state_dump)

    # ── Phase 2: Run both parallel from 51 to 100 and compare exactly ──
    for i in range(50, 100):
        wa, log_a = pipeline_a.step(dates[i], ticks[i])
        wb, log_b = pipeline_b.step(dates[i], ticks[i])

        assert wa == wb, f"Weight divergence at step {i}: {wa} != {wb}"
        assert log_a["p_cp"] == log_b["p_cp"], f"P_cp divergence at step {i}"
        assert log_a["s_t"] == log_b["s_t"], f"AEMA divergence at step {i}"
        assert np.isclose(log_a["vol_guard_cap"], log_b["vol_guard_cap"]), f"Vol guard cap divergence at step {i}"

        # Assert bit-identical floats on the probabilities matrix
        np.testing.assert_array_equal(pipeline_a._bocpd._probs, pipeline_b._bocpd._probs)
        np.testing.assert_array_equal(pipeline_a._bocpd._stats, pipeline_b._bocpd._stats)
