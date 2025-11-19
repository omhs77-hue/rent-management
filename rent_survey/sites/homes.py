"""LIFULL HOME'S search implementation."""
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


class HomesClient(SiteClient):
    site_name = "homes"
    BASE_URL = "https://www.homes.co.jp/chintai/list/"

    def __init__(self, http_client: RateLimitedClient):
        super().__init__(http_client)

    def search(self, query: SurveyQuery, limit: int) -> List[RentalListing]:
        params = self._build_query_params(query)
        response = self.http.get(self.BASE_URL, params=params)
        soup = self.build_soup(response.text)
        listings: List[RentalListing] = []
        for card in soup.select("div.mod-property-list div.property" ):
            listing = self._parse_card(card, query)
            if listing:
                listings.append(listing)
            if len(listings) >= limit:
                break
        return listings[:limit]

    def _build_query_params(self, query: SurveyQuery) -> dict:
        params = {
            "keyword": query.station,
            "bukken_type": query.building_type or "",
            "madori": query.madori or "",
            "minutes": query.minutes or "",
        }
        if query.area:
            params["area_min"] = max(0, query.area - query.area_tolerance)
            params["area_max"] = query.area + query.area_tolerance
        if query.age_max:
            params["age"] = query.age_max
        if query.auto_lock == "required":
            params["equipment"] = "autolock"
        if query.bath_toilet == "required":
            params["bath_toilet"] = "separate"
        return params

    def _parse_card(self, card: BeautifulSoup, query: SurveyQuery) -> RentalListing | None:
        title_el = card.select_one("h2.property-title a")
        title = title_el.get_text(strip=True) if title_el else ""
        url = title_el["href"] if title_el and title_el.has_attr("href") else self.BASE_URL
        rent_el = card.select_one("span.price strong")
        management_el = card.select_one("span.price span.property-data")
        deposit_el = card.select_one("span.shikikin")
        key_el = card.select_one("span.reikin")
        area_el = card.select_one("span.menseki")
        madori_el = card.select_one("span.madori")
        built_el = card.select_one("span.chikunen")
        station_el = card.select_one("div.property-point p")
        built_text = built_el.get_text(strip=True) if built_el else None
        built_info = parse_built_info(built_text or "")
        built_at = built_info["built_at"]
        built_age = built_info["built_age_years"]
        station_info = parse_station_walk(station_el.get_text(strip=True) if station_el else "")
        listing = RentalListing(
            title=title,
            site=self.site_name,
            url=self._absolute_url(url),
            rent=parse_yen(rent_el.get_text(strip=True) if rent_el else ""),
            management_fee=parse_yen(management_el.get_text(strip=True) if management_el else ""),
            total_rent=None,
            deposit=parse_yen(deposit_el.get_text(strip=True) if deposit_el else ""),
            key_money=parse_yen(key_el.get_text(strip=True) if key_el else ""),
            area=parse_area(area_el.get_text(strip=True) if area_el else None),
            madori=madori_el.get_text(strip=True) if madori_el else None,
            built_at=built_at,
            built_at_text=built_text,
            built_age_years=built_age,
            age_diff_from_subject=compute_age_difference(query.subject_built, built_at, built_age),
            station=station_info["station"],
            walk_minutes=station_info["walk_minutes"],
            building_type=query.building_type,
            auto_lock=True if query.auto_lock == "required" else None,
            bath_toilet_separate=True if query.bath_toilet == "required" else None,
            aspect=None,
            collected_at=datetime.now(timezone.utc),
            raw={"source": "homes"},
        )
        listing.total_rent = (listing.rent or 0) + (listing.management_fee or 0)
        return listing

    def _absolute_url(self, href: str) -> str:
        if href.startswith("http"):
            return href
        return f"https://www.homes.co.jp{href}"
