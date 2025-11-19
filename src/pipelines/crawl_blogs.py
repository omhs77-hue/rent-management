"""Pipeline for crawling configured blogs into JSONL."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import List

import yaml

from src.config import ensure_data_directories, get_settings
from src.crawlers.blog_crawler import BlogCrawler
from src.utils.http_client import HumanHttpClient

ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / "seeds" / "blogs.yml"


def load_seeds() -> List[dict]:
    if not SEED_PATH.exists():
        raise FileNotFoundError(f"Seed file not found: {SEED_PATH}")
    with SEED_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def configure_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def main() -> None:
    settings = get_settings()
    ensure_data_directories(settings)
    seeds = load_seeds()
    log_path = settings.data_root() / "logs" / "crawl-blogs.log"
    configure_logging(log_path)

    http_settings = settings.http
    http_client = HumanHttpClient(
        user_agent=http_settings.get("user_agent", "Mozilla/5.0"),
        domain_factors=settings.domains,
        timeout=settings.http_client.get("timeout", 30),
    )
    crawler = BlogCrawler(http_client, settings)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    raw_dir = settings.data_root() / "raw" / "blogs"

    for site in seeds:
        output_path = raw_dir / f"{today}-{site.get('name', 'unknown')}.jsonl"
        crawler.crawl_site(site, output_path)

    http_client.close()


if __name__ == "__main__":
    main()
