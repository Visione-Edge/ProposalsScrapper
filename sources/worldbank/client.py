"""World Bank procurement notices API client."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from html import unescape

import httpx

from sources.base import BaseTender

logger = logging.getLogger(__name__)

API_URL = "https://search.worldbank.org/api/v2/procnotices"

# Strip HTML tags from notice_text
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return unescape(_TAG_RE.sub(" ", text)).strip() if text else ""


def _parse_date(date_str: str | None) -> str:
    """Parse various WB date formats to YYYY-MM-DD HH:MM:SS."""
    if not date_str:
        return ""
    # ISO format: 2026-03-20T00:00:00Z
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%d-%b-%Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return date_str[:19] if len(date_str) >= 10 else date_str


class WorldBankClient:
    """Fetches procurement notices from the World Bank API."""

    def __init__(self, country: str = "Costa Rica", rows_per_page: int = 50):
        self.country = country
        self.rows_per_page = rows_per_page
        self._client = httpx.Client(timeout=30.0)

    def fetch_recent_tenders(self, days_back: int = 30, **kwargs) -> list[BaseTender]:
        today_str = datetime.now().strftime("%Y-%m-%d")
        all_tenders: list[BaseTender] = []
        offset = 0

        while True:
            params = {
                "format": "json",
                "rows": self.rows_per_page,
                "os": offset,
                "deadlinedate": today_str,  # Only notices with deadline >= today
            }
            if self.country:
                params["project_ctry_name"] = self.country
            resp = self._client.get(API_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            notices = data.get("procnotices", [])
            if not notices:
                break

            for n in notices:
                tender = self._map_notice(n)
                if tender:
                    all_tenders.append(tender)

            total = int(data.get("total", 0))
            offset += self.rows_per_page
            if offset >= total:
                break

        logger.info("World Bank: %d notices fetched for %s", len(all_tenders), self.country)
        return all_tenders

    def _map_notice(self, n: dict) -> BaseTender | None:
        notice_id = n.get("id", "")
        if not notice_id:
            return None

        name = n.get("bid_description", "") or n.get("project_name", "")
        name = _strip_html(name)[:500]

        return BaseTender(
            cartel_no=f"wb-{notice_id}",
            cartel_seq="0",
            inst_cartel_no=n.get("bid_reference_no", notice_id),
            name=name,
            institution_code="",
            institution_name=n.get("contact_organization", n.get("project_name", "")),
            procedure_type=n.get("procurement_method_name", ""),
            status=n.get("notice_status", ""),
            registration_date=_parse_date(n.get("submission_date", n.get("noticedate"))),
            bid_start_date=_parse_date(n.get("noticedate")),
            bid_end_date=_parse_date(n.get("submission_deadline_date")),
            opening_date="",
            executor_name=n.get("contact_name", ""),
            source="worldbank",
            source_url=f"https://projects.worldbank.org/en/projects-operations/procurement-detail/{notice_id}",
            raw=n,
        )

    def close(self) -> None:
        self._client.close()
