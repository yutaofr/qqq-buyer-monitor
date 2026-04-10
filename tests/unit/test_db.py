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
