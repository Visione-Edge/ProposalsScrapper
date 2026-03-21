"""Base model and client protocol shared across all procurement sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class BaseTender:
    """Universal tender model that maps to the existing DB schema.

    For non-SICOP sources:
      - cartel_no = "{source_prefix}-{native_id}"
      - cartel_seq = "0"
    SICOP keeps its original cartel_no/cartel_seq values.
    """

    cartel_no: str
    cartel_seq: str
    inst_cartel_no: str
    name: str
    institution_code: str
    institution_name: str
    procedure_type: str
    status: str
    registration_date: str
    bid_start_date: str
    bid_end_date: str
    opening_date: str
    executor_name: str
    source: str
    source_url: str
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def searchable_text(self) -> str:
        return f"{self.name} {self.inst_cartel_no} {self.institution_name}".lower()

    @property
    def url(self) -> str:
        return self.source_url

    @property
    def reg_date_str(self) -> str:
        return self.registration_date[:10] if self.registration_date else ""


SOURCE_LABELS = {
    "sicop": "SICOP",
    "worldbank": "Banco Mundial",
    "undp": "UNDP",
    "idb": "BID/IDB",
    "bcie": "BCIE",
    "caf": "CAF",
    "eu_ted": "EU/TED",
    "ccss": "CCSS",
    "ice_pel": "ICE/PEL",
    "ungm": "UNGM",
    "unops": "UNOPS",
}


@runtime_checkable
class SourceClient(Protocol):
    """Protocol that all source clients must implement."""

    def fetch_recent_tenders(self, days_back: int = 3, **kwargs) -> list[BaseTender]: ...
    def close(self) -> None: ...
