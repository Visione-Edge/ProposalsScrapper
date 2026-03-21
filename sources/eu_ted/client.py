"""EU TED (Tenders Electronic Daily) API client."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from html import unescape

import httpx

from sources.base import BaseTender

logger = logging.getLogger(__name__)

# TED search API (no auth required for basic search)
TED_SEARCH_URL = "https://ted.europa.eu/api/v3.0/notices/search"

# Fallback: bulk daily XML packages
TED_PACKAGES_URL = "https://ted.europa.eu/packages/daily/"

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return unescape(_TAG_RE.sub(" ", text)).strip() if text else ""


def _parse_date(date_str: str) -> str:
    if not date_str:
        return ""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(date_str.strip()[:19], fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return date_str[:19] if len(date_str) >= 10 else date_str


class EUTEDClient:
    """Fetches procurement notices from EU TED portal."""

    def __init__(self, search_query: str = "software OR digital OR IT OR technology",
                 country: str = ""):
        self.search_query = search_query
        self.country = country
        self._client = httpx.Client(timeout=30.0, follow_redirects=True)

    def fetch_recent_tenders(self, days_back: int = 30, **kwargs) -> list[BaseTender]:
        tenders: list[BaseTender] = []

        try:
            tenders = self._fetch_via_api(days_back)
        except Exception as e:
            logger.warning("EU TED API error: %s, trying search page", e)
            try:
                tenders = self._fetch_via_search_page(days_back)
            except Exception as e2:
                logger.warning("EU TED search page error: %s", e2)

        logger.info("EU TED: %d notices fetched", len(tenders))
        return tenders

    def _fetch_via_api(self, days_back: int) -> list[BaseTender]:
        cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
        tenders: list[BaseTender] = []
        page = 1

        while True:
            params = {
                "q": self.search_query,
                "pageNum": page,
                "pageSize": 50,
                "scope": "3",  # Active notices
            }
            if self.country:
                params["country"] = self.country

            resp = self._client.get(TED_SEARCH_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", data.get("notices", []))
            if not results:
                break

            for item in results:
                tender = self._map_api_notice(item)
                if tender:
                    tenders.append(tender)

            # Limit pages
            page += 1
            total_pages = data.get("totalPages", data.get("total_pages", 1))
            if page > min(total_pages, 10):
                break

        return tenders

    def _map_api_notice(self, item: dict) -> BaseTender | None:
        notice_id = item.get("tedDocumentNumber", item.get("id", item.get("noticeId", "")))
        if not notice_id:
            return None

        title = item.get("title", item.get("titleText", ""))
        if isinstance(title, dict):
            title = title.get("en", title.get("fr", next(iter(title.values()), "")))
        title = _strip_html(str(title))

        if not title:
            return None

        org = item.get("buyerName", item.get("organisationName", ""))
        if isinstance(org, dict):
            org = org.get("en", next(iter(org.values()), ""))

        country = item.get("country", item.get("countryCode", ""))
        deadline = _parse_date(item.get("deadlineDate", item.get("deadline", "")))
        pub_date = _parse_date(item.get("publicationDate", item.get("publishedDate", "")))

        return BaseTender(
            cartel_no=f"ted-{notice_id}",
            cartel_seq="0",
            inst_cartel_no=str(notice_id),
            name=title[:500],
            institution_code=country,
            institution_name=_strip_html(str(org)) or f"EU - {country}",
            procedure_type=item.get("procedureType", item.get("type", "")),
            status="Published",
            registration_date=pub_date,
            bid_start_date=pub_date,
            bid_end_date=deadline,
            opening_date="",
            executor_name="",
            source="eu_ted",
            source_url=f"https://ted.europa.eu/en/notice/-/{notice_id}",
            raw=item,
        )

    def _fetch_via_search_page(self, days_back: int) -> list[BaseTender]:
        """Fallback: scrape the TED search results page."""
        cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
        tenders: list[BaseTender] = []

        url = "https://ted.europa.eu/en/search/result"
        params = {
            "q": self.search_query,
        }

        resp = self._client.get(url, params=params)
        resp.raise_for_status()

        # Parse notice blocks from HTML
        blocks = re.findall(
            r'<div[^>]*class="[^"]*notice[^"]*"[^>]*>(.*?)</div>\s*</div>',
            resp.text, re.DOTALL
        )

        for i, block in enumerate(blocks[:50]):
            link_match = re.search(r'href="([^"]*notice[^"]*)"', block)
            title_match = re.search(r'<h[23][^>]*>(.*?)</h[23]>', block, re.DOTALL)

            if not title_match:
                continue

            title = _strip_html(title_match.group(1))
            link = link_match.group(1) if link_match else ""
            if link and not link.startswith("http"):
                link = f"https://ted.europa.eu{link}"

            notice_id = ""
            if link:
                id_match = re.search(r'/(\d+)', link)
                notice_id = id_match.group(1) if id_match else str(i)
            else:
                notice_id = str(i)

            tenders.append(BaseTender(
                cartel_no=f"ted-{notice_id}",
                cartel_seq="0",
                inst_cartel_no=f"TED-{notice_id}",
                name=title[:500],
                institution_code="EU",
                institution_name="European Union",
                procedure_type="",
                status="Published",
                registration_date="",
                bid_start_date="",
                bid_end_date="",
                opening_date="",
                executor_name="",
                source="eu_ted",
                source_url=link or "https://ted.europa.eu",
                raw={"title": title, "url": link},
            ))

        return tenders

    def close(self) -> None:
        self._client.close()
