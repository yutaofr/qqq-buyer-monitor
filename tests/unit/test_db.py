from __future__ import annotations

import json
import sqlite3
from datetime import date

from src.models import SignalResult, TargetAllocationState
from src.store.db import CURRENT_SCHEMA_VERSION, init_db, load_history, save_signal


def test_save_and_load_signal(tmp_path):
    db_path = tmp_path / "signals.db"
    result = SignalResult(
        date=date(2026, 3, 19),
        price=402.0,
        target_beta=0.90,
        probabilities={"MID_CYCLE": 1.0},
        priors={"MID_CYCLE": 1.0},
        entropy=0.0,
        stable_regime="MID_CYCLE",
        target_allocation=TargetAllocationState(0.10, 0.90, 0.0, 0.90),
        logic_trace=[],
        explanation="test",
    )

    save_signal(result, path=str(db_path))
    history = load_history(n=1, path=str(db_path))

    assert len(history) == 1
    assert history[0]["date"] == "2026-03-19"
    assert history[0]["target_beta"] == 0.90
    assert history[0]["price"] == 402.0


def test_save_and_load_signal_persists_posterior_and_execution_regime_surfaces(tmp_path):
    db_path = tmp_path / "signals.db"
    result = SignalResult(
        date=date(2026, 4, 9),
        price=610.19,
        target_beta=0.62,
        probabilities={"BUST": 0.47, "LATE_CYCLE": 0.45, "MID_CYCLE": 0.05, "RECOVERY": 0.03},
        priors={"MID_CYCLE": 0.36, "LATE_CYCLE": 0.26, "BUST": 0.20, "RECOVERY": 0.18},
        entropy=0.71,
        stable_regime="BUST",
        target_allocation=TargetAllocationState(0.38, 0.62, 0.0, 0.62),
        logic_trace=[],
        explanation="test",
        metadata={"posterior_regime": "BUST", "execution_regime": "MID_CYCLE"},
    )

    save_signal(result, path=str(db_path))
    history = load_history(n=1, path=str(db_path))

    assert history[0]["posterior_regime"] == "BUST"
    assert history[0]["execution_regime"] == "MID_CYCLE"
    assert history[0]["stable_regime"] == "BUST"


def test_init_db_writes_schema_version_meta(tmp_path):
    db_path = tmp_path / "signals.db"

    conn = init_db(str(db_path))
    schema_version = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    conn.close()

    assert schema_version == (CURRENT_SCHEMA_VERSION,)


def test_init_db_rebuilds_legacy_signals_schema_and_sets_version(tmp_path):
    db_path = tmp_path / "signals.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE signals (
            date TEXT PRIMARY KEY,
            price REAL NOT NULL,
            json_blob TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()

    conn = init_db(str(db_path))
    columns = {row[1] for row in conn.execute("PRAGMA table_info(signals)").fetchall()}
    schema_version = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    conn.close()

    assert "target_beta" in columns
    assert schema_version == (CURRENT_SCHEMA_VERSION,)


def test_load_history_reads_legacy_rows_without_mutating_schema(tmp_path):
    db_path = tmp_path / "signals.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE signals (
            date TEXT PRIMARY KEY,
            price REAL NOT NULL,
            json_blob TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT INTO signals (date, price, json_blob) VALUES (?, ?, ?)",
        (
            "2026-04-09",
            610.19,
            json.dumps(
                {
                    "date": "2026-04-09",
                    "price": 610.19,
                    "target_beta": 0.62,
                    "probabilities": {"LATE_CYCLE": 1.0},
                    "priors": {"LATE_CYCLE": 1.0},
                    "entropy": 0.0,
                    "stable_regime": "LATE_CYCLE",
                    "target_allocation": {
                        "target_cash_pct": 0.38,
                        "target_qqq_pct": 0.62,
                        "target_qld_pct": 0.0,
                        "target_beta": 0.62,
                    },
                    "logic_trace": [],
                    "explanation": "legacy history",
                    "metadata": {},
                }
            ),
        ),
    )
    conn.commit()
    conn.close()

    history = load_history(n=5, path=str(db_path))

    assert len(history) == 1
    assert history[0]["date"] == "2026-04-09"

    conn = sqlite3.connect(str(db_path))
    columns = {row[1] for row in conn.execute("PRAGMA table_info(signals)").fetchall()}
    count = conn.execute("SELECT count(*) FROM signals").fetchone()[0]
    conn.close()

    assert "target_beta" not in columns
    assert count == 1


def test_init_db_migrates_legacy_signals_schema_without_losing_rows(tmp_path):
    db_path = tmp_path / "signals.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE signals (
            date TEXT PRIMARY KEY,
            price REAL NOT NULL,
            json_blob TEXT NOT NULL
        )
        """
    )
    rows = [
        ("2026-04-09", 610.19, 0.62),
        ("2026-04-10", 611.07, 0.58),
    ]
    for record_date, price, target_beta in rows:
        conn.execute(
            "INSERT INTO signals (date, price, json_blob) VALUES (?, ?, ?)",
            (
                record_date,
                price,
                json.dumps(
                    {
                        "date": record_date,
                        "price": price,
                        "target_beta": target_beta,
                        "probabilities": {"LATE_CYCLE": 1.0},
                        "priors": {"LATE_CYCLE": 1.0},
                        "entropy": 0.0,
                        "stable_regime": "LATE_CYCLE",
                        "target_allocation": {
                            "target_cash_pct": 1.0 - target_beta,
                            "target_qqq_pct": target_beta,
                            "target_qld_pct": 0.0,
                            "target_beta": target_beta,
                        },
                        "logic_trace": [],
                        "explanation": "legacy migration",
                        "metadata": {},
                    }
                ),
            ),
        )
    conn.commit()
    conn.close()

    conn = init_db(str(db_path))
    columns = {row[1] for row in conn.execute("PRAGMA table_info(signals)").fetchall()}
    migrated_rows = conn.execute(
        "SELECT date, target_beta, price FROM signals ORDER BY date"
    ).fetchall()
    conn.close()

    assert "target_beta" in columns
    assert migrated_rows == [
        ("2026-04-09", 0.62, 610.19),
        ("2026-04-10", 0.58, 611.07),
    ]
