"""Shared synthetic bars. These are not market prices."""

from __future__ import annotations

from datetime import date, timedelta

from scanner.models import Bar


def date_range(start: date, count: int) -> list[date]:
    return [start + timedelta(days=offset) for offset in range(count)]


def flat_bars(
    start: date,
    count: int,
    *,
    close: float = 100.0,
    volume: float = 1000.0,
    high_offset: float = 1.0,
    low_offset: float = 1.0,
) -> list[Bar]:
    bars: list[Bar] = []
    for session in date_range(start, count):
        bars.append(
            Bar(
                date=session,
                open=close,
                high=close + high_offset,
                low=close - low_offset,
                close=close,
                volume=volume,
            )
        )
    return bars
