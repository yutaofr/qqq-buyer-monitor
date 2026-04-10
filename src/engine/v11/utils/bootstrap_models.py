from dataclasses import dataclass, field
from datetime import UTC, date, datetime


@dataclass
class MacroGap:
    missing_date: date
    prev_available_date: date | None
    next_available_date: date | None
    gap_days: int

@dataclass
class CacheStaleness:
    last_date: date | None
    days_stale: int

@dataclass
class FieldCompleteness:
    missing_fields: dict[str, int] = field(default_factory=dict)

@dataclass
class BootstrapAuditReport:
    macro_gaps: list[MacroGap] = field(default_factory=list)
    price_cache_staleness: CacheStaleness = field(default_factory=lambda: CacheStaleness(None, 0))
    field_completeness: FieldCompleteness = field(default_factory=FieldCompleteness)
    audit_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    is_healthy: bool = True

@dataclass
class BootstrapRepairResult:
    total_rows_added: int = 0
    total_fields_repaired: int = 0
    repair_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
