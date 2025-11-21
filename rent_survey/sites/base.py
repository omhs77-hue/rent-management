"""Site client base classes."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import List

from bs4 import BeautifulSoup

from ..models import RentalListing, SurveyQuery
from ..utils import RateLimitedClient

logger = logging.getLogger(__name__)


class SiteClient(ABC):
    """Abstract search client for a rent site."""

    site_name: str

    def __init__(self, http_client: RateLimitedClient):
        self.http = http_client

    @abstractmethod
    def search(self, query: SurveyQuery, limit: int) -> List[RentalListing]:
        raise NotImplementedError

    @staticmethod
    def build_soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    def log_skip(self, reason: str) -> None:
        logger.warning("%s skipped: %s", self.site_name, reason)

    @staticmethod
    def detect_blocking(html: str) -> str | None:
        """Return a human friendly reason if the response looks blocked or empty."""

        lowered = html.lower()
        markers = {
            "captcha": "blocked_by_captcha",
            "forbidden": "forbidden",
            "アクセスが頻繁": "rate_limited",
            "アクセスが集中": "rate_limited",
            "条件に一致する物件は見つかりません": "no_results_on_site",
        }
        for marker, reason in markers.items():
            if marker in lowered:
                return reason
        return None
