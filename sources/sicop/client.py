"""SICOP source adapter — wraps the existing SICOPClient to return BaseTender."""

from __future__ import annotations

from sicop.client import SICOPClient, Tender
from sources.base import BaseTender


def _to_base(tender: Tender) -> BaseTender:
    return BaseTender(
        cartel_no=tender.cartel_no,
        cartel_seq=tender.cartel_seq,
        inst_cartel_no=tender.inst_cartel_no,
        name=tender.name,
        institution_code=tender.institution_code,
        institution_name=tender.institution_name,
        procedure_type=tender.procedure_type,
        status=tender.status,
        registration_date=tender.registration_date,
        bid_start_date=tender.bid_start_date,
        bid_end_date=tender.bid_end_date,
        opening_date=tender.opening_date,
        executor_name=tender.executor_name,
        source="sicop",
        source_url=tender.url,
        raw=tender.raw,
    )


class SICOPSourceClient:
    """Adapter around the existing SICOPClient."""

    def __init__(self, page_size: int = 50, request_delay: float = 1.0):
        self._client = SICOPClient(page_size=page_size, request_delay=request_delay)

    def fetch_recent_tenders(
        self,
        days_back: int = 3,
        max_pages: int = 0,
        procedure_types: list[str] | None = None,
        institutions: list[str] | None = None,
    ) -> list[BaseTender]:
        tenders = self._client.fetch_recent_tenders(
            days_back=days_back,
            max_pages=max_pages,
            procedure_types=procedure_types,
            institutions=institutions,
        )
        return [_to_base(t) for t in tenders]

    def close(self) -> None:
        self._client.close()
