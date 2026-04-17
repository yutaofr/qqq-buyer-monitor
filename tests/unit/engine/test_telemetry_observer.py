from __future__ import annotations

import pandas as pd

from src.engine.telemetry_observer import (
    InMemoryTelemetrySink,
    TelemetryObservedEngine,
    V16TelemetrySidecar,
)


def test_telemetry_observed_engine_delegates_runtime_unchanged_and_notifies_observer():
    class FakeEngine:
        def __init__(self):
            self.calls = []

        def daily_run(self, raw_t0_data, baseline_result=None):
            self.calls.append((raw_t0_data, baseline_result))
            return {
                "target_beta": 0.75,
                "v13_4_diagnostics": {
                    "mahalanobis_dist": 4.2,
                    "dead_features": ["liquidity_velocity"],
                },
            }

    raw = pd.DataFrame(
        [{"credit_spread_bps": 410.0}],
        index=pd.DatetimeIndex([pd.Timestamp("2023-10-03")], name="observation_date"),
    )
    sink = InMemoryTelemetrySink()
    sidecar = V16TelemetrySidecar(sink=sink, engine_version="v16.audit")
    engine = FakeEngine()

    observed = TelemetryObservedEngine(engine=engine, observers=[sidecar])
    runtime = observed.daily_run(raw, baseline_result={"source": "cached"})

    assert runtime["target_beta"] == 0.75
    assert not hasattr(engine, "v16_telemetry")
    assert len(engine.calls) == 1
    assert sink.rows == [
        {
            "date": "2023-10-03",
            "engine_version": "v16.audit",
            "mahalanobis_dist": 4.2,
            "dead_features_count": 1,
            "dead_features": ["liquidity_velocity"],
        }
    ]
