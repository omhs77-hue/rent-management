"""Pipeline to crawl YouTube channels via the official API."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List

import yaml

from src.config import get_settings
from src.crawlers.youtube_crawler import YouTubeCrawler

ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / "seeds" / "youtube_channels.yml"


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
    seeds = load_seeds()
    log_path = settings.data_root() / "logs" / "crawl-youtube.log"
    configure_logging(log_path)

    api_key = os.environ.get("YOUTUBE_API_KEY")
    crawler = YouTubeCrawler(api_key=api_key, settings=settings)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    raw_dir = settings.data_root() / "raw" / "youtube"
    raw_dir.mkdir(parents=True, exist_ok=True)

    for channel in seeds:
        output_path = raw_dir / f"{today}-{channel.get('name', channel['channel_id'])}.jsonl"
        crawler.crawl_channel(channel, output_path)

    crawler.close()


if __name__ == "__main__":
    main()
