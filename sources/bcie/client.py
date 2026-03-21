"""BCIE procurement notices web scraper."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

import httpx

from sources.base import BaseTender

logger = logging.getLogger(__name__)

BASE_URL = "https://adquisiciones.bcie.org"
NOTICES_URL = f"{BASE_URL}/en/procurement-notice"

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub("", text).strip()


def _parse_date(date_str: str) -> str:
    """Parse DD/MM/YYYY to YYYY-MM-DD HH:MM:SS."""
    if not date_str:
        return ""
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return date_str


class BCIEClient:
    """Scrapes procurement notices from BCIE portal."""

    def __init__(self, request_delay: float = 2.0):
        self.request_delay = request_delay
        self._client = httpx.Client(timeout=30.0, follow_redirects=True)

    def fetch_recent_tenders(self, days_back: int = 30, **kwargs) -> list[BaseTender]:
        resp = self._client.get(NOTICES_URL)
        resp.raise_for_status()

        cutoff = datetime.now() - timedelta(days=days_back)
        tenders: list[BaseTender] = []

        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", resp.text, re.DOTALL)
        for row in rows[1:]:  # Skip header row
            tender = self._parse_row(row, cutoff)
            if tender:
                tenders.append(tender)

        logger.info("BCIE: %d notices fetched", len(tenders))
        return tenders

    def _parse_row(self, row_html: str, cutoff: datetime) -> BaseTender | None:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.DOTALL)
        if len(cells) < 5:
            return None

        notice_id = _strip_html(cells[0])
        name = _strip_html(cells[1])
        country = _strip_html(cells[2])
        pub_date_str = _strip_html(cells[3])
        deadline_str = _strip_html(cells[4])

        if not notice_id or not name:
            return None

        pub_date = _parse_date(pub_date_str)
        if pub_date:
            try:
                if datetime.strptime(pub_date[:10], "%Y-%m-%d") < cutoff:
                    return None
            except ValueError:
                pass

        # Extract detail link
        links = re.findall(r'href="([^"]+)"', row_html)
        detail_url = f"{BASE_URL}{links[0]}" if links else NOTICES_URL

        return BaseTender(
            cartel_no=f"bcie-{notice_id}",
            cartel_seq="0",
            inst_cartel_no=f"BCIE-{notice_id}",
            name=name[:500],
            institution_code="BCIE",
            institution_name=f"BCIE - {country}",
            procedure_type="",
            status="Published",
            registration_date=pub_date,
            bid_start_date=pub_date,
            bid_end_date=_parse_date(deadline_str),
            opening_date="",
            executor_name="",
            source="bcie",
            source_url=detail_url,
            raw={"notice_id": notice_id, "name": name, "country": country,
                 "pub_date": pub_date_str, "deadline": deadline_str},
        )

    def close(self) -> None:
        self._client.close()
