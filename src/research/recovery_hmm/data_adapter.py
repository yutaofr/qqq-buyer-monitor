"""Strict local-data adapter for the recovery HMM shadow research track."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.research.recovery_hmm.feature_space import REQUIRED_COLUMNS


@dataclass(frozen=True)
class RecoveryHmmReadinessReport:
    frame: pd.DataFrame
    coverage: dict[str, float]
    mapped_columns: tuple[str, ...]
    missing_columns: tuple[str, ...]
    incomplete_columns: tuple[str, ...]
    source_notes: dict[str, str]

    @property
    def is_ready(self) -> bool:
        return not self.missing_columns

    def to_dict(self) -> dict[str, object]:
        return {
            "is_ready": self.is_ready,
            "coverage": self.coverage,
            "mapped_columns": list(self.mapped_columns),
            "missing_columns": list(self.missing_columns),
            "incomplete_columns": list(self.incomplete_columns),
            "source_notes": self.source_notes,
            "row_count": int(len(self.frame)),
            "start_date": self.frame.index.min().date().isoformat()
            if not self.frame.empty
            else None,
            "end_date": self.frame.index.max().date().isoformat() if not self.frame.empty else None,
        }


def _load_macro_dump(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["observation_date"] = pd.to_datetime(frame["observation_date"], errors="coerce")
    frame = frame.dropna(subset=["observation_date"]).set_index("observation_date").sort_index()
    return frame


def build_local_readiness_report(macro_dump_path: str | Path) -> RecoveryHmmReadinessReport:
    macro = _load_macro_dump(macro_dump_path)
    frame = pd.DataFrame(index=macro.index)
    source_notes: dict[str, str] = {}

    if "credit_spread_bps" in macro.columns:
        frame["hy_ig_spread"] = pd.to_numeric(macro["credit_spread_bps"], errors="coerce") / 100.0
        source_notes["hy_ig_spread"] = "mapped from macro_historical_dump.credit_spread_bps / 100"

    if "real_yield_10y_pct" in macro.columns:
        frame["real_yield_10y"] = (
            pd.to_numeric(macro["real_yield_10y_pct"], errors="coerce") * 100.0
        )
        source_notes["real_yield_10y"] = (
            "mapped from macro_historical_dump.real_yield_10y_pct * 100"
        )

    coverage = {
        column: float(frame[column].notna().mean()) if column in frame.columns else 0.0
        for column in sorted(REQUIRED_COLUMNS)
    }
    missing = tuple(sorted(column for column in REQUIRED_COLUMNS if coverage[column] <= 0.0))
    incomplete = tuple(sorted(column for column, ratio in coverage.items() if 0.0 < ratio < 1.0))
    return RecoveryHmmReadinessReport(
        frame=frame,
        coverage=coverage,
        mapped_columns=tuple(sorted(frame.columns)),
        missing_columns=missing,
        incomplete_columns=incomplete,
        source_notes=source_notes,
    )
