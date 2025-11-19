"""High level orchestration for rent survey."""
from __future__ import annotations

import logging
from typing import Dict, List, Type

from .models import RentalListing, SurveyQuery, SurveyResult
from .sites.homes import HomesClient
from .sites.suumo import SuumoClient
from .sites.base import SiteClient
from .utils import RateLimitedClient, deduplicate, filter_listings

logger = logging.getLogger(__name__)

SITE_REGISTRY: Dict[str, Type[SiteClient]] = {
    "homes": HomesClient,
    "suumo": SuumoClient,
}


class SurveyRunner:
    """Run a rent survey for the provided query."""

    def __init__(self, query: SurveyQuery, user_agent: str, min_interval: float, request_timeout: float = 30.0):
        self.query = query
        self.user_agent = user_agent
        self.min_interval = min_interval
        self.request_timeout = request_timeout

    def run(self) -> SurveyResult:
        listings: List[RentalListing] = []
        skipped: Dict[str, str] = {}
        for site_name in self.query.sites:
            client_cls = SITE_REGISTRY.get(site_name)
            if not client_cls:
                skipped[site_name] = "unsupported_site"
                continue
            http = RateLimitedClient(self.user_agent, min_interval=self.min_interval, timeout=self.request_timeout)
            client = client_cls(http)
            try:
                site_results = client.search(self.query, self.query.max_listings)
                listings.extend(site_results)
            except Exception as exc:  # pragma: no cover - network dependent
                logger.warning("Failed to fetch from %s: %s", site_name, exc)
                skipped[site_name] = str(exc)
            finally:
                http.close()
        filtered = filter_listings(listings, self.query)
        deduped = deduplicate(filtered)
        return SurveyResult(
            raw_listings=listings,
            filtered_listings=filtered,
            deduplicated_listings=deduped,
            skipped_sites=skipped,
        )
