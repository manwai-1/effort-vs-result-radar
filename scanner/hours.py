"""Regular-session clock for US and Hong Kong.

The clock uses America/New_York and Asia/Hong_Kong. It does not assume a fixed
UTC offset, so US daylight-saving time is handled by the zone database.
Hong Kong has no daylight-saving time.

A market is in its regular session on a local weekday when the local time is
at or after 09:30 and strictly before 16:00. The 16:00 minute is the close, so
it is outside the session.

Hong Kong's lunch break (12:00–13:00) is inside that window on purpose. Lunch
prints are the last traded morning prices from the data vendor, not invented
prices. One clock rule covers the whole 09:30–16:00 local weekday, and the
scheduled workflow therefore still fires during lunch.

The post-close window starts at 16:20 local on that same weekday and lasts
until the local date changes. That is when a scheduled run finalizes the
session that just completed (official close and full-day volume). 16:00 is
already complete for T+N backfill, but it is not this window. Each market is
judged on its own clock.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

US_ZONE = ZoneInfo("America/New_York")
HK_ZONE = ZoneInfo("Asia/Hong_Kong")
ZONES = {"US": US_ZONE, "HK": HK_ZONE}

SESSION_OPEN_MINUTES = 9 * 60 + 30
SESSION_CLOSE_MINUTES = 16 * 60
POST_CLOSE_START_MINUTES = 16 * 60 + 20


def require_aware(now: datetime) -> datetime:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timestamps must include a timezone offset")
    return now


def market_local(now: datetime, market: str) -> datetime:
    return require_aware(now).astimezone(ZONES[market])


def _minutes(local: datetime) -> int:
    return local.hour * 60 + local.minute


def is_regular_session(now: datetime, market: str) -> bool:
    local = market_local(now, market)
    if local.weekday() >= 5:
        return False
    minutes = _minutes(local)
    return SESSION_OPEN_MINUTES <= minutes < SESSION_CLOSE_MINUTES


def session_complete(now: datetime, market: str) -> bool:
    """True once the local clock is at or past 16:00.

    Weekend and holiday dates are completed because their session date is
    before the market's current local date; callers apply that date test.
    This function only answers the clock for the local calendar day.
    """

    local = market_local(now, market)
    return _minutes(local) >= SESSION_CLOSE_MINUTES


def is_post_close_window(now: datetime, market: str) -> bool:
    """True when this market's just-completed session should be finalized.

    Local weekday, at or after 16:20, until the local date changes. The
    16:00 close is complete for T+N but is outside this window, so a
    scheduled 16:00 slot does not rewrite radar.json. A UTC cron that is
    16:20 only in the other daylight-saving season is decided here, not by
    the cron label. 16:20 Asia/Hong_Kong is 08:20 UTC. 16:20
    America/New_York is 20:20 UTC during EDT and 21:20 UTC during EST.
    """

    local = market_local(now, market)
    if local.weekday() >= 5:
        return False
    return _minutes(local) >= POST_CLOSE_START_MINUTES


def session_date_ceiling(now: datetime, market: str) -> date:
    """Latest session date that may be measured at `now`.

    Before the local open, today's session has not started. A bar dated
    today is not a price for that market. From 09:30 onward the ceiling is
    the local calendar date, including the post-close window.
    """

    local = market_local(now, market)
    if local.weekday() < 5 and _minutes(local) < SESSION_OPEN_MINUTES:
        return local.date() - timedelta(days=1)
    return local.date()


def session_date_is_complete(now: datetime, market: str, session: date) -> bool:
    """True when `session` can no longer be a partial bar at `now`."""

    local_date = market_local(now, market).date()
    if session < local_date:
        return True
    if session > local_date:
        return False
    return session_complete(now, market)


def open_markets(now: datetime) -> list[str]:
    return [market for market in ("US", "HK") if is_regular_session(now, market)]


def post_close_markets(now: datetime) -> list[str]:
    return [market for market in ("US", "HK") if is_post_close_window(now, market)]
