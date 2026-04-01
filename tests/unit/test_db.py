from __future__ import annotations

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


def test_init_db_writes_schema_version_meta(tmp_path):
    db_path = tmp_path / "signals.db"

    conn = init_db(str(db_path))
    schema_version = conn.execute(
        "SELECT value FROM meta WHERE key = 'schema_version'"
    ).fetchone()
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
    schema_version = conn.execute(
        "SELECT value FROM meta WHERE key = 'schema_version'"
    ).fetchone()
    conn.close()

    assert "target_beta" in columns
    assert schema_version == (CURRENT_SCHEMA_VERSION,)
