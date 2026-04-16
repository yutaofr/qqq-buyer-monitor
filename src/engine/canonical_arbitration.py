"""Canonical execution arbitration between Bayesian and V16 topology engines."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import date
from typing import Any

import pandas as pd

from src.models import SignalResult, TargetAllocationState


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if pd.notna(out) else default


def _safe_bool(value: object) -> bool:
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _stamp_to_date(value: object) -> date | None:
    if value is None:
        return None
    try:
        return pd.Timestamp(value).date()
    except Exception:
        return None


def _normalize_alloc(qld: float, qqq: float, cash: float) -> tuple[float, float, float]:
    qld = max(0.0, qld)
    qqq = max(0.0, qqq)
    cash = max(0.0, cash)
    total = qld + qqq + cash
    if total <= 0.0:
        return 0.0, 0.5, 0.5
    return qld / total, qqq / total, cash / total


def _with_official_allocation(
    result: SignalResult,
    *,
    qld: float,
    qqq: float,
    cash: float,
    source: str,
    reason: str,
    v16_snapshot: dict[str, Any],
) -> SignalResult:
    qld, qqq, cash = _normalize_alloc(qld, qqq, cash)
    target_beta = round(float(qqq + (2.0 * qld)), 6)
    metadata = deepcopy(result.metadata or {})
    metadata["execution_bucket"] = "QLD" if qld > 0.0 else "QQQ"
    metadata["canonical_decision"] = {
        "source": source,
        "reason": reason,
        "official_target_beta": target_beta,
        "official_reference_path": {
            "qld_pct": round(qld, 6),
            "qqq_pct": round(qqq, 6),
            "cash_pct": round(cash, 6),
        },
        "v16_topology": v16_snapshot,
    }

    logic_trace = list(result.logic_trace or [])
    logic_trace.append({"step": "canonical_arbitration", "result": metadata["canonical_decision"]})

    return replace(
        result,
        target_beta=target_beta,
        target_allocation=TargetAllocationState(
            target_cash_pct=cash,
            target_qqq_pct=qqq,
            target_qld_pct=qld,
            target_beta=target_beta,
        ),
        logic_trace=logic_trace,
        metadata=metadata,
    )


def apply_v16_topology_arbitration(
    result: SignalResult,
    v16_state: dict[str, Any] | None,
) -> SignalResult:
    """Make V16 topology the execution authority when its process is clean.

    The Bayesian engine remains the macro risk prior. V16 cannot pass through a
    hard liquidity or trend veto, but it can override a conservative Bayesian
    allocation when the topology process is safe and BUST is not dominant.
    """
    if not v16_state:
        return result

    latest_log = dict(v16_state.get("latest_log") or {})
    if latest_log.get("state") not in {None, "active"}:
        return result

    latest_row = dict(v16_state.get("latest_row") or {})
    v16_date = _stamp_to_date(v16_state.get("last_timestamp"))
    result_date = result.date
    stale_days = None
    if v16_date is not None:
        stale_days = (pd.Timestamp(result_date).date() - v16_date).days
    is_fresh = stale_days is None or stale_days <= 3

    qld = _safe_float(latest_log.get("qld"))
    qqq = _safe_float(latest_log.get("qqq"))
    cash = _safe_float(latest_log.get("cash"))
    p_cp = _safe_float(latest_log.get("p_cp"))
    s_t = _safe_float(latest_log.get("s_t"))
    vol_cap = _safe_float(latest_log.get("vol_guard_cap"), 1.0)
    circuit_breaker = _safe_bool(latest_log.get("circuit_breaker"))
    momentum_lockout = _safe_bool(latest_log.get("momentum_lockout"))
    qqq_price = _safe_float(latest_row.get("QQQ_price"))
    qqq_sma200 = _safe_float(latest_row.get("QQQ_sma200"))
    above_sma = qqq_sma200 <= 0.0 or qqq_price >= qqq_sma200
    bust_prob = _safe_float((result.probabilities or {}).get("BUST"))

    snapshot = {
        "date": v16_date.isoformat() if v16_date else None,
        "fresh": is_fresh,
        "stale_days": stale_days,
        "qld": qld,
        "qqq": qqq,
        "cash": cash,
        "p_cp": p_cp,
        "s_t": s_t,
        "vol_guard_cap": vol_cap,
        "circuit_breaker": circuit_breaker,
        "momentum_lockout": momentum_lockout,
        "qqq_price": qqq_price,
        "qqq_sma200": qqq_sma200,
        "above_sma200": above_sma,
        "bayesian_bust_probability": bust_prob,
    }

    hard_veto = circuit_breaker or momentum_lockout or p_cp >= 0.70 or s_t >= 0.70 or not above_sma
    if is_fresh and hard_veto:
        return _with_official_allocation(
            result,
            qld=0.0,
            qqq=0.5,
            cash=0.5,
            source="v16_hard_veto",
            reason="V16 topology hard risk veto blocks leveraged exposure.",
            v16_snapshot=snapshot,
        )

    topology_safe = (
        is_fresh
        and qld > 0.0
        and p_cp < 0.15
        and s_t < 0.30
        and vol_cap >= 1.5
        and above_sma
        and bust_prob < 0.55
    )
    if topology_safe:
        return _with_official_allocation(
            result,
            qld=qld,
            qqq=qqq,
            cash=cash,
            source="v16_topology",
            reason="V16 topology process is clean; Bayesian posterior is retained as risk telemetry.",
            v16_snapshot=snapshot,
        )

    metadata = deepcopy(result.metadata or {})
    metadata["canonical_decision"] = {
        "source": "bayesian_base",
        "reason": "V16 topology was stale, non-bullish, or blocked by Bayesian BUST dominance.",
        "official_target_beta": result.target_beta,
        "official_reference_path": {
            "qld_pct": result.target_allocation.target_qld_pct,
            "qqq_pct": result.target_allocation.target_qqq_pct,
            "cash_pct": result.target_allocation.target_cash_pct,
        },
        "v16_topology": snapshot,
    }
    logic_trace = list(result.logic_trace or [])
    logic_trace.append({"step": "canonical_arbitration", "result": metadata["canonical_decision"]})
    return replace(result, logic_trace=logic_trace, metadata=metadata)
