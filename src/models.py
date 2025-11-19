"""Shared data models used across crawlers."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ContentDocument:
    """Dataclass representing the JSONL schema for crawled content."""

    id: str
    source: str
    url: str
    title: str
    author: Optional[str]
    published_at: Optional[str]
    fetched_at: str
    tags: List[str] = field(default_factory=list)
    content: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @staticmethod
    def now_iso() -> str:
        return datetime.utcnow().isoformat()
