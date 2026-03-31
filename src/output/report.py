"""JSON report generator for v11 Bayesian Monitor."""
from __future__ import annotations

import json

from src.models import SignalResult
from src.store.db import _to_json_dict


def to_json(result: SignalResult, indent: int = 2) -> str:
    """Serialise a SignalResult to a pretty-printed JSON string."""
    payload = _to_json_dict(result)
    return json.dumps(payload, ensure_ascii=False, indent=indent)
