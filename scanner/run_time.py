"""Timestamp formatting for JSON files."""

from __future__ import annotations

from datetime import datetime


def isoformat_offset(now: datetime) -> str:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timestamps must include a timezone offset")
    return now.isoformat(timespec="seconds")
