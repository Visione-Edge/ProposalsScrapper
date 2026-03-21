"""UNOPS eSourcing procurement scraper."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

import httpx

from sources.base import BaseTender

logger = logging.getLogger(__name__)

UNOPS_URL = "https://esourcing.unops.org/"

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub("", text).strip()


def _parse_date(date_str: str) -> str:
    if not date_str:
        return ""
    for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y", "%B %d, %Y",
                "%Y-%m-%dT%H:%M:%S", "%d %b %Y"):
        try:
            return datetime.strptime(date_str.strip()[:19], fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return date_str[:19] if len(date_str) >= 10 else date_str


class UNOPSClient:
    """Scrapes procurement notices from UNOPS eSourcing portal."""

    def __init__(self, request_delay: float = 2.0):
        self.request_delay = request_delay
        self._client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ProposalsScrapper/1.0)"},
        )

    def fetch_recent_tenders(self, days_back: int = 30, **kwargs) -> list[BaseTender]:
        tenders: list[BaseTender] = []
        cutoff = datetime.now() - timedelta(days=days_back)

        try:
            resp = self._client.get(UNOPS_URL)
            resp.raise_for_status()
            tenders = self._parse_page(resp.text, cutoff)
        except Exception as e:
            logger.warning("UNOPS error: %s", e)

        logger.info("UNOPS: %d notices fetched", len(tenders))
        return tenders

    def _parse_page(self, html: str, cutoff: datetime) -> list[BaseTender]:
        tenders: list[BaseTender] = []

        # Try table rows
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL)
        for row in rows:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
            if len(cells) < 3:
                continue

            # Find the cell with the most text as title
            best_cell = ""
            for cell in cells:
                clean = _strip_html(cell)
                if len(clean) > len(best_cell):
                    best_cell = clean

            if len(best_cell) < 10:
                continue

            # Extract link and ID
            links = re.findall(r'href="([^"]+)"', row)
            url = links[0] if links else UNOPS_URL
            if url.startswith("/"):
                url = f"https://esourcing.unops.org{url}"

            # Try to extract reference number
            ref_match = re.search(r'(RFP|RFQ|ITB|EOI|LRFQ)[-/\s]*\d+[-/\w]*', row)
            reference = ref_match.group() if ref_match else _strip_html(cells[0])

            notice_id = reference or str(hash(best_cell) % 100000)

            # Find dates
            dates = re.findall(r'\d{1,2}[-/]\w{3}[-/]\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}', row)
            pub_date = _parse_date(dates[0]) if dates else ""
            deadline = _parse_date(dates[1]) if len(dates) > 1 else ""

            if pub_date:
                try:
                    if datetime.strptime(pub_date[:10], "%Y-%m-%d") < cutoff:
                        continue
                except ValueError:
                    pass

            tenders.append(BaseTender(
                cartel_no=f"unops-{notice_id}",
                cartel_seq="0",
                inst_cartel_no=f"UNOPS-{reference}",
                name=best_cell[:500],
                institution_code="UNOPS",
                institution_name="UNOPS",
                procedure_type="",
                status="Published",
                registration_date=pub_date,
                bid_start_date=pub_date,
                bid_end_date=deadline,
                opening_date="",
                executor_name="",
                source="unops",
                source_url=url,
                raw={"title": best_cell, "reference": reference, "url": url},
            ))

        # Try card/article patterns
        if not tenders:
            articles = re.findall(
                r'<(?:article|div)[^>]*class="[^"]*(?:notice|opportunity|tender|card)[^"]*"[^>]*>(.*?)</(?:article|div)>',
                html, re.DOTALL
            )
            for i, article in enumerate(articles[:50]):
                link_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', article, re.DOTALL)
                if not link_match:
                    continue
                title = _strip_html(link_match.group(2))
                if not title or len(title) < 10:
                    continue

                href = link_match.group(1)
                if href.startswith("/"):
                    href = f"https://esourcing.unops.org{href}"

                tenders.append(BaseTender(
                    cartel_no=f"unops-{i}",
                    cartel_seq="0",
                    inst_cartel_no=f"UNOPS-{i}",
                    name=title[:500],
                    institution_code="UNOPS",
                    institution_name="UNOPS",
                    procedure_type="",
                    status="Published",
                    registration_date="",
                    bid_start_date="",
                    bid_end_date="",
                    opening_date="",
                    executor_name="",
                    source="unops",
                    source_url=href,
                    raw={"title": title, "url": href},
                ))

        return tenders

    def close(self) -> None:
        self._client.close()
