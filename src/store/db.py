"""SQLite persistence layer for historical signal records."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from src.models import (
    SignalDetail,
    SignalResult,
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

CREATE_MACRO_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS macro_states (
    date TEXT PRIMARY KEY,
    credit_spread REAL,
    trailing_pe REAL,
    forward_pe REAL,
    real_yield REAL,
    fcf_yield REAL,
    earnings_revisions_breadth REAL
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
    conn.execute(CREATE_TABLE_SQL)
    conn.execute(CREATE_MACRO_TABLE_SQL)
    conn.execute(CREATE_RUNTIME_INPUTS_SQL)

    # v3.0 migrations for existing DB
    for col in ["forward_pe", "real_yield", "fcf_yield", "earnings_revisions_breadth"]:
        try:
            conn.execute(f"ALTER TABLE macro_states ADD COLUMN {col} REAL")
        except sqlite3.OperationalError:
            pass

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


def _migrate_blob(blob: dict) -> dict:
    """Lazy migration for historical JSON blobs to ensure v8.0+ compatibility."""
    # Ensure target_allocation exists for legacy records
    if "target_allocation" not in blob:
        blob["target_allocation"] = {
            "target_cash_pct": blob.get("target_cash_pct", 0.1),
            "target_qqq_pct": 0.9,
            "target_qld_pct": 0.0,
            "target_beta": 0.9,
        }

    # v8.0+ field migration — null defaults for old records
    blob.setdefault("risk_state", None)
    blob.setdefault("deployment_state", None)
    blob.setdefault("selected_candidate_id", None)
    blob.setdefault("registry_version", None)
    blob.setdefault("tier0_regime", None)
    blob.setdefault("tier0_applied", False)
    blob.setdefault("raw_target_beta", None)
    blob.setdefault("target_beta", None)
    blob.setdefault("assumed_beta_before", None)
    blob.setdefault("assumed_beta_after", None)
    blob.setdefault("friction_blockers", [])
    blob.setdefault("estimated_turnover", None)
    blob.setdefault("estimated_cost_drag", None)
    blob.setdefault("should_adjust", None)
    blob.setdefault("rebalance_action", {})
    blob.setdefault("deployment_action", {})
    blob.setdefault("candidate_selection_audit", [])

    # Remove purged legacy fields if present
    blob.pop("current_portfolio", None)
    blob.pop("effective_exposure", None)
    blob.pop("interval_beta_audit", None)

    return blob


def load_history(n: int = 30, path: str = DEFAULT_DB_PATH) -> list[dict]:
    """Return the most recent n signal records as raw dicts."""
    if not Path(path).exists():
        return []
    conn = init_db(path)
    rows = conn.execute(
        "SELECT json_blob FROM signals ORDER BY date DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()
    return [_migrate_blob(json.loads(row[0])) for row in rows]


def get_historical_series(days: int = 60, path: str = DEFAULT_DB_PATH) -> pd.DataFrame | None:
    """
    Return a pandas DataFrame of the last `days` records from the DB.
    Extracts date, price, vix, and breadth for divergence calculations.
    """
    if not Path(path).exists():
        return None

    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    conn = init_db(path)
    rows = conn.execute(
        "SELECT json_blob FROM signals WHERE date >= ? ORDER BY date ASC", (cutoff_date,)
    ).fetchall()
    conn.close()

    if not rows:
        return None

    data = []
    for row in rows:
        d = json.loads(row[0])
        tier1 = d.get("tier1", {}).get("details", {})

        # Extract scalar values safely
        vix_val = tier1.get("vix", {}).get("value")
        breadth_val = tier1.get("breadth", {}).get("value")

        data.append({
            "date": pd.to_datetime(d["date"]),
            "price": d["price"],
            "vix": vix_val,
            "breadth": breadth_val,
            "signal": d.get("signal")
        })

    df = pd.DataFrame(data)
    if not df.empty:
        df.set_index("date", inplace=True)
        return df
    return None


def save_macro_state(
    record_date: date,
    credit_spread: float | None = None,
    trailing_pe: float | None = None,
    forward_pe: float | None = None,
    real_yield: float | None = None,
    fcf_yield: float | None = None,
    earnings_revisions_breadth: float | None = None,
    path: str = DEFAULT_DB_PATH,
) -> None:
    """Save the latest low-frequency macro variables."""
    conn = init_db(path)
    conn.execute(
        """
        INSERT INTO macro_states (
            date, credit_spread, trailing_pe, forward_pe,
            real_yield, fcf_yield, earnings_revisions_breadth
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            credit_spread = COALESCE(excluded.credit_spread, macro_states.credit_spread),
            trailing_pe = COALESCE(excluded.trailing_pe, macro_states.trailing_pe),
            forward_pe = COALESCE(excluded.forward_pe, macro_states.forward_pe),
            real_yield = COALESCE(excluded.real_yield, macro_states.real_yield),
            fcf_yield = COALESCE(excluded.fcf_yield, macro_states.fcf_yield),
            earnings_revisions_breadth = COALESCE(excluded.earnings_revisions_breadth, macro_states.earnings_revisions_breadth)
        """,
        (
            record_date.isoformat(),
            credit_spread, trailing_pe, forward_pe,
            real_yield, fcf_yield, earnings_revisions_breadth
        )
    )
    conn.commit()
    conn.close()
    logger.debug("Saved macro state for %s", record_date.isoformat())


def load_latest_macro_state(path: str = DEFAULT_DB_PATH) -> dict | None:
    """Return the most recent macro state dict."""
    if not Path(path).exists():
        return None
    conn = init_db(path)
    row = conn.execute(
        "SELECT date, credit_spread, trailing_pe, forward_pe, real_yield, fcf_yield, earnings_revisions_breadth FROM macro_states ORDER BY date DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        return {
            "date": row[0],
            "credit_spread": row[1],
            "trailing_pe": row[2],
            "forward_pe": row[3],
            "real_yield": row[4],
            "fcf_yield": row[5],
            "earnings_revisions_breadth": row[6],
        }
    return None


def save_runtime_inputs(
    record_date: date,
    available_new_cash: float | None = None,
    rolling_drawdown: float | None = None,
    path: str = DEFAULT_DB_PATH,
) -> None:
    """Save the latest runtime inputs used by the v7 controllers."""
    conn = init_db(path)
    conn.execute(
        """
        INSERT INTO runtime_inputs (
            date, available_new_cash, rolling_drawdown
        )
        VALUES (?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            available_new_cash = COALESCE(excluded.available_new_cash, runtime_inputs.available_new_cash),
            rolling_drawdown = COALESCE(excluded.rolling_drawdown, runtime_inputs.rolling_drawdown)
        """,
        (record_date.isoformat(), available_new_cash, rolling_drawdown),
    )
    conn.commit()
    conn.close()
    logger.debug("Saved runtime inputs for %s", record_date.isoformat())


def load_latest_runtime_inputs(path: str = DEFAULT_DB_PATH) -> dict | None:
    """Return the most recent runtime input dict."""
    if not Path(path).exists():
        return None
    conn = init_db(path)
    row = conn.execute(
        "SELECT date, available_new_cash, rolling_drawdown FROM runtime_inputs ORDER BY date DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        return {
            "date": row[0],
            "available_new_cash": row[1],
            "rolling_drawdown": row[2],
        }
    return None


def load_runtime_inputs(record_date: date, path: str = DEFAULT_DB_PATH) -> dict | None:
    """Return runtime inputs for one specific trading date."""
    if not Path(path).exists():
        return None
    conn = init_db(path)
    row = conn.execute(
        "SELECT date, available_new_cash, rolling_drawdown FROM runtime_inputs WHERE date = ?",
        (record_date.isoformat(),),
    ).fetchone()
    conn.close()
    if row:
        return {
            "date": row[0],
            "available_new_cash": row[1],
            "rolling_drawdown": row[2],
        }
    return None


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
        "allocation_state": result.allocation_state.value,
        "daily_tranche_pct": float(result.daily_tranche_pct),
        "max_total_add_pct": float(result.max_total_add_pct),
        "cooldown_days": int(result.cooldown_days),
        "required_persistence_days": int(result.required_persistence_days),
        "confidence": result.confidence,
        "data_quality": result.data_quality,
        "tier1": {
            "score": t1.score,
            "stress_score": getattr(t1, "stress_score", 0),
            "capitulation_score": getattr(t1, "capitulation_score", 0),
            "persistence_score": getattr(t1, "persistence_score", 0),
            "valuation_bonus": getattr(t1, "valuation_bonus", 0),
            "fcf_bonus": getattr(t1, "fcf_bonus", 0),
            "short_flow_bonus": getattr(t1, "short_flow_bonus", 0),
            "divergence_bonus": getattr(t1, "divergence_bonus", 0),
            "divergence_flags": getattr(t1, "divergence_flags", {}),
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
        "pe_source": result.pe_source,
        "erp": _float(result.erp),
        "logic_trace": result.logic_trace,
        # v6.3 Strategic Portfolio & Rebalancing
        "target_allocation": {
            "target_cash_pct": _float(result.target_allocation.target_cash_pct),
            "target_qqq_pct": _float(result.target_allocation.target_qqq_pct),
            "target_qld_pct": _float(result.target_allocation.target_qld_pct),
            "target_beta": _float(result.target_allocation.target_beta),
        },
        # v7.0 Dual-Controller fields
        "risk_state": result.risk_state.value if result.risk_state is not None else None,
        "deployment_state": result.deployment_state.value if result.deployment_state is not None else None,
        "selected_candidate_id": result.selected_candidate_id,
        "registry_version": result.registry_version,
        "tier0_regime": result.tier0_regime,
        "tier0_applied": result.tier0_applied,
        "raw_target_beta": _float(result.raw_target_beta),
        "target_beta": _float(result.target_beta),
        "assumed_beta_before": _float(result.assumed_beta_before),
        "assumed_beta_after": _float(result.assumed_beta_after),
        "friction_blockers": list(result.friction_blockers),
        "estimated_turnover": _float(result.estimated_turnover),
        "estimated_cost_drag": _float(result.estimated_cost_drag),
        "should_adjust": result.should_adjust,
        "rebalance_action": result.rebalance_action,
        "deployment_action": result.deployment_action,
        "candidate_selection_audit": result.candidate_selection_audit,
    }
