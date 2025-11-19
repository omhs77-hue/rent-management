"""SUUMO search implementation."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List

from bs4 import BeautifulSoup

from ..models import RentalListing, SurveyQuery
from ..utils import (
    RateLimitedClient,
    compute_age_difference,
    parse_area,
    parse_built_info,
    parse_station_walk,
    parse_yen,
)
from .base import SiteClient

logger = logging.getLogger(__name__)


class SuumoClient(SiteClient):
    site_name = "suumo"
    BASE_URL = "https://suumo.jp/chintai/"

    def __init__(self, http_client: RateLimitedClient):
        super().__init__(http_client)

    def search(self, query: SurveyQuery, limit: int) -> List[RentalListing]:
        params = self._build_query_params(query)
        response = self.http.get(self.BASE_URL, params=params)
        soup = self.build_soup(response.text)
        listings: List[RentalListing] = []
        for cassette in soup.select("div.cassetteitem"):
            listings.extend(self._parse_cassette(cassette, query))
            if len(listings) >= limit:
                break
        if not listings:
            reason = self.detect_blocking(response.text) or "no_listings_parsed"
            self.log_skip(reason)
            raise ValueError(reason)
        return listings[:limit]

    def _build_query_params(self, query: SurveyQuery) -> dict:
        params = {
            "sc": query.station,
            "md": query.madori or "",
            "et": query.minutes or "",
            "fw": query.station,
        }
        if query.area:
            params["ma"] = max(0, query.area - query.area_tolerance)
            params["ta"] = query.area + query.area_tolerance
        if query.age_max:
            params["cb"] = 0
            params["ct"] = query.age_max
        return params

    def _parse_cassette(self, cassette: BeautifulSoup, query: SurveyQuery) -> List[RentalListing]:
        title = cassette.select_one("div.cassetteitem_content-title")
        title_text = title.get_text(strip=True) if title else ""
        station_text = cassette.select_one("div.cassetteitem_detail-text")
        station_info = parse_station_walk(station_text.get_text(strip=True) if station_text else "")
        building_type = cassette.select_one("div.cassetteitem_content-label")
        table = cassette.select_one("table.cassetteitem_other")
        rows = table.select("tbody tr") if table else []
        listings: List[RentalListing] = []
        for row in rows:
            rent_cell = row.select_one("td.cassetteitem_price--rent")
            admin_cell = row.select_one("td.cassetteitem_price--administration")
            deposit_cell = row.select_one("td.cassetteitem_price--deposit")
            key_cell = row.select_one("td.cassetteitem_price--gratuity")
            madori_cell = row.select_one("td.cassetteitem_madori")
            area_cell = row.select_one("td.cassetteitem_menseki")
            link = row.select_one("a")
            built_cell = row.select_one("td.cassetteitem_col4")
            built_text = built_cell.get_text(strip=True) if built_cell else None
            built_info = parse_built_info(built_text or "")
            built_at = built_info["built_at"]
            built_age = built_info["built_age_years"]
            listing = RentalListing(
                title=title_text,
                site=self.site_name,
                url=self._absolute_url(link["href"]) if link and link.has_attr("href") else self.BASE_URL,
                rent=parse_yen(rent_cell.get_text(strip=True) if rent_cell else ""),
                management_fee=parse_yen(admin_cell.get_text(strip=True) if admin_cell else ""),
                total_rent=None,
                deposit=parse_yen(deposit_cell.get_text(strip=True) if deposit_cell else ""),
                key_money=parse_yen(key_cell.get_text(strip=True) if key_cell else ""),
                area=parse_area(area_cell.get_text(strip=True) if area_cell else None),
                madori=madori_cell.get_text(strip=True) if madori_cell else None,
                built_at=built_at,
                built_at_text=built_text,
                built_age_years=built_age,
                age_diff_from_subject=compute_age_difference(query.subject_built, built_at, built_age),
                station=station_info["station"],
                walk_minutes=station_info["walk_minutes"],
                building_type=building_type.get_text(strip=True) if building_type else None,
                auto_lock=None,
                bath_toilet_separate=None,
                aspect=None,
                collected_at=datetime.now(timezone.utc),
                raw={"source": "suumo"},
            )
            listing.total_rent = (listing.rent or 0) + (listing.management_fee or 0)
            listings.append(listing)
        return listings

    def _absolute_url(self, href: str) -> str:
        if href.startswith("http"):
            return href
        return f"https://suumo.jp{href}"
