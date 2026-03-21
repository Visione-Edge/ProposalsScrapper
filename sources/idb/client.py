"""IDB/BID procurement notices client (CKAN CSV)."""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta

import httpx

from sources.base import BaseTender

logger = logging.getLogger(__name__)

CSV_URL = "https://data.iadb.org/file/download/9cc29cd0-c487-42e9-ad49-9971b4125066"


def _parse_date(date_str: str | None) -> str:
    if not date_str:
        return ""
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return date_str[:19] if len(date_str) >= 10 else date_str


class IDBClient:
    """Fetches procurement notices from IDB open data CSV."""

    def __init__(self, country_filter: str = "COSTA RICA"):
        self.country_filter = country_filter.upper()
        self._client = httpx.Client(timeout=120.0, follow_redirects=True)

    def fetch_recent_tenders(self, days_back: int = 90, **kwargs) -> list[BaseTender]:
        resp = self._client.get(CSV_URL)
        resp.raise_for_status()

        cutoff = datetime.now() - timedelta(days=days_back)
        tenders: list[BaseTender] = []

        reader = csv.DictReader(io.StringIO(resp.text))
        for row in reader:
            country = (row.get("countryname") or "").upper()
            if self.country_filter and self.country_filter not in country:
                continue

            tender = self._map_row(row, cutoff)
            if tender:
                tenders.append(tender)

        logger.info("IDB: %d notices fetched for %s", len(tenders), self.country_filter)
        return tenders

    def _map_row(self, row: dict, cutoff: datetime) -> BaseTender | None:
        notice_id = row.get("noticeid", "")
        if not notice_id:
            return None

        pub_date = _parse_date(row.get("publicationdate"))
        if pub_date:
            try:
                if datetime.strptime(pub_date[:10], "%Y-%m-%d") < cutoff:
                    return None
            except ValueError:
                pass

        name = (row.get("noticetitle") or row.get("projectname") or "").strip()
        if not name:
            return None

        project_url = row.get("proyecturl", "")
        doc_url = row.get("documenturl", "")

        return BaseTender(
            cartel_no=f"idb-{notice_id}",
            cartel_seq="0",
            inst_cartel_no=row.get("loannumber", f"IDB-{notice_id}"),
            name=name[:500],
            institution_code="IDB",
            institution_name=f"BID - {row.get('projectname', '')[:100]}",
            procedure_type=row.get("prcrmnt_mthd_engl_nm", row.get("category_nm", "")),
            status=row.get("projectstatus", "Published"),
            registration_date=pub_date,
            bid_start_date=pub_date,
            bid_end_date=_parse_date(row.get("deadline")),
            opening_date="",
            executor_name="",
            source="idb",
            source_url=doc_url or project_url or "",
            raw=row,
        )

    def close(self) -> None:
        self._client.close()
