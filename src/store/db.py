"""SQLite persistence layer for v11 Bayesian signal records."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import date
from pathlib import Path

from src.models import SignalResult

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.environ.get("QQQ_DB_PATH", "data/signals.db")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS signals (
    date TEXT PRIMARY KEY,
    target_beta REAL NOT NULL,
    price REAL NOT NULL,
    json_blob TEXT NOT NULL
);
"""

CREATE_MACRO_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS macro_states (
    date TEXT PRIMARY KEY,
    credit_spread REAL,
    forward_pe REAL,
    real_yield REAL
);
"""

CREATE_RUNTIME_INPUTS_SQL = """
CREATE TABLE IF NOT EXISTS runtime_inputs (
    date TEXT PRIMARY KEY,
    available_new_cash REAL,
    rolling_drawdown REAL
);
"""

def init_db(path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Initialise (or open) the SQLite database and create the table."""
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))

    # Force Schema Sync for V11 (Destructive Cleanup)
    cursor = conn.execute("PRAGMA table_info(signals)")
    columns = {row[1] for row in cursor.fetchall()}
    if columns and "target_beta" not in columns:
        logger.warning("Legacy schema detected in %s. Dropping for V11 convergence.", path)
        conn.execute("DROP TABLE IF EXISTS signals")

    conn.execute(CREATE_TABLE_SQL)
    conn.execute(CREATE_MACRO_TABLE_SQL)
    conn.execute(CREATE_RUNTIME_INPUTS_SQL)
    conn.commit()
    return conn


def _to_json_dict(result: SignalResult) -> dict:
    """Serialise a SignalResult to a JSON-compatible dict."""
    return {
        "date": result.date.isoformat(),
        "price": float(result.price),
        "target_beta": float(result.target_beta),
        "probabilities": {k: float(v) for k, v in result.probabilities.items()},
        "priors": {k: float(v) for k, v in result.priors.items()},
        "entropy": float(result.entropy),
        "stable_regime": result.stable_regime,
        "target_allocation": result.target_allocation.to_dict(),
        "logic_trace": result.logic_trace,
        "explanation": result.explanation,
        "metadata": result.metadata,
    }


def save_signal(result: SignalResult, path: str = DEFAULT_DB_PATH) -> None:
    """Upsert a SignalResult into the database."""
    conn = init_db(path)
    blob = _to_json_dict(result)
    conn.execute(
        """
        INSERT INTO signals (date, target_beta, price, json_blob)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            target_beta=excluded.target_beta,
            price=excluded.price,
            json_blob=excluded.json_blob
        """,
        (
            result.date.isoformat(),
            result.target_beta,
            result.price,
            json.dumps(blob, ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()


def load_history(n: int = 30, path: str = DEFAULT_DB_PATH) -> list[dict]:
    """Return the most recent n signal records as raw dicts."""
    if not Path(path).exists():
        return []
    conn = init_db(path)
    rows = conn.execute(
        "SELECT json_blob FROM signals ORDER BY date DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()
    return [json.loads(row[0]) for row in rows]


def save_macro_state(
    record_date: date,
    credit_spread: float | None = None,
    forward_pe: float | None = None,
    real_yield: float | None = None,
    path: str = DEFAULT_DB_PATH,
) -> None:
    """Save the latest low-frequency macro variables."""
    conn = init_db(path)
    conn.execute(
        """
        INSERT INTO macro_states (date, credit_spread, forward_pe, real_yield)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            credit_spread = COALESCE(excluded.credit_spread, macro_states.credit_spread),
            forward_pe = COALESCE(excluded.forward_pe, macro_states.forward_pe),
            real_yield = COALESCE(excluded.real_yield, macro_states.real_yield)
        """,
        (record_date.isoformat(), credit_spread, forward_pe, real_yield)
    )
    conn.commit()
    conn.close()


def save_runtime_inputs(
    record_date: date,
    available_new_cash: float | None = None,
    rolling_drawdown: float | None = None,
    path: str = DEFAULT_DB_PATH,
) -> None:
    """Save the latest runtime inputs."""
    conn = init_db(path)
    conn.execute(
        """
        INSERT INTO runtime_inputs (date, available_new_cash, rolling_drawdown)
        VALUES (?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            available_new_cash = COALESCE(excluded.available_new_cash, runtime_inputs.available_new_cash),
            rolling_drawdown = COALESCE(excluded.rolling_drawdown, runtime_inputs.rolling_drawdown)
        """,
        (record_date.isoformat(), available_new_cash, rolling_drawdown),
    )
    conn.commit()
    conn.close()
