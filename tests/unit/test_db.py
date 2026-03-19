from __future__ import annotations

import sqlite3

from src.store.db import init_db


def test_init_db_migrates_forward_pe_for_existing_macro_state_table(tmp_path):
    db_path = tmp_path / "signals.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE macro_states (
            date TEXT PRIMARY KEY,
            credit_spread REAL,
            trailing_pe REAL,
            real_yield REAL,
            fcf_yield REAL,
            earnings_revisions_breadth REAL
        )
        """
    )
    conn.commit()
    conn.close()

    migrated = init_db(str(db_path))
    columns = {
        row[1]
        for row in migrated.execute("PRAGMA table_info(macro_states)").fetchall()
    }
    migrated.close()

    assert "forward_pe" in columns
