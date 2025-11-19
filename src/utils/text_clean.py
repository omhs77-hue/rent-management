"""Utility helpers for text normalization."""
from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"\s+")


def clean_text(value: str) -> str:
    """Normalize whitespace and strip surrounding spaces."""

    value = _WHITESPACE_RE.sub(" ", value)
    return value.strip()
