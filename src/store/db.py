"""SQLite persistence layer for historical signal records."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import date
from pathlib import Path

from src.models import (
    Signal,
    SignalDetail,
    SignalResult,
    Tier1Result,
    Tier2Result,
)

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.environ.get("QQQ_DB_PATH", "data/signals.db")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS signals (
    date TEXT PRIMARY KEY,
    signal TEXT NOT NULL,
    final_score INTEGER NOT NULL,
    price REAL NOT NULL,
    json_blob TEXT NOT NULL
);
"""


def init_db(path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Initialise (or open) the SQLite database and create the table."""
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()
    logger.debug("DB initialised at %s", db_path)
    return conn


def save_signal(result: SignalResult, path: str = DEFAULT_DB_PATH) -> None:
    """Upsert a SignalResult into the database."""
    conn = init_db(path)
    blob = _to_json_dict(result)
    conn.execute(
        """
        INSERT INTO signals (date, signal, final_score, price, json_blob)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            signal=excluded.signal,
            final_score=excluded.final_score,
            price=excluded.price,
            json_blob=excluded.json_blob
        """,
        (
            result.date.isoformat(),
            result.signal.value,
            result.final_score,
            result.price,
            json.dumps(blob, ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()
    logger.debug("Saved signal for %s: %s", result.date, result.signal.value)


def load_history(n: int = 30, path: str = DEFAULT_DB_PATH) -> list[dict]:
    """Return the most recent n signal records as raw dicts."""
    if not Path(path).exists():
        return []
    conn = sqlite3.connect(path)
    rows = conn.execute(
        "SELECT json_blob FROM signals ORDER BY date DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()
    return [json.loads(row[0]) for row in rows]


def _to_json_dict(result: SignalResult) -> dict:
    """Serialise a SignalResult to a JSON-compatible dict (all native Python types)."""

    def _bool(v) -> bool:  # noqa: ANN001
        return bool(v)

    def _float(v) -> float | None:  # noqa: ANN001
        return float(v) if v is not None else None

    def detail_to_dict(d: SignalDetail) -> dict:
        return {
            "name": d.name,
            "value": float(d.value),
            "points": int(d.points),
            "thresholds": [float(x) for x in d.thresholds] if isinstance(d.thresholds, tuple) and not isinstance(d.thresholds[0], tuple) else str(d.thresholds),
            "triggered_half": _bool(d.triggered_half),
            "triggered_full": _bool(d.triggered_full),
        }

    t1 = result.tier1
    t2 = result.tier2

    return {
        "date": result.date.isoformat(),
        "price": result.price,
        "signal": result.signal.value,
        "final_score": result.final_score,
        "tier1": {
            "score": t1.score,
            "details": {
                "drawdown_52w": detail_to_dict(t1.drawdown_52w),
                "ma200_deviation": detail_to_dict(t1.ma200_deviation),
                "vix": detail_to_dict(t1.vix),
                "fear_greed": detail_to_dict(t1.fear_greed),
                "breadth": detail_to_dict(t1.breadth),
            },
        },
        "tier2": {
            "adjustment": int(t2.adjustment),
            "put_wall": _float(t2.put_wall),
            "call_wall": _float(t2.call_wall),
            "gamma_flip": _float(t2.gamma_flip),
            "support_confirmed": _bool(t2.support_confirmed),
            "support_broken": _bool(t2.support_broken),
            "upside_open": _bool(t2.upside_open),
            "gamma_positive": _bool(t2.gamma_positive),
            "gamma_source": str(t2.gamma_source),
            "put_wall_distance_pct": _float(t2.put_wall_distance_pct),
            "call_wall_distance_pct": _float(t2.call_wall_distance_pct),
        },
        "explanation": result.explanation,
    }
