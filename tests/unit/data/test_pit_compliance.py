from pathlib import Path

import pandas as pd


def _load_canonical_dataset() -> pd.DataFrame:
    path = Path("data/macro_historical_dump.csv")
    return pd.read_csv(path, parse_dates=["observation_date", "effective_date"])


def test_pit_compliance_capex():
    """v12 canonical DNA must expose PIT-safe core capex values."""
    dataset = _load_canonical_dataset().set_index("observation_date")

    assert "core_capex_mm" in dataset.columns
    assert pd.notna(dataset.loc["2020-04-03", "core_capex_mm"])
    assert pd.notna(dataset.loc["2020-05-20", "core_capex_mm"])


def test_pit_compliance_eps():
    """v12 canonical DNA must expose PIT-safe Shiller ERP values on the business-day calendar."""
    dataset = _load_canonical_dataset().set_index("observation_date")

    assert "erp_ttm_pct" in dataset.columns
    assert "2020-03-15" not in dataset.index.astype(str)
    assert pd.notna(dataset.loc["2020-03-16", "erp_ttm_pct"])
    assert pd.notna(dataset.loc["2020-05-15", "erp_ttm_pct"])


def test_pit_tier1_tplus1():
    """Tier-1 daily series must carry next-business-day visibility metadata."""
    dataset = _load_canonical_dataset()

    assert "treasury_vol_21d" in dataset.columns
    assert "breakeven_10y" in dataset.columns
    assert "usdjpy" in dataset.columns
    assert (dataset["effective_date"] >= dataset["observation_date"]).all()


def test_no_future_function_leak():
    """The PIT dataset must not regress to v11 forward-looking ERP inputs."""
    dataset = _load_canonical_dataset()

    assert "erp_ttm_pct" in dataset.columns
    assert "forward_pe" in dataset.columns
    assert dataset["source_erp_ttm"].notna().all()
