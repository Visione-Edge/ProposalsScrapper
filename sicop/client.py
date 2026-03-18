"""Cliente HTTP para la API pública de SICOP."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import httpx

API_BASE = "https://prod-api.sicop.go.cr"

SEARCH_ENDPOINT = f"{API_BASE}/bid/api/v1/public/epCartel/searchEpCartels"
DETAIL_ENDPOINT = f"{API_BASE}/bid/api/v1/public/epCartel/findById"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://www.sicop.go.cr",
    "Referer": "https://www.sicop.go.cr/",
}


@dataclass
class Tender:
    """Representa una licitación de SICOP."""

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
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: dict) -> Tender:
        return cls(
            cartel_no=data.get("cartelNo", ""),
            cartel_seq=str(data.get("cartelSeq", "")),
            inst_cartel_no=data.get("instCartelNo", ""),
            name=data.get("cartelNm", ""),
            institution_code=data.get("cartelInstCd", ""),
            institution_name=data.get("cartelInstNm", ""),
            procedure_type=data.get("proceType", ""),
            status=data.get("cartelStatStr", data.get("cartelStat", "")),
            registration_date=data.get("regDt", ""),
            bid_start_date=data.get("biddocStartDt", ""),
            bid_end_date=data.get("biddocEndDt", ""),
            opening_date=data.get("openbidDt", ""),
            executor_name=data.get("executorNm", ""),
            raw=data,
        )

    @property
    def url(self) -> str:
        return f"https://www.sicop.go.cr/moduloOferta/search/EP_SEJ_COQ603.jsp?cartelNo={self.cartel_no}&cartelSeq={self.cartel_seq}"

    @property
    def searchable_text(self) -> str:
        return f"{self.name} {self.inst_cartel_no} {self.institution_name}".lower()

    @property
    def reg_date_str(self) -> str:
        """Retorna solo la parte de fecha (YYYY-MM-DD) del registration_date."""
        return self.registration_date[:10] if self.registration_date else ""


class SICOPClient:
    """Cliente para consultar la API pública de SICOP."""

    def __init__(self, page_size: int = 50, request_delay: float = 1.0):
        self.page_size = page_size
        self.request_delay = request_delay
        self._client = httpx.Client(headers=HEADERS, timeout=30.0, verify=True)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> SICOPClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _post(self, url: str, payload: dict) -> dict:
        resp = self._client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()

    def fetch_tenders_page(
        self,
        page: int = 0,
        procedure_types: list[str] | None = None,
        institutions: list[str] | None = None,
    ) -> tuple[list[Tender], int]:
        """Obtiene una página de licitaciones.

        Retorna (lista de tenders, total de páginas).
        """
        form_filter: list[dict] = []
        if procedure_types:
            form_filter.append({"key": "proceType", "value": ",".join(procedure_types)})
        if institutions:
            form_filter.append({"key": "cartelInstCd", "value": ",".join(institutions)})

        payload = {
            "pageNumber": page,
            "pageSize": self.page_size,
            "formFilter": form_filter,
        }

        data = self._post(SEARCH_ENDPOINT, payload)

        content = data.get("content", data.get("list", []))
        total_pages = data.get("totalPages", 1)

        tenders = [Tender.from_api(item) for item in content]
        return tenders, total_pages

    def fetch_recent_tenders(
        self,
        days_back: int = 3,
        max_pages: int = 0,
        procedure_types: list[str] | None = None,
        institutions: list[str] | None = None,
    ) -> list[Tender]:
        """Obtiene licitaciones recientes (últimos N días).

        Los resultados de SICOP vienen ordenados por fecha descendente.
        Pagina hasta que las fechas sean más antiguas que el cutoff.
        """
        cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        all_tenders: list[Tender] = []
        page = 0

        while True:
            tenders, total_pages = self.fetch_tenders_page(
                page=page,
                procedure_types=procedure_types,
                institutions=institutions,
            )

            if not tenders:
                break

            # Revisar si ya pasamos el cutoff
            hit_cutoff = False
            for t in tenders:
                if t.reg_date_str >= cutoff:
                    all_tenders.append(t)
                else:
                    hit_cutoff = True

            if hit_cutoff:
                break

            page += 1
            if page >= total_pages:
                break
            if max_pages and page >= max_pages:
                break

            time.sleep(self.request_delay)

        return all_tenders

    def fetch_tender_detail(self, cartel_no: str, cartel_seq: str) -> dict:
        """Obtiene el detalle de una licitación específica."""
        payload = {"cartelNo": cartel_no, "cartelSeq": cartel_seq}
        return self._post(DETAIL_ENDPOINT, payload)
