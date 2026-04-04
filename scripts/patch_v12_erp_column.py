"""Backfill the v12 Shiller ERP column into an existing canonical dataset."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.collector.global_macro import fetch_historical_shiller_erp_series
from src.collector.macro import fetch_historical_fred_series

INPUT_PATH = Path("data/macro_historical_dump.csv")
OUTPUT_PATH = Path("data/macro_historical_dump.v12.erpfix.csv")


def main() -> None:
    frame = pd.read_csv(INPUT_PATH, parse_dates=["observation_date", "effective_date"])

    real_yield = fetch_historical_fred_series("DFII10")
    if real_yield is None or real_yield.empty:
        raise RuntimeError("Unable to fetch DFII10 for ERP backfill")

    real_yield = real_yield.rename(columns={"DFII10": "real_yield_10y_pct"})
    real_yield["real_yield_10y_pct"] = (
        pd.to_numeric(real_yield["real_yield_10y_pct"], errors="coerce") / 100.0
    )

    erp = fetch_historical_shiller_erp_series(real_yield_frame=real_yield)
    if erp.empty:
        raise RuntimeError("Unable to fetch Shiller ERP history for ERP backfill")

    calendar = pd.to_datetime(frame["observation_date"], errors="coerce")
    erp["effective_date"] = pd.to_datetime(erp["effective_date"], errors="coerce")
    erp = (
        erp.sort_values("effective_date")
        .drop_duplicates("effective_date", keep="last")
        .set_index("effective_date")
    )

    frame["erp_ttm_pct"] = pd.to_numeric(
        erp["erp_ttm_pct"].reindex(calendar, method="ffill"),
        errors="coerce",
    ).to_numpy()
    frame["source_erp_ttm"] = "direct:shiller"

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUTPUT_PATH, index=False)

    print(
        {
            "rows": len(frame),
            "erp_non_null": int(frame["erp_ttm_pct"].notna().sum()),
            "first_erp_date": str(
                frame.loc[frame["erp_ttm_pct"].notna(), "observation_date"].min()
            ),
            "last_erp_date": str(frame.loc[frame["erp_ttm_pct"].notna(), "observation_date"].max()),
        }
    )


if __name__ == "__main__":
    main()
