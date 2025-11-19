"""Aggregation helpers for rent survey."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from statistics import mean, median
from typing import Dict, Iterable, List, Optional

from .models import GroupSummary, NumericSummary, RentalListing


def _safe_mean(values: List[float]) -> Optional[float]:
    return mean(values) if values else None


def _safe_median(values: List[float]) -> Optional[float]:
    return median(values) if values else None


def summarize_numeric(values: Iterable[float]) -> NumericSummary:
    data = list(values)
    return NumericSummary(
        count=len(data),
        average=_safe_mean(data),
        median=_safe_median(data),
        minimum=min(data) if data else None,
        maximum=max(data) if data else None,
    )


def summarize_total_rent(listings: List[RentalListing]) -> NumericSummary:
    totals = [l.total_rent for l in listings if l.total_rent is not None]
    return summarize_numeric(totals)


def summarize_rent(listings: List[RentalListing]) -> NumericSummary:
    rents = [l.rent for l in listings if l.rent is not None]
    return summarize_numeric(rents)


def summarize_area_rent(listings: List[RentalListing]) -> NumericSummary:
    unit = [l.total_rent / l.area for l in listings if l.total_rent and l.area]
    return summarize_numeric(unit)


def group_by_auto_lock(listings: List[RentalListing]) -> List[GroupSummary]:
    groups: Dict[str, List[RentalListing]] = defaultdict(list)
    for listing in listings:
        key = "auto_lock" if listing.auto_lock else "no_auto_lock" if listing.auto_lock is False else "unknown"
        groups[key].append(listing)
    return [GroupSummary(label=k, summary=summarize_total_rent(v)) for k, v in groups.items()]


def group_by_bath(listings: List[RentalListing]) -> List[GroupSummary]:
    groups: Dict[str, List[RentalListing]] = defaultdict(list)
    for listing in listings:
        key = "bath_toilet_separate" if listing.bath_toilet_separate else "unit_bath" if listing.bath_toilet_separate is False else "unknown"
        groups[key].append(listing)
    return [GroupSummary(label=k, summary=summarize_total_rent(v)) for k, v in groups.items()]


def group_by_aspect(listings: List[RentalListing]) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for listing in listings:
        label = listing.aspect or "unknown"
        counts[label] += 1
    return dict(counts)


def group_by_age_difference(listings: List[RentalListing], age_diff: Optional[int]) -> List[GroupSummary]:
    if age_diff is None:
        return []
    within: List[RentalListing] = []
    outside: List[RentalListing] = []
    for listing in listings:
        diff = listing.age_diff_from_subject
        if diff is None:
            continue
        (within if abs(diff) <= age_diff else outside).append(listing)
    return [
        GroupSummary(label=f"within_±{age_diff}", summary=summarize_total_rent(within)),
        GroupSummary(label=f"outside_±{age_diff}", summary=summarize_total_rent(outside)),
    ]


def brand_new_filtered(listings: List[RentalListing]) -> List[RentalListing]:
    return [l for l in listings if not (l.built_age_years is not None and l.built_age_years < 1)]


def format_numeric_summary(label: str, summary: NumericSummary) -> str:
    data = asdict(summary)
    parts = [f"{k}={v}" for k, v in data.items()]
    return f"{label}: " + ", ".join(parts)
