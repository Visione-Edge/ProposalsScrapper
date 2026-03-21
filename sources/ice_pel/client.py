"""ICE / Grupo ICE (Portal PEL) scraper."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

import httpx

from sources.base import BaseTender

logger = logging.getLogger(__name__)

PEL_URL = "https://apps.grupoice.com/PEL/"
TRANSPARENCIA_URL = "https://www.grupoice.com/wps/portal/ICE/Transparencia/compras"

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub("", text).strip()


def _parse_date(date_str: str) -> str:
    if not date_str:
        return ""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return date_str


class ICEPELClient:
    """Scrapes procurement notices from ICE/Grupo ICE PEL portal."""

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

        # Try PEL portal
        try:
            pel_tenders = self._fetch_pel(cutoff)
            tenders.extend(pel_tenders)
        except Exception as e:
            logger.warning("ICE PEL error: %s", e)

        # Try transparencia page as fallback
        if not tenders:
            try:
                trans_tenders = self._fetch_transparencia(cutoff)
                tenders.extend(trans_tenders)
            except Exception as e:
                logger.warning("ICE Transparencia error: %s", e)

        logger.info("ICE/PEL: %d notices fetched", len(tenders))
        return tenders

    def _fetch_pel(self, cutoff: datetime) -> list[BaseTender]:
        resp = self._client.get(PEL_URL)
        resp.raise_for_status()
        return self._parse_notices(resp.text, PEL_URL, cutoff)

    def _fetch_transparencia(self, cutoff: datetime) -> list[BaseTender]:
        resp = self._client.get(TRANSPARENCIA_URL)
        resp.raise_for_status()
        return self._parse_notices(resp.text, TRANSPARENCIA_URL, cutoff)

    def _parse_notices(self, html: str, base_url: str, cutoff: datetime) -> list[BaseTender]:
        tenders: list[BaseTender] = []

        # Try table rows
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL)
        for row in rows:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
            if len(cells) < 3:
                continue

            name = _strip_html(cells[1]) if len(cells) > 1 else ""
            if not name or len(name) < 10:
                continue

            notice_id = _strip_html(cells[0])
            links = re.findall(r'href="([^"]+)"', row)
            url = links[0] if links else base_url
            if url.startswith("/"):
                url = f"https://apps.grupoice.com{url}"

            # Try to find dates
            date_str = ""
            deadline_str = ""
            for cell in cells[2:]:
                clean = _strip_html(cell)
                date_match = re.match(r"\d{1,2}/\d{1,2}/\d{4}", clean)
                if date_match:
                    if not date_str:
                        date_str = date_match.group()
                    else:
                        deadline_str = date_match.group()

            pub_date = _parse_date(date_str)
            if pub_date:
                try:
                    if datetime.strptime(pub_date[:10], "%Y-%m-%d") < cutoff:
                        continue
                except ValueError:
                    pass

            tenders.append(BaseTender(
                cartel_no=f"ice-{notice_id}",
                cartel_seq="0",
                inst_cartel_no=f"ICE-{notice_id}",
                name=name[:500],
                institution_code="ICE",
                institution_name="Grupo ICE",
                procedure_type="",
                status="Published",
                registration_date=pub_date,
                bid_start_date=pub_date,
                bid_end_date=_parse_date(deadline_str),
                opening_date="",
                executor_name="",
                source="ice_pel",
                source_url=url,
                raw={"name": name, "id": notice_id, "url": url},
            ))

        # Also try article/card patterns
        if not tenders:
            articles = re.findall(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)
            for i, article in enumerate(articles):
                link_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', article, re.DOTALL)
                if not link_match:
                    continue
                title = _strip_html(link_match.group(2))
                if not title or len(title) < 10:
                    continue
                href = link_match.group(1)
                if href.startswith("/"):
                    href = f"https://apps.grupoice.com{href}"

                tenders.append(BaseTender(
                    cartel_no=f"ice-art-{i}",
                    cartel_seq="0",
                    inst_cartel_no=f"ICE-{i}",
                    name=title[:500],
                    institution_code="ICE",
                    institution_name="Grupo ICE",
                    procedure_type="",
                    status="Published",
                    registration_date="",
                    bid_start_date="",
                    bid_end_date="",
                    opening_date="",
                    executor_name="",
                    source="ice_pel",
                    source_url=href,
                    raw={"title": title, "url": href},
                ))

        return tenders

    def close(self) -> None:
        self._client.close()
