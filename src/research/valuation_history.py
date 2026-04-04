"""Historical valuation proxy ingestion for v10 research datasets."""

from __future__ import annotations

import re
import subprocess

import pandas as pd
from bs4 import BeautifulSoup

DAMODARAN_HISTIMPL_URL = (
    "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histimpl.html"
)
DAMODARAN_SOURCE_TAG = "damodaran:histimpl"
_TARGET_HEADERS = {"year", "earnings yield", "implied erp (fcfe)"}


def _normalize_header(value: str) -> str:
    return " ".join(value.split()).strip().lower()


def _extract_float(value: str) -> float | None:
    match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
    if match is None:
        return None
    return float(match.group(0))


def _extract_year(value: str) -> int | None:
    match = re.search(r"(19|20)\d{2}", value)
    if match is None:
        return None
    return int(match.group(0))


def _find_target_table(soup: BeautifulSoup):
    for table in soup.find_all("table"):
        header_cells = table.find("tr")
        if header_cells is None:
            continue
        headers = {
            _normalize_header(cell.get_text(" ", strip=True))
            for cell in header_cells.find_all(["th", "td"])
        }
        if _TARGET_HEADERS.issubset(headers):
            return table
    raise ValueError("Could not find Damodaran historical implied ERP table")


def parse_damodaran_histimpl_html(html: str) -> pd.DataFrame:
    """Parse Damodaran's historical implied ERP table into canonical valuation rows."""
    soup = BeautifulSoup(html, "html.parser")
    table = _find_target_table(soup)
    rows: list[dict[str, object]] = []

    raw_headers = [
        _normalize_header(cell.get_text(" ", strip=True))
        for cell in table.find("tr").find_all(["th", "td"])
    ]
    header_index = {name: idx for idx, name in enumerate(raw_headers)}
    year_idx = header_index["year"]
    earnings_yield_idx = header_index["earnings yield"]
    erp_idx = header_index["implied erp (fcfe)"]

    for tr in table.find_all("tr")[1:]:
        cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"])]
        if len(cells) <= max(year_idx, earnings_yield_idx, erp_idx):
            continue

        year = _extract_year(cells[year_idx])
        earnings_yield_pct = _extract_float(cells[earnings_yield_idx])
        erp_pct = _extract_float(cells[erp_idx])
        if year is None or earnings_yield_pct is None or erp_pct is None or earnings_yield_pct <= 0:
            continue

        observation_date = pd.Timestamp(year=year, month=12, day=31)
        rows.append(
            {
                "observation_date": observation_date,
                "effective_date": observation_date + pd.Timedelta(days=1),
                "forward_pe": 100.0 / earnings_yield_pct,
                "erp_pct": erp_pct,
                "source_forward_pe": DAMODARAN_SOURCE_TAG,
                "source_erp": DAMODARAN_SOURCE_TAG,
            }
        )

    if not rows:
        raise ValueError(
            "No usable valuation rows parsed from Damodaran historical implied ERP table"
        )

    frame = pd.DataFrame(rows)
    frame = frame.sort_values("observation_date").drop_duplicates(
        subset=["observation_date"],
        keep="last",
    )
    frame = frame.reset_index(drop=True)
    return frame.loc[
        :,
        [
            "observation_date",
            "effective_date",
            "forward_pe",
            "erp_pct",
            "source_forward_pe",
            "source_erp",
        ],
    ]


def fetch_historical_valuation_proxy(timeout: int = 20) -> pd.DataFrame:
    """Fetch the historical valuation proxy used to supplement the macro history."""
    try:
        completed = subprocess.run(
            [
                "curl",
                "-sS",
                "-L",
                "--max-time",
                str(timeout),
                DAMODARAN_HISTIMPL_URL,
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout + 5,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Failed to fetch Damodaran historical implied ERP table") from exc

    return parse_damodaran_histimpl_html(completed.stdout)
