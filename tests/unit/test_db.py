from __future__ import annotations

from datetime import date

from src.models import SignalResult, TargetAllocationState
from src.store.db import load_history, save_signal


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
