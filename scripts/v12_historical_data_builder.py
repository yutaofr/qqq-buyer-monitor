"""Build the canonical v12 PIT-safe macro dataset."""

from __future__ import annotations

from pathlib import Path

from src.research.data_contracts import summarize_historical_macro_coverage
from src.research.historical_macro_builder import build_historical_macro_dataset

DEFAULT_OUTPUT_PATH = Path("data/macro_historical_dump.csv")


def main() -> None:
    frame = build_historical_macro_dataset(
        output_path=DEFAULT_OUTPUT_PATH,
        base_dataset_path=DEFAULT_OUTPUT_PATH,
    )
    summary = summarize_historical_macro_coverage(frame)
    print(
        "Built v12 macro dataset:",
        {
            "rows": len(frame),
            "first_observation_date": summary["first_observation_date"],
            "last_observation_date": summary["last_observation_date"],
        },
    )


if __name__ == "__main__":
    main()
