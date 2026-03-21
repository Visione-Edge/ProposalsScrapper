"""UNGM (United Nations Global Marketplace) client."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

import httpx

from sources.base import BaseTender

logger = logging.getLogger(__name__)

# UNGM uses an internal AJAX API
UNGM_SEARCH_URL = "https://www.ungm.org/Public/Notice"
UNGM_API_URL = "https://www.ungm.org/api/Public/Notice"

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub("", text).strip()


def _parse_date(date_str: str) -> str:
    if not date_str:
        return ""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y",
                "%m/%d/%Y", "%b %d, %Y"):
        try:
            return datetime.strptime(date_str.strip()[:19], fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return date_str[:19] if len(date_str) >= 10 else date_str


class UNGMClient:
    """Fetches procurement notices from UNGM."""

    def __init__(self, request_delay: float = 2.0):
        self.request_delay = request_delay
        self._client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; ProposalsScrapper/1.0)",
                "Accept": "application/json, text/html",
                "X-Requested-With": "XMLHttpRequest",
            },
        )

    def fetch_recent_tenders(self, days_back: int = 30, **kwargs) -> list[BaseTender]:
        tenders: list[BaseTender] = []

        # Try the AJAX API first
        try:
            tenders = self._fetch_via_api(days_back)
        except Exception as e:
            logger.debug("UNGM API error: %s, trying HTML", e)

        # Fallback: parse HTML page
        if not tenders:
            try:
                tenders = self._fetch_via_html(days_back)
            except Exception as e:
                logger.warning("UNGM HTML error: %s", e)

        logger.info("UNGM: %d notices fetched", len(tenders))
        return tenders

    def _fetch_via_api(self, days_back: int) -> list[BaseTender]:
        cutoff = datetime.now() - timedelta(days=days_back)
        tenders: list[BaseTender] = []

        # UNGM Angular app posts to this endpoint
        payload = {
            "PageIndex": 0,
            "PageSize": 50,
            "NoticetypeIndex": 0,  # All types
            "Title": "",
            "Description": "",
            "Deadline": "",
            "SortField": "DatePublished",
            "SortAscending": False,
            "isPicker": False,
            "UNSPSCs": [],
            "DeadlineFrom": "",
        }

        resp = self._client.post(UNGM_API_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()

        results = data if isinstance(data, list) else data.get("Results", data.get("results", []))

        for item in results:
            tender = self._map_api_item(item, cutoff)
            if tender:
                tenders.append(tender)

        return tenders

    def _map_api_item(self, item: dict, cutoff: datetime) -> BaseTender | None:
        title = item.get("Title", item.get("title", ""))
        if not title:
            return None

        notice_id = str(item.get("Id", item.get("id", item.get("Reference", ""))))
        reference = item.get("Reference", item.get("reference", notice_id))
        deadline = _parse_date(item.get("Deadline", item.get("deadline", "")))
        pub_date = _parse_date(item.get("DatePublished", item.get("publishedDate", "")))

        if pub_date:
            try:
                if datetime.strptime(pub_date[:10], "%Y-%m-%d") < cutoff:
                    return None
            except ValueError:
                pass

        org = item.get("AgencyName", item.get("Organization", item.get("agency", "")))

        return BaseTender(
            cartel_no=f"ungm-{notice_id}",
            cartel_seq="0",
            inst_cartel_no=str(reference),
            name=_strip_html(title)[:500],
            institution_code="UN",
            institution_name=_strip_html(str(org)) or "United Nations",
            procedure_type=item.get("NoticeType", item.get("type", "")),
            status="Published",
            registration_date=pub_date,
            bid_start_date=pub_date,
            bid_end_date=deadline,
            opening_date="",
            executor_name="",
            source="ungm",
            source_url=f"https://www.ungm.org/Public/Notice/{notice_id}",
            raw=item,
        )

    def _fetch_via_html(self, days_back: int) -> list[BaseTender]:
        cutoff = datetime.now() - timedelta(days=days_back)
        tenders: list[BaseTender] = []

        resp = self._client.get(UNGM_SEARCH_URL)
        resp.raise_for_status()

        # Parse table rows
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", resp.text, re.DOTALL)
        for row in rows:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
            if len(cells) < 4:
                continue

            title = _strip_html(cells[1]) if len(cells) > 1 else ""
            if not title or len(title) < 10:
                continue

            reference = _strip_html(cells[0])
            links = re.findall(r'href="([^"]+)"', row)
            url = links[0] if links else UNGM_SEARCH_URL
            if url.startswith("/"):
                url = f"https://www.ungm.org{url}"

            notice_id = reference or str(hash(title) % 100000)

            tenders.append(BaseTender(
                cartel_no=f"ungm-{notice_id}",
                cartel_seq="0",
                inst_cartel_no=f"UNGM-{reference}",
                name=title[:500],
                institution_code="UN",
                institution_name="United Nations (UNGM)",
                procedure_type="",
                status="Published",
                registration_date="",
                bid_start_date="",
                bid_end_date="",
                opening_date="",
                executor_name="",
                source="ungm",
                source_url=url,
                raw={"title": title, "reference": reference},
            ))

        return tenders

    def close(self) -> None:
        self._client.close()
