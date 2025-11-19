"""CLI entrypoint for rent survey tool."""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import date, datetime, timezone
from typing import List, Optional

from .models import SurveyQuery
from .runner import SurveyRunner
from .stats import (
    brand_new_filtered,
    format_numeric_summary,
    group_by_age_difference,
    group_by_aspect,
    group_by_auto_lock,
    group_by_bath,
    summarize_area_rent,
    summarize_rent,
    summarize_total_rent,
)
from .utils import ensure_output_path, write_output

DEFAULT_SAFARI_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15"
)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect comparable rental listings from JP portals.")
    parser.add_argument("--station", required=True, help="Primary station name keyword.")
    parser.add_argument("--minutes", type=int, default=None, help="Maximum walking minutes from station.")
    parser.add_argument("--area", type=float, default=None, help="Target floor area in square meters.")
    parser.add_argument("--area-tolerance", type=float, default=10.0, help="± tolerance for area filtering.")
    parser.add_argument("--madori", default=None, help="Desired floor plan (e.g., 1K).")
    parser.add_argument("--subject-built", dest="subject_built", default=None, help="Subject property built YYYY-MM.")
    parser.add_argument("--age-max", type=int, default=None, help="Maximum building age to search on site.")
    parser.add_argument("--age-diff", type=int, default=None, help="Allowed difference in years for grouping.")
    parser.add_argument("--building-type", default=None, help="Building type keyword per site.")
    parser.add_argument(
        "--auto-lock",
        choices=["required", "forbidden", "any"],
        default="any",
        help="Auto-lock requirement",
    )
    parser.add_argument(
        "--bath-toilet",
        choices=["required", "forbidden", "any"],
        default="any",
        help="Bath/toilet separation requirement",
    )
    parser.add_argument("--aspect", default=None, help="Main aspect (e.g., south).")
    parser.add_argument("--max-listings", type=int, default=50, help="Per-site listing limit.")
    parser.add_argument(
        "--sites",
        default="homes,suumo",
        help="Comma separated site names (homes,suumo).",
    )
    parser.add_argument(
        "--output-format",
        choices=["csv", "jsonl"],
        default="csv",
        help="Output file format",
    )
    parser.add_argument("--output-path", default=None, help="Explicit output file path.")
    parser.add_argument("--user-agent", default=None, help="Override HTTP User-Agent string.")
    parser.add_argument("--request-interval", type=float, default=1.2, help="Seconds between requests.")
    parser.add_argument("--request-timeout", type=float, default=30.0, help="HTTP timeout seconds.")
    parser.add_argument(
        "--brand-new-separate-stats",
        action="store_true",
        help="Print additional stats excluding brand-new listings.",
    )
    return parser.parse_args(argv)


def parse_subject_built(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m").date()


def parse_sites(raw: str) -> List[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    subject_built = parse_subject_built(args.subject_built)
    sites = parse_sites(args.sites)
    user_agent = args.user_agent or os.environ.get("RENT_SURVEY_USER_AGENT") or DEFAULT_SAFARI_UA
    aspect = args.aspect.lower() if args.aspect else None
    query = SurveyQuery(
        station=args.station,
        minutes=args.minutes,
        area=args.area,
        area_tolerance=args.area_tolerance,
        madori=args.madori,
        subject_built=subject_built,
        age_max=args.age_max,
        age_diff=args.age_diff,
        building_type=args.building_type,
        auto_lock=args.auto_lock,
        bath_toilet=args.bath_toilet,
        aspect=aspect,
        max_listings=args.max_listings,
        sites=sites,
        brand_new_separate_stats=args.brand_new_separate_stats,
    )
    runner = SurveyRunner(query=query, user_agent=user_agent, min_interval=args.request_interval, request_timeout=args.request_timeout)
    result = runner.run()
    output_path = ensure_output_path(args.output_path, args.output_format)
    write_output(result.deduplicated_listings, output_path, args.output_format)
    print_summary(result, query, output_path)


def print_summary(result, query: SurveyQuery, output_path) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    print("=== Rent Survey Summary ===")
    print(f"Generated at: {timestamp}")
    print(f"Output file: {output_path}")
    if result.skipped_sites:
        print("Skipped sites:", json.dumps(result.skipped_sites, ensure_ascii=False))
    raw_counts = Counter([l.site for l in result.raw_listings])
    filtered_counts = Counter([l.site for l in result.filtered_listings])
    print("Site counts (raw):", dict(raw_counts))
    print("Site counts (filtered):", dict(filtered_counts))
    print(f"Raw listings: {len(result.raw_listings)}")
    print(f"Filtered listings: {len(result.filtered_listings)}")
    print(f"Deduplicated listings: {len(result.deduplicated_listings)}")
    total_summary = summarize_total_rent(result.deduplicated_listings)
    print(format_numeric_summary("Total rent", total_summary))
    rent_summary = summarize_rent(result.deduplicated_listings)
    print(format_numeric_summary("Rent", rent_summary))
    area_summary = summarize_area_rent(result.deduplicated_listings)
    print(format_numeric_summary("Rent per sqm", area_summary))
    if query.age_diff:
        for group in group_by_age_difference(result.deduplicated_listings, query.age_diff):
            print(format_numeric_summary(f"Age diff {group.label}", group.summary))
    for group in group_by_auto_lock(result.deduplicated_listings):
        print(format_numeric_summary(f"Auto lock {group.label}", group.summary))
    for group in group_by_bath(result.deduplicated_listings):
        print(format_numeric_summary(f"Bath {group.label}", group.summary))
    aspect_counts = group_by_aspect(result.deduplicated_listings)
    print("Aspect distribution:", aspect_counts)
    if query.brand_new_separate_stats:
        filtered = brand_new_filtered(result.deduplicated_listings)
        if filtered:
            print("-- Without brand-new units --")
            print(format_numeric_summary("Total rent", summarize_total_rent(filtered)))
            print(format_numeric_summary("Rent", summarize_rent(filtered)))


if __name__ == "__main__":  # pragma: no cover
    main()
