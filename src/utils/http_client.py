"""HTTP client utilities with human-like waits and robots.txt handling."""
from __future__ import annotations

import logging
import random
import time
from typing import Dict, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx


LOGGER = logging.getLogger(__name__)


def human_like_wait(char_count: int, domain_factor: float = 1.0) -> None:
    """Sleep for a short time based on response size to mimic human pacing."""

    if char_count < 1000:
        base = 0.5
    elif char_count < 3000:
        base = 1.0
    elif char_count < 7000:
        base = 1.5
    else:
        base = 2.5

    jitter = random.uniform(0, 0.7)
    time.sleep((base + jitter) * domain_factor)


class HumanHttpClient:
    """Thin wrapper around httpx.Client that respects robots.txt and waits."""

    def __init__(
        self,
        user_agent: str,
        domain_factors: Optional[Dict[str, Dict[str, float]]] = None,
        timeout: int = 30,
    ) -> None:
        headers = {"User-Agent": user_agent}
        self._client = httpx.Client(headers=headers, timeout=timeout)
        self.user_agent = user_agent
        self.domain_factors = domain_factors or {}
        self._robot_parsers: Dict[str, RobotFileParser] = {}

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HumanHttpClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        self.close()

    def _domain_factor(self, domain: str) -> float:
        if domain in self.domain_factors:
            return float(self.domain_factors[domain].get("factor", 1.0))
        default = self.domain_factors.get("default", {})
        return float(default.get("factor", 1.0))

    def _get_robot_parser(self, url: str) -> RobotFileParser:
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain in self._robot_parsers:
            return self._robot_parsers[domain]

        robots_url = f"{parsed.scheme}://{domain}/robots.txt"
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            parser.read()
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.warning("Failed to read robots.txt for %s: %s", domain, exc)
        self._robot_parsers[domain] = parser
        return parser

    def _is_allowed(self, url: str) -> bool:
        parser = self._get_robot_parser(url)
        allowed = parser.can_fetch(self.user_agent, url)
        return allowed if allowed is not None else True

    def get(self, url: str, **kwargs) -> Optional[httpx.Response]:
        domain = urlparse(url).netloc
        if not self._is_allowed(url):
            LOGGER.info("Blocked by robots.txt: %s", url)
            return None

        response = self._client.get(url, **kwargs)
        human_like_wait(len(response.text), self._domain_factor(domain))
        return response
