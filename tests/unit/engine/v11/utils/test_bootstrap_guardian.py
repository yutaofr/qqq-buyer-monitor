import json
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

# We expect the implementation to be imported from here:
from src.engine.v11.utils.bootstrap_guardian import BootstrapGuardian
from src.engine.v11.utils.bootstrap_models import BootstrapAuditReport


@pytest.fixture
def mock_filesystem():
    """Setup a temporary filesystem mimicking production data structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        # 1. Macro CSV - creating a gap between 2026-04-02 and 2026-04-08
        macro_path = base / "macro_historical_dump.csv"
        dates = pd.date_range(start="2020-01-01", end="2026-04-02", freq="B")
        macro_df = pd.DataFrame({"observation_date": dates.astype(str)})
        # deliberately add a disconnected date
        macro_df = pd.concat(
            [macro_df, pd.DataFrame({"observation_date": ["2026-04-08"]})], ignore_index=True
        )
        macro_df.to_csv(macro_path, index=False)

        # 2. Price Cache - stale, ending on 2026-03-27
        price_path = base / "qqq_history_cache.csv"
        price_dates = pd.date_range(start="2020-01-01", end="2026-03-27", freq="B")
        price_df = pd.DataFrame(
            {
                "Date": [d.strftime("%Y-%m-%d 00:00:00-04:00") for d in price_dates],
                "Close": [300.0] * len(price_dates),
                "Volume": [50000000.0] * len(price_dates),
            }
        )
        price_df.to_csv(price_path, index=False)

        # 3. Seed Prior
        seed_path = base / "v13_6_cold_start_seed.json"
        with open(seed_path, "w") as f:
            json.dump({"last_observation_date": "2026-03-31", "counts": {"MID_CYCLE": 100}}, f)

        yield {
            "macro_csv": str(macro_path),
            "price_csv": str(price_path),
            "seed_json": str(seed_path),
            "base_dir": tmpdir,
        }


def test_audit_macro_gap_detection(mock_filesystem):
    """RED: Guardian should detect missing business days (e.g., 04-03 to 04-07)."""
    guardian = BootstrapGuardian(
        macro_csv_path=mock_filesystem["macro_csv"],
        price_cache_path=mock_filesystem["price_csv"],
        cold_start_seed_path=mock_filesystem["seed_json"],
    )

    report: BootstrapAuditReport = guardian.audit()
    assert report.is_healthy is False, "Should not be healthy with a 3-business-day gap"

    gaps = report.macro_gaps
    assert len(gaps) > 0, "Should detect at least one gap interval"

    # We missed Apr 6 (Mon), Apr 7 (Tue) between Apr 2 and Apr 8
    # Note: 2026-04-03 is Good Friday (NYSE closed)
    missing_dates = [gap.missing_date.isoformat() for gap in gaps]
    assert "2026-04-06" in missing_dates
    assert "2026-04-07" in missing_dates


def test_audit_price_cache_staleness(mock_filesystem):
    """RED: Price cache should be flagged as stale."""
    guardian = BootstrapGuardian(
        macro_csv_path=mock_filesystem["macro_csv"],
        price_cache_path=mock_filesystem["price_csv"],
        cold_start_seed_path=mock_filesystem["seed_json"],
    )

    report = guardian.audit()
    assert report.price_cache_staleness.days_stale > 0
    assert report.price_cache_staleness.last_date == date(2026, 3, 27)


def test_repair_backfill_resolves_gaps(mock_filesystem, monkeypatch):
    """RED: Guardian.repair() should use local price cache only and remove the gap."""
    guardian = BootstrapGuardian(
        macro_csv_path=mock_filesystem["macro_csv"],
        price_cache_path=mock_filesystem["price_csv"],
        cold_start_seed_path=mock_filesystem["seed_json"],
    )

    # Seed the local price cache with the dates needed for backfill.
    dates = pd.date_range("2026-03-27", "2026-04-08", freq="B")
    pd.DataFrame(
        {
            "Date": [d.strftime("%Y-%m-%d 00:00:00-04:00") for d in dates],
            "Close": [600.0] * len(dates),
            "Volume": [60000000.0] * len(dates),
        }
    ).to_csv(mock_filesystem["price_csv"], index=False)

    monkeypatch.setattr(
        "src.collector.price.fetch_price_data",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("live fetch forbidden")),
    )

    report = guardian.audit()
    result = guardian.repair(report)

    assert result.total_rows_added == 2  # Should have added 2 business days (04-06, 04-07)

    # Re-audit should now be healthy or at least not have macro gaps
    report2 = guardian.audit()
    assert len(report2.macro_gaps) == 0


def test_1260_day_window_restriction(mock_filesystem):
    """RED: It should only care about gaps within the last 1260 business days."""
    # Let's create an ancient gap > 1260 days ago
    df = pd.read_csv(mock_filesystem["macro_csv"])

    # Ancient gap in 2020: omit 2020-03-16
    df = df[df["observation_date"] != "2020-03-16"]
    df.to_csv(mock_filesystem["macro_csv"], index=False)

    guardian = BootstrapGuardian(
        macro_csv_path=mock_filesystem["macro_csv"],
        price_cache_path=mock_filesystem["price_csv"],
        cold_start_seed_path=mock_filesystem["seed_json"],
    )
    report = guardian.audit()

    missing_dates = [gap.missing_date.isoformat() for gap in report.macro_gaps]

    # Still complains about 04-06
    assert "2026-04-06" in missing_dates
    # *Does NOT* complain about 2020-03-16 because it's older than 1260 trading days from 2026-04-08
    assert "2020-03-16" not in missing_dates
