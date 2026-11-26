"""Regular-session clock for US and Hong Kong.

The clock uses America/New_York and Asia/Hong_Kong. It does not assume a fixed
UTC offset, so US daylight-saving time is handled by the zone database.

A market is in its regular session on a local weekday when the local time is
at or after 09:30 and strictly before 16:00. The 16:00 minute is the close, so
it is outside the session.

Hong Kong's lunch break (12:00–13:00) is inside that window on purpose. Lunch
prints are the last traded morning prices from the data vendor, not invented
prices. One clock rule covers the whole 09:30–16:00 local weekday, and the
scheduled workflow therefore still fires during lunch.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

US_ZONE = ZoneInfo("America/New_York")
HK_ZONE = ZoneInfo("Asia/Hong_Kong")
ZONES = {"US": US_ZONE, "HK": HK_ZONE}

SESSION_OPEN_MINUTES = 9 * 60 + 30
SESSION_CLOSE_MINUTES = 16 * 60


def require_aware(now: datetime) -> datetime:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timestamps must include a timezone offset")
    return now


def market_local(now: datetime, market: str) -> datetime:
    return require_aware(now).astimezone(ZONES[market])


def is_regular_session(now: datetime, market: str) -> bool:
    local = market_local(now, market)
    if local.weekday() >= 5:
        return False
    minutes = local.hour * 60 + local.minute
    return SESSION_OPEN_MINUTES <= minutes < SESSION_CLOSE_MINUTES


def session_complete(now: datetime, market: str) -> bool:
    """True once the local clock is at or past 16:00.

    Weekend and holiday dates are completed because their session date is
    before the market's current local date; callers apply that date test.
    This function only answers the clock for the local calendar day.
    """

    local = market_local(now, market)
    minutes = local.hour * 60 + local.minute
    return minutes >= SESSION_CLOSE_MINUTES


def open_markets(now: datetime) -> list[str]:
    return [market for market in ("US", "HK") if is_regular_session(now, market)]
