"""JSON report generator."""
from __future__ import annotations

import json
from typing import Any

from src.store.db import _to_json_dict  # reuse the serialiser
from src.models import SignalResult


def summarize_data_quality(data_quality: dict[str, dict[str, Any]]) -> str:
    """Return a compact human-readable summary of feature availability."""
    total = len(data_quality)
    if total == 0:
        return "0/0 可用"

    usable = sum(1 for meta in data_quality.values() if meta.get("usable"))
    return f"{usable}/{total} 可用"


def to_json(result: SignalResult, indent: int = 2) -> str:
    """Serialise a SignalResult to a pretty-printed JSON string."""
    payload = _to_json_dict(result)
    payload["data_quality_summary"] = summarize_data_quality(result.data_quality)
    return json.dumps(payload, ensure_ascii=False, indent=indent)
