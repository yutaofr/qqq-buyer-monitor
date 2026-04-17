from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd


@dataclass(frozen=True)
class ObservationEvent:
    """Execution-layer event emitted after an engine runtime snapshot is produced."""

    raw_t0_data: pd.DataFrame
    runtime: dict[str, Any]
    baseline_result: dict[str, Any] | None = None

    @property
    def date(self) -> str:
        if not self.raw_t0_data.empty:
            dt = pd.Timestamp(self.raw_t0_data.index[-1]).normalize()
            return dt.date().isoformat()
        runtime_date = self.runtime.get("date")
        if runtime_date is not None:
            return pd.Timestamp(runtime_date).normalize().date().isoformat()
        return ""


class TelemetryObserver(Protocol):
    def observe(self, event: ObservationEvent) -> None:
        """Record telemetry outside the observed engine."""


class TelemetrySink(Protocol):
    def emit(self, row: dict[str, Any]) -> None:
        """Persist one telemetry row."""


class InMemoryTelemetrySink:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def emit(self, row: dict[str, Any]) -> None:
        self.rows.append(dict(row))


class V16TelemetrySidecar:
    """Extract V16 telemetry from execution events without mutating the engine."""

    def __init__(self, *, sink: TelemetrySink, engine_version: str = "v16.telemetry") -> None:
        self._sink = sink
        self._engine_version = str(engine_version)

    def observe(self, event: ObservationEvent) -> None:
        diagnostics = dict(event.runtime.get("v13_4_diagnostics", {}) or {})
        dead_features = list(diagnostics.get("dead_features", []) or [])
        self._sink.emit(
            {
                "date": event.date,
                "engine_version": self._engine_version,
                "mahalanobis_dist": float(diagnostics.get("mahalanobis_dist", 0.0) or 0.0),
                "dead_features_count": int(len(dead_features)),
                "dead_features": dead_features,
            }
        )


class TelemetryObservedEngine:
    """Decorator that preserves the wrapped engine API and emits observation events."""

    def __init__(self, *, engine: Any, observers: list[TelemetryObserver] | None = None) -> None:
        self._engine = engine
        self._observers = list(observers or [])

    def daily_run(self, raw_t0_data: pd.DataFrame, baseline_result: dict | None = None) -> dict:
        runtime = self._engine.daily_run(raw_t0_data, baseline_result=baseline_result)
        event = ObservationEvent(
            raw_t0_data=raw_t0_data,
            runtime=runtime,
            baseline_result=baseline_result,
        )
        for observer in self._observers:
            observer.observe(event)
        return runtime
