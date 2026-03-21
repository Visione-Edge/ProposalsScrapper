"""CAF (Banco de Desarrollo de América Latina) procurement scraper."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

import httpx

from sources.base import BaseTender

logger = logging.getLogger(__name__)

CALLS_URL = "https://www.caf.com/en/work-with-us/calls/"
BIDS_URL = "https://www.caf.com/en/work-with-us/bids/"

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub("", text).strip()


def _parse_date(date_str: str) -> str:
    if not date_str:
        return ""
    for fmt in ("%B %d, %Y", "%d/%m/%Y", "%Y-%m-%d", "%b %d, %Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return date_str


class CAFClient:
    """Scrapes procurement calls from CAF website."""

    def __init__(self, request_delay: float = 2.0):
        self.request_delay = request_delay
        self._client = httpx.Client(timeout=30.0, follow_redirects=True, verify=False)

    def fetch_recent_tenders(self, days_back: int = 90, **kwargs) -> list[BaseTender]:
        tenders: list[BaseTender] = []
        cutoff = datetime.now() - timedelta(days=days_back)

        for url, notice_type in [(CALLS_URL, "Call"), (BIDS_URL, "Bid")]:
            try:
                resp = self._client.get(url)
                resp.raise_for_status()
                items = self._parse_page(resp.text, url, notice_type, cutoff)
                tenders.extend(items)
            except Exception as e:
                logger.warning("CAF: error fetching %s: %s", url, e)

        logger.info("CAF: %d notices fetched", len(tenders))
        return tenders

    def _parse_page(self, html: str, base_url: str, notice_type: str,
                    cutoff: datetime) -> list[BaseTender]:
        tenders: list[BaseTender] = []

        # CAF uses article/card patterns for listings
        articles = re.findall(
            r'<article[^>]*>(.*?)</article>', html, re.DOTALL
        )
        if not articles:
            # Fallback: look for list items with links
            articles = re.findall(
                r'<li[^>]*class="[^"]*item[^"]*"[^>]*>(.*?)</li>', html, re.DOTALL
            )
        if not articles:
            # Fallback: look for any linked content blocks
            articles = re.findall(
                r'<div[^>]*class="[^"]*card[^"]*"[^>]*>(.*?)</div>\s*</div>',
                html, re.DOTALL
            )

        for i, article in enumerate(articles):
            # Extract title and link
            link_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', article, re.DOTALL)
            if not link_match:
                continue

            href = link_match.group(1)
            title = _strip_html(link_match.group(2))
            if not title or len(title) < 10:
                continue

            # Build full URL
            if href.startswith("/"):
                href = f"https://www.caf.com{href}"

            # Try to find a date
            date_match = re.search(
                r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{4}|\w+ \d{1,2},?\s*\d{4})',
                article
            )
            pub_date = _parse_date(date_match.group(1)) if date_match else ""

            if pub_date:
                try:
                    if datetime.strptime(pub_date[:10], "%Y-%m-%d") < cutoff:
                        continue
                except ValueError:
                    pass

            # Generate a stable ID from the URL
            slug = href.rstrip("/").split("/")[-1]
            notice_id = slug or str(i)

            tenders.append(BaseTender(
                cartel_no=f"caf-{notice_id}",
                cartel_seq="0",
                inst_cartel_no=f"CAF-{notice_type}-{notice_id}",
                name=title[:500],
                institution_code="CAF",
                institution_name="CAF - Banco de Desarrollo de América Latina",
                procedure_type=notice_type,
                status="Published",
                registration_date=pub_date,
                bid_start_date=pub_date,
                bid_end_date="",
                opening_date="",
                executor_name="",
                source="caf",
                source_url=href,
                raw={"title": title, "url": href, "type": notice_type,
                     "date": pub_date},
            ))

        return tenders

    def close(self) -> None:
        self._client.close()
