"""Utility helpers for parsing listing fields."""
from __future__ import annotations

import csv
import json
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import httpx

from .models import RentalListing, SurveyQuery

YEN_PATTERN = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*(万円|万|円)")
AREA_PATTERN = re.compile(r"([0-9]+(?:\.[0-9]+)?)")
DATE_PATTERN = re.compile(r"(\d{4})年(\d{1,2})月")
BUILT_AGE_PATTERN = re.compile(r"築(\d+)年")
STATION_PATTERN = re.compile(r"(?P<station>[^\s　]+)\s*徒歩\s*(?P<minutes>\d+)")


class RateLimitedClient:
    """Thin wrapper around httpx.Client with human-like pacing."""

    def __init__(
        self,
        user_agent: str,
        min_interval: float = 1.0,
        timeout: float = 30.0,
        follow_redirects: bool = True,
    ):
        self.client = httpx.Client(
            headers={"User-Agent": user_agent}, timeout=timeout, follow_redirects=follow_redirects
        )
        self.min_interval = max(0.1, min_interval)
        self._next_request = 0.0

    def get(self, url: str, params: Optional[Dict[str, str]] = None) -> httpx.Response:
        now = time.monotonic()
        wait = self._next_request - now
        if wait > 0:
            time.sleep(wait)
        response = self.client.get(url, params=params)
        self._next_request = time.monotonic() + self.min_interval
        response.raise_for_status()
        return response

    def close(self) -> None:
        self.client.close()


def ensure_output_path(output_path: Optional[str], output_format: str) -> Path:
    base_dir = Path("outputs")
    base_dir.mkdir(parents=True, exist_ok=True)
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    suffix = ".csv" if output_format == "csv" else ".jsonl"
    return base_dir / f"rent-survey-{timestamp}{suffix}"


def write_output(listings: Iterable[RentalListing], output_path: Path, output_format: str) -> None:
    records = [listing_to_dict(l) for l in listings]
    if output_format == "csv":
        if not records:
            output_path.write_text("", encoding="utf-8")
            return
        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0]).keys())
            writer.writeheader()
            writer.writerows(records)
    else:
        with output_path.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")


def listing_to_dict(listing: RentalListing) -> Dict[str, object]:
    return {
        "title": listing.title,
        "site": listing.site,
        "sources": listing.sources or [listing.site],
        "url": listing.url,
        "rent": listing.rent,
        "management_fee": listing.management_fee,
        "total_rent": listing.total_rent,
        "deposit": listing.deposit,
        "key_money": listing.key_money,
        "area": listing.area,
        "madori": listing.madori,
        "built_at": listing.built_at.isoformat() if listing.built_at else listing.built_at_text,
        "built_age_years": listing.built_age_years,
        "age_diff_from_subject": listing.age_diff_from_subject,
        "station": listing.station,
        "walk_minutes": listing.walk_minutes,
        "building_type": listing.building_type,
        "auto_lock": listing.auto_lock,
        "bath_toilet_separate": listing.bath_toilet_separate,
        "aspect": listing.aspect,
        "collected_at": listing.collected_at.isoformat(),
        "raw": listing.raw,
    }


def parse_yen(value: str) -> Optional[int]:
    if not value:
        return None
    value = value.replace(",", "")
    match = YEN_PATTERN.search(value)
    if not match:
        digits = AREA_PATTERN.search(value)
        if digits:
            return int(float(digits.group(1)))
        return None
    number = float(match.group(1))
    unit = match.group(2)
    if unit in {"万円", "万"}:
        return int(number * 10000)
    return int(number)


def parse_area(value: str) -> Optional[float]:
    if not value:
        return None
    match = AREA_PATTERN.search(value)
    return float(match.group(1)) if match else None


def parse_station_walk(value: str) -> Dict[str, Optional[object]]:
    result: Dict[str, Optional[object]] = {"station": None, "walk_minutes": None}
    if not value:
        return result
    match = STATION_PATTERN.search(value)
    if match:
        result["station"] = match.group("station")
        result["walk_minutes"] = int(match.group("minutes"))
    return result


def parse_built_info(value: str) -> Dict[str, Optional[object]]:
    if not value:
        return {"built_at": None, "built_age_years": None}
    if "新築" in value:
        return {"built_at": None, "built_age_years": 0.0}
    date_match = DATE_PATTERN.search(value)
    if date_match:
        year, month = int(date_match.group(1)), int(date_match.group(2))
        return {"built_at": date(year, month, 1), "built_age_years": _age_from(year, month)}
    age_match = BUILT_AGE_PATTERN.search(value)
    if age_match:
        return {"built_at": None, "built_age_years": float(age_match.group(1))}
    return {"built_at": None, "built_age_years": None}


def _age_from(year: int, month: int) -> float:
    today = date.today()
    years = today.year - year
    month_diff = today.month - month
    return max(0.0, years + month_diff / 12)


def compute_age_difference(subject_built: Optional[date], built: Optional[date], built_age: Optional[float]) -> Optional[float]:
    if subject_built is None:
        return None
    if built:
        delta = (built.year - subject_built.year) + (built.month - subject_built.month) / 12
        return delta
    if built_age is not None:
        subject_age = _age_from(subject_built.year, subject_built.month)
        return subject_age - built_age
    return None


def normalize_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"true", "yes", "1", "required"}:
        return True
    if lowered in {"false", "no", "0", "forbidden"}:
        return False
    return None


def clamp_area(area: Optional[float], target: Optional[float], tolerance: float) -> bool:
    if area is None or target is None:
        return True
    return abs(area - target) <= tolerance


def clamp_minutes(minutes: Optional[int], target: Optional[int]) -> bool:
    if target is None or minutes is None:
        return True
    return minutes <= target


def filter_listings(listings: Iterable[RentalListing], query: SurveyQuery) -> List[RentalListing]:
    filtered: List[RentalListing] = []
    for listing in listings:
        if not clamp_area(listing.area, query.area, query.area_tolerance):
            continue
        if not clamp_minutes(listing.walk_minutes, query.minutes):
            continue
        if query.madori and listing.madori and query.madori not in listing.madori:
            continue
        if query.building_type and listing.building_type and query.building_type not in listing.building_type:
            continue
        if query.auto_lock == "required" and listing.auto_lock is False:
            continue
        if query.auto_lock == "forbidden" and listing.auto_lock is True:
            continue
        if query.bath_toilet == "required" and listing.bath_toilet_separate is False:
            continue
        if query.bath_toilet == "forbidden" and listing.bath_toilet_separate is True:
            continue
        if query.aspect not in (None, "any") and listing.aspect:
            if query.aspect not in listing.aspect.lower():
                continue
        filtered.append(listing)
    return filtered


def deduplicate(listings: Iterable[RentalListing]) -> List[RentalListing]:
    # TODO: Strengthen duplicate detection using fuzzy matching and property IDs.
    unique: Dict[str, RentalListing] = {}
    for listing in listings:
        key = "|".join(
            [
                listing.title.strip(),
                str(round(listing.area or 0.0, 1)),
                str(listing.rent or 0),
                str(listing.management_fee or 0),
                listing.station or "",
                str(listing.walk_minutes or 0),
            ]
        )
        if key in unique:
            unique[key].merge_source(listing.site)
            continue
        listing.sources = [listing.site]
        unique[key] = listing
    return list(unique.values())
