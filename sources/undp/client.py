"""UNDP procurement notices RSS client."""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import httpx

from sources.base import BaseTender

logger = logging.getLogger(__name__)

RSS_BASE = "https://procurement-notices.undp.org/rss_feeds"

# XML namespaces used in UNDP RSS
NS = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rss": "http://purl.org/rss/1.0/",
    "dc": "http://purl.org/dc/elements/1.1/",
}
# UNDP custom namespace prefix in tags
_UNDP_NS = "http://procurement-notices.undp.org/rss_feed/spec/"


def _get_undp_field(item: ET.Element, field: str) -> str:
    """Get a field from UNDP's custom namespace."""
    el = item.find(f"{{{_UNDP_NS}}}{field}")
    return (el.text or "").strip() if el is not None else ""


def _parse_date(date_str: str) -> str:
    if not date_str:
        return ""
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%d-%b-%y", "%d %B %Y"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return date_str[:19] if len(date_str) >= 10 else date_str


def _extract_id_from_url(url: str) -> str:
    """Extract notice/negotiation ID from UNDP URL."""
    m = re.search(r"(?:notice_id|nego_id)=(\d+)", url)
    return m.group(1) if m else url.split("/")[-1]


class UNDPClient:
    """Fetches procurement notices from UNDP RSS feed."""

    def __init__(self, region: str = "RLA", country_filter: str = "COSTA RICA"):
        self.region = region
        self.country_filter = country_filter.upper()
        self._client = httpx.Client(timeout=30.0, follow_redirects=True)

    def fetch_recent_tenders(self, days_back: int = 30, **kwargs) -> list[BaseTender]:
        url = f"{RSS_BASE}/{self.region}.xml"
        resp = self._client.get(url)
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        items = root.findall("rss:item", NS)

        cutoff = datetime.now() - timedelta(days=days_back)
        tenders: list[BaseTender] = []

        for item in items:
            tender = self._map_item(item, cutoff)
            if tender:
                tenders.append(tender)

        logger.info("UNDP: %d notices fetched (region=%s, country=%s)",
                     len(tenders), self.region, self.country_filter)
        return tenders

    def _map_item(self, item: ET.Element, cutoff: datetime) -> BaseTender | None:
        # Filter by country
        country = _get_undp_field(item, "duty_station_cty").upper().strip()
        if self.country_filter and self.country_filter not in country:
            return None

        title_el = item.find("rss:title", NS)
        link_el = item.find("rss:link", NS)
        date_el = item.find("dc:date", NS)

        title = (title_el.text or "").strip() if title_el is not None else ""
        link = (link_el.text or "").strip() if link_el is not None else ""
        pub_date = (date_el.text or "").strip() if date_el is not None else ""

        if not title or not link:
            return None

        deadline = _get_undp_field(item, "deadline")
        subject = _get_undp_field(item, "subject") or title
        area = _get_undp_field(item, "area_desc")
        station = _get_undp_field(item, "duty_station")
        notice_id = _extract_id_from_url(link)

        reg_date = _parse_date(pub_date)

        # Filter by cutoff date
        if reg_date:
            try:
                if datetime.strptime(reg_date[:10], "%Y-%m-%d") < cutoff:
                    return None
            except ValueError:
                pass

        return BaseTender(
            cartel_no=f"undp-{notice_id}",
            cartel_seq="0",
            inst_cartel_no=f"UNDP-{notice_id}",
            name=subject[:500],
            institution_code="UNDP",
            institution_name=station or "UNDP",
            procedure_type=area,
            status="Published",
            registration_date=reg_date,
            bid_start_date=reg_date,
            bid_end_date=_parse_date(deadline),
            opening_date="",
            executor_name="",
            source="undp",
            source_url=link,
            raw={"title": title, "link": link, "date": pub_date,
                 "deadline": deadline, "area": area, "country": country,
                 "station": station},
        )

    def close(self) -> None:
        self._client.close()
