"""CCSS (Caja Costarricense de Seguro Social) open data client."""

from __future__ import annotations

import csv
import io
import logging
import re
from datetime import datetime, timedelta

import httpx

from sources.base import BaseTender

logger = logging.getLogger(__name__)

# CCSS open data page
OPEN_DATA_URL = "https://www.ccss.sa.cr/datos-abiertos-licitaciones"

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


class CCSSClient:
    """Scrapes procurement data from CCSS open data portal."""

    def __init__(self, request_delay: float = 2.0):
        self.request_delay = request_delay
        self._client = httpx.Client(timeout=60.0, follow_redirects=True)

    def fetch_recent_tenders(self, days_back: int = 90, **kwargs) -> list[BaseTender]:
        tenders: list[BaseTender] = []
        cutoff = datetime.now() - timedelta(days=days_back)

        try:
            # Try to find CSV/JSON links on the open data page
            resp = self._client.get(OPEN_DATA_URL)
            resp.raise_for_status()

            # Look for CSV download links
            csv_links = re.findall(
                r'href="([^"]+\.csv[^"]*)"', resp.text, re.IGNORECASE
            )
            json_links = re.findall(
                r'href="([^"]+\.json[^"]*)"', resp.text, re.IGNORECASE
            )

            # Try JSON first, then CSV
            for link in json_links + csv_links:
                if not link.startswith("http"):
                    link = f"https://www.ccss.sa.cr{link}"
                try:
                    data_resp = self._client.get(link)
                    data_resp.raise_for_status()

                    if link.lower().endswith(".json") or "json" in link.lower():
                        items = data_resp.json()
                        if isinstance(items, list):
                            for item in items:
                                tender = self._map_json_item(item, cutoff)
                                if tender:
                                    tenders.append(tender)
                    else:
                        reader = csv.DictReader(io.StringIO(data_resp.text))
                        for row in reader:
                            tender = self._map_csv_row(row, cutoff)
                            if tender:
                                tenders.append(tender)

                    if tenders:
                        break  # Got data from first working link
                except Exception as e:
                    logger.debug("CCSS: error fetching %s: %s", link, e)
                    continue

            # Fallback: parse HTML tables on the page
            if not tenders:
                tenders = self._parse_html_tables(resp.text, cutoff)

        except Exception as e:
            logger.warning("CCSS: error: %s", e)

        logger.info("CCSS: %d notices fetched", len(tenders))
        return tenders

    def _map_json_item(self, item: dict, cutoff: datetime) -> BaseTender | None:
        name = item.get("nombre", item.get("descripcion", item.get("title", "")))
        if not name:
            return None

        notice_id = str(item.get("id", item.get("numero", hash(name) % 100000)))
        pub_date = _parse_date(item.get("fecha", item.get("fecha_publicacion", "")))

        if pub_date:
            try:
                if datetime.strptime(pub_date[:10], "%Y-%m-%d") < cutoff:
                    return None
            except ValueError:
                pass

        return BaseTender(
            cartel_no=f"ccss-{notice_id}",
            cartel_seq="0",
            inst_cartel_no=f"CCSS-{notice_id}",
            name=name[:500],
            institution_code="CCSS",
            institution_name="Caja Costarricense de Seguro Social",
            procedure_type=item.get("tipo", item.get("modalidad", "")),
            status=item.get("estado", "Published"),
            registration_date=pub_date,
            bid_start_date=pub_date,
            bid_end_date=_parse_date(item.get("fecha_cierre", item.get("fecha_limite", ""))),
            opening_date="",
            executor_name=item.get("unidad", ""),
            source="ccss",
            source_url=item.get("url", OPEN_DATA_URL),
            raw=item,
        )

    def _map_csv_row(self, row: dict, cutoff: datetime) -> BaseTender | None:
        # Try common column names
        name = ""
        for key in ["nombre", "descripcion", "title", "NOMBRE", "DESCRIPCION"]:
            if row.get(key):
                name = row[key]
                break
        if not name:
            return None

        notice_id = ""
        for key in ["id", "numero", "ID", "NUMERO"]:
            if row.get(key):
                notice_id = str(row[key])
                break
        if not notice_id:
            notice_id = str(hash(name) % 100000)

        pub_date = ""
        for key in ["fecha", "fecha_publicacion", "FECHA"]:
            if row.get(key):
                pub_date = _parse_date(row[key])
                break

        if pub_date:
            try:
                if datetime.strptime(pub_date[:10], "%Y-%m-%d") < cutoff:
                    return None
            except ValueError:
                pass

        deadline = ""
        for key in ["fecha_cierre", "fecha_limite", "FECHA_CIERRE"]:
            if row.get(key):
                deadline = _parse_date(row[key])
                break

        return BaseTender(
            cartel_no=f"ccss-{notice_id}",
            cartel_seq="0",
            inst_cartel_no=f"CCSS-{notice_id}",
            name=name[:500],
            institution_code="CCSS",
            institution_name="Caja Costarricense de Seguro Social",
            procedure_type=row.get("tipo", row.get("modalidad", row.get("TIPO", ""))),
            status=row.get("estado", row.get("ESTADO", "Published")),
            registration_date=pub_date,
            bid_start_date=pub_date,
            bid_end_date=deadline,
            opening_date="",
            executor_name=row.get("unidad", row.get("UNIDAD", "")),
            source="ccss",
            source_url=OPEN_DATA_URL,
            raw=row,
        )

    def _parse_html_tables(self, html: str, cutoff: datetime) -> list[BaseTender]:
        tenders: list[BaseTender] = []
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL)

        for row in rows[1:]:  # Skip header
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
            if len(cells) < 3:
                continue

            name = _strip_html(cells[1]) if len(cells) > 1 else ""
            if not name or len(name) < 5:
                continue

            notice_id = _strip_html(cells[0]) if cells else str(hash(name) % 100000)
            links = re.findall(r'href="([^"]+)"', row)
            url = links[0] if links else OPEN_DATA_URL
            if url.startswith("/"):
                url = f"https://www.ccss.sa.cr{url}"

            tenders.append(BaseTender(
                cartel_no=f"ccss-{notice_id}",
                cartel_seq="0",
                inst_cartel_no=f"CCSS-{notice_id}",
                name=name[:500],
                institution_code="CCSS",
                institution_name="Caja Costarricense de Seguro Social",
                procedure_type="",
                status="Published",
                registration_date="",
                bid_start_date="",
                bid_end_date="",
                opening_date="",
                executor_name="",
                source="ccss",
                source_url=url,
                raw={"name": name, "id": notice_id},
            ))

        return tenders

    def close(self) -> None:
        self._client.close()
