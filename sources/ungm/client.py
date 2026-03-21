"""UNGM (United Nations Global Marketplace) client.

UNGM is a JavaScript-rendered Angular/jQuery app that loads data via AJAX
after page render. Without a headless browser, we cannot access the data.
This client is a placeholder that returns empty results.
Future: integrate with Playwright or Selenium for headless scraping.
"""

from __future__ import annotations

import logging

from sources.base import BaseTender

logger = logging.getLogger(__name__)


class UNGMClient:
    """UNGM client — requires headless browser (not yet implemented)."""

    def __init__(self, request_delay: float = 2.0):
        pass

    def fetch_recent_tenders(self, days_back: int = 30, **kwargs) -> list[BaseTender]:
        logger.info("UNGM: requires headless browser — skipping (0 results)")
        return []

    def close(self) -> None:
        pass
