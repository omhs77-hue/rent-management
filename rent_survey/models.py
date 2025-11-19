"""Core dataclasses for rent survey listings and statistics."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any, Dict, List, Optional


@dataclass
class SurveyQuery:
    """Normalized representation of CLI arguments."""

    station: str
    minutes: Optional[int]
    area: Optional[float]
    area_tolerance: float
    madori: Optional[str]
    subject_built: Optional[date]
    age_max: Optional[int]
    age_diff: Optional[int]
    building_type: Optional[str]
    auto_lock: str
    bath_toilet: str
    aspect: Optional[str]
    max_listings: int
    sites: List[str]
    brand_new_separate_stats: bool


@dataclass
class RentalListing:
    """Normalized rental listing across sites."""

    title: str
    site: str
    url: str
    rent: Optional[int]
    management_fee: Optional[int]
    total_rent: Optional[int]
    deposit: Optional[int]
    key_money: Optional[int]
    area: Optional[float]
    madori: Optional[str]
    built_at: Optional[date]
    built_at_text: Optional[str]
    built_age_years: Optional[float]
    age_diff_from_subject: Optional[float]
    station: Optional[str]
    walk_minutes: Optional[int]
    building_type: Optional[str]
    auto_lock: Optional[bool]
    bath_toilet_separate: Optional[bool]
    aspect: Optional[str]
    collected_at: datetime
    raw: Dict[str, Any] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)

    def merge_source(self, other_site: str) -> None:
        if other_site not in self.sources:
            self.sources.append(other_site)


@dataclass
class SurveyResult:
    """Holds raw/filtered/deduplicated listings."""

    raw_listings: List[RentalListing]
    filtered_listings: List[RentalListing]
    deduplicated_listings: List[RentalListing]
    skipped_sites: Dict[str, str]


@dataclass
class NumericSummary:
    count: int
    average: Optional[float]
    median: Optional[float]
    minimum: Optional[float]
    maximum: Optional[float]


@dataclass
class GroupSummary:
    label: str
    summary: NumericSummary
