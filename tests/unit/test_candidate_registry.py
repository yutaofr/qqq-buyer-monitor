"""TDD: Candidate Registry — load, filter, and edge cases."""
from pathlib import Path

import pytest

from src.engine.candidate_registry import load_registry, select_runtime_candidates
from src.models.risk import RiskState

FIXTURE = "tests/fixtures/candidate_registry_v7.json"


# ── Task 9 ─────────────────────────────────────────────────────────────────────

def test_load_registry_reads_certified_candidates():
    registry = load_registry(FIXTURE)
    assert registry.registry_version == "test-v7-r1"
    assert len(registry.candidates) == 6


def test_load_registry_version_and_budget():
    registry = load_registry(FIXTURE)
    assert registry.drawdown_budget == 0.30
    assert registry.generated_at == "2026-03-24T12:00:00Z"


def test_load_registry_candidate_fields():
    registry = load_registry(FIXTURE)
    c = next(c for c in registry.candidates if c.candidate_id == "neutral-base-001")
    assert c.allowed_risk_state == RiskState.RISK_NEUTRAL
    assert c.qqq_pct == 0.70
    assert c.certification_status == "CERTIFIED"
    assert c.research_metrics["max_drawdown"] == 0.22


def test_load_registry_raises_on_missing_file():
    """Missing registry must raise FileNotFoundError — no silent fallback (SRD AC-3)."""
    with pytest.raises(FileNotFoundError):
        load_registry("/tmp/nonexistent_registry_v7.json")


def test_registry_candidates_are_certified_candidates():
    from src.models.candidate import CertifiedCandidate
    registry = load_registry(FIXTURE)
    for c in registry.candidates:
        assert isinstance(c, CertifiedCandidate)


# ── Task 10 ────────────────────────────────────────────────────────────────────

def test_select_runtime_candidates_filters_by_risk_state():
    registry = load_registry(FIXTURE)
    candidates = select_runtime_candidates(registry, RiskState.RISK_NEUTRAL)
    assert all(c.allowed_risk_state == RiskState.RISK_NEUTRAL for c in candidates)


def test_select_runtime_candidates_default_certified_only():
    registry = load_registry(FIXTURE)
    candidates = select_runtime_candidates(registry, RiskState.RISK_NEUTRAL, allow_conditional=False)
    assert all(c.certification_status == "CERTIFIED" for c in candidates)
    # CONDITIONAL should be excluded
    assert all(c.candidate_id != "neutral-conditional-001" for c in candidates)


def test_select_runtime_candidates_allows_conditional_when_flag_set():
    registry = load_registry(FIXTURE)
    candidates = select_runtime_candidates(registry, RiskState.RISK_NEUTRAL, allow_conditional=True)
    names = [c.candidate_id for c in candidates]
    assert "neutral-conditional-001" in names


def test_select_runtime_candidates_returns_empty_for_wrong_state():
    registry = load_registry(FIXTURE)
    candidates = select_runtime_candidates(registry, RiskState.RISK_EXIT)
    assert candidates == []


def test_select_runtime_candidates_defense_state():
    registry = load_registry(FIXTURE)
    candidates = select_runtime_candidates(registry, RiskState.RISK_DEFENSE)
    assert len(candidates) == 1
    assert candidates[0].candidate_id == "defense-001"
