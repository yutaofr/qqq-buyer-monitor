"""JSON report generator."""
from __future__ import annotations

import json

from src.store.db import _to_json_dict  # reuse the serialiser
from src.models import SignalResult


def to_json(result: SignalResult, indent: int = 2) -> str:
    """Serialise a SignalResult to a pretty-printed JSON string."""
    return json.dumps(_to_json_dict(result), ensure_ascii=False, indent=indent)
