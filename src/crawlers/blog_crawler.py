"""Simple blog crawler that turns pages into JSONL documents."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.models import ContentDocument
from src.utils.http_client import HumanHttpClient
from src.utils.text_clean import clean_text

LOGGER = logging.getLogger(__name__)


class BlogCrawler:
    """Crawl configured blogs and output JSONL files."""

    def __init__(self, http_client: HumanHttpClient, settings) -> None:
        self.http_client = http_client
        self.settings = settings

    def crawl_site(self, site_config: Dict, output_path: Path) -> int:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        collected = 0
        today = datetime.utcnow().strftime("%Y-%m-%d")
        seen: set[str] = set()

        with output_path.open("a", encoding="utf-8") as fh:
            for url in site_config.get("start_urls", []):
                for article_url in self._discover_articles(url, site_config):
                    if article_url in seen:
                        continue
                    seen.add(article_url)
                    document = self._fetch_article(article_url, site_config, today, collected + 1)
                    if document is None:
                        continue
                    fh.write(document.to_json() + "\n")
                    collected += 1
        LOGGER.info("%s: collected %s articles", site_config.get("name"), collected)
        return collected

    def _discover_articles(self, listing_url: str, site_config: Dict) -> Iterable[str]:
        response = self.http_client.get(listing_url)
        if response is None or response.status_code >= 400:
            LOGGER.warning("Failed to fetch listing %s", listing_url)
            return []

        soup = BeautifulSoup(response.text, "lxml")
        selector = site_config.get("article_link_selector", "a")
        base_url = site_config.get("base_url", listing_url)
        links = []
        for link in soup.select(selector):
            href = link.get("href")
            if not href:
                continue
            links.append(urljoin(base_url, href))
        return links

    def _fetch_article(
        self,
        article_url: str,
        site_config: Dict,
        today: str,
        sequence: int,
    ) -> Optional[ContentDocument]:
        response = self.http_client.get(article_url)
        if response is None or response.status_code >= 400:
            LOGGER.warning("Failed to fetch article %s", article_url)
            return None

        soup = BeautifulSoup(response.text, "lxml")
        title = self._extract_text(soup, site_config.get("title_selector"))
        if not title and soup.title and soup.title.string:
            title = clean_text(soup.title.string)
        content = self._extract_content(soup, site_config.get("content_selector"))
        if not content:
            content = clean_text(soup.get_text(separator="\n"))
        if not content.strip():
            LOGGER.debug("Empty content for %s", article_url)
            return None

        published_at = self._extract_text(soup, site_config.get("date_selector"))
        author = self._extract_text(soup, site_config.get("author_selector"))
        doc_id = f"blog_{today}_{site_config.get('name', 'unknown')}_{sequence:04d}"

        return ContentDocument(
            id=doc_id,
            source="blog",
            url=article_url,
            title=title or article_url,
            author=author or None,
            published_at=published_at or None,
            fetched_at=ContentDocument.now_iso(),
            tags=site_config.get("tags", []),
            content=content,
        )

    @staticmethod
    def _extract_text(soup: BeautifulSoup, selector: Optional[str]) -> Optional[str]:
        if not selector:
            return None
        node = soup.select_one(selector)
        if not node:
            return None
        return clean_text(node.get_text(separator=" "))

    @staticmethod
    def _extract_content(soup: BeautifulSoup, selector: Optional[str]) -> str:
        if selector:
            node = soup.select_one(selector)
            if node:
                return clean_text(node.get_text(separator="\n"))
        # fallback to article body
        article = soup.find("article")
        if article:
            return clean_text(article.get_text(separator="\n"))
        return clean_text(soup.get_text(separator="\n"))
