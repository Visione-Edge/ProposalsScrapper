"""Multi-source procurement scraping registry."""

from __future__ import annotations

import logging
from typing import Any

from .base import BaseTender, SourceClient, SOURCE_LABELS

logger = logging.getLogger(__name__)


def get_enabled_sources(config: dict) -> list[tuple[str, SourceClient]]:
    """Return instantiated clients for all enabled sources."""
    sources_cfg = config.get("sources", {})
    enabled: list[tuple[str, SourceClient]] = []

    # SICOP
    sicop_cfg = sources_cfg.get("sicop", {"enabled": True})
    if sicop_cfg.get("enabled", True):
        from .sicop.client import SICOPSourceClient
        client = SICOPSourceClient(
            page_size=sicop_cfg.get("page_size", config.get("page_size", 50)),
            request_delay=sicop_cfg.get("request_delay", config.get("request_delay", 1.0)),
        )
        enabled.append(("sicop", client))

    # World Bank
    wb_cfg = sources_cfg.get("worldbank", {})
    if wb_cfg.get("enabled", False):
        from .worldbank.client import WorldBankClient
        client = WorldBankClient(
            country=wb_cfg.get("country", "Costa Rica"),
            rows_per_page=wb_cfg.get("rows_per_page", 50),
        )
        enabled.append(("worldbank", client))

    # UNDP
    undp_cfg = sources_cfg.get("undp", {})
    if undp_cfg.get("enabled", False):
        from .undp.client import UNDPClient
        client = UNDPClient(
            region=undp_cfg.get("region", "RLA"),
            country_filter=undp_cfg.get("country_filter", "COSTA RICA"),
        )
        enabled.append(("undp", client))

    # IDB/BID
    idb_cfg = sources_cfg.get("idb", {})
    if idb_cfg.get("enabled", False):
        from .idb.client import IDBClient
        client = IDBClient(
            country_filter=idb_cfg.get("country_filter", "Costa Rica"),
        )
        enabled.append(("idb", client))

    # BCIE
    bcie_cfg = sources_cfg.get("bcie", {})
    if bcie_cfg.get("enabled", False):
        from .bcie.client import BCIEClient
        client = BCIEClient(
            request_delay=bcie_cfg.get("request_delay", 2.0),
        )
        enabled.append(("bcie", client))

    # CAF
    caf_cfg = sources_cfg.get("caf", {})
    if caf_cfg.get("enabled", False):
        from .caf.client import CAFClient
        client = CAFClient(
            request_delay=caf_cfg.get("request_delay", 2.0),
        )
        enabled.append(("caf", client))

    return enabled
