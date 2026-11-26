from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from scanner.hours import is_regular_session, session_complete

NY = ZoneInfo("America/New_York")
HK = ZoneInfo("Asia/Hong_Kong")
UTC = timezone.utc


def test_us_dst_is_not_a_fixed_utc_offset():
    summer_open = datetime(2026, 7, 15, 9, 30, tzinfo=NY)
    winter_open = datetime(2026, 1, 15, 9, 30, tzinfo=NY)
    assert summer_open.utcoffset().total_seconds() == -4 * 3600
    assert winter_open.utcoffset().total_seconds() == -5 * 3600
    assert is_regular_session(datetime(2026, 7, 15, 13, 30, tzinfo=UTC), "US")
    assert not is_regular_session(datetime(2026, 7, 15, 13, 29, tzinfo=UTC), "US")
    assert not is_regular_session(datetime(2026, 1, 15, 13, 30, tzinfo=UTC), "US")
    assert is_regular_session(datetime(2026, 1, 15, 14, 30, tzinfo=UTC), "US")
    assert is_regular_session(datetime(2026, 1, 15, 20, 30, tzinfo=UTC), "US")
    assert not is_regular_session(datetime(2026, 1, 15, 21, 0, tzinfo=UTC), "US")
    assert not is_regular_session(datetime(2026, 7, 15, 20, 0, tzinfo=UTC), "US")


def test_hong_kong_has_no_dst_and_lunch_is_inside_the_window():
    summer = datetime(2026, 7, 15, 12, 30, tzinfo=HK)
    winter = datetime(2026, 1, 15, 12, 30, tzinfo=HK)
    assert summer.utcoffset().total_seconds() == 8 * 3600
    assert winter.utcoffset().total_seconds() == 8 * 3600
    assert is_regular_session(datetime(2026, 11, 27, 1, 30, tzinfo=UTC), "HK")
    assert not is_regular_session(datetime(2026, 11, 27, 1, 29, tzinfo=UTC), "HK")
    assert is_regular_session(datetime(2026, 11, 27, 4, 30, tzinfo=UTC), "HK")
    assert is_regular_session(datetime(2026, 11, 27, 7, 59, tzinfo=UTC), "HK")
    assert not is_regular_session(datetime(2026, 11, 27, 8, 0, tzinfo=UTC), "HK")


def test_weekends_use_the_market_local_weekday():
    assert not is_regular_session(datetime(2026, 11, 28, 10, 0, tzinfo=HK), "HK")
    assert not is_regular_session(datetime(2026, 11, 28, 12, 0, tzinfo=NY), "US")
    # Monday 09:30 HKT is still Sunday evening in New York.
    monday_hk_open = datetime(2026, 11, 30, 1, 30, tzinfo=UTC)
    assert is_regular_session(monday_hk_open, "HK")
    assert not is_regular_session(monday_hk_open, "US")


def test_session_complete_starts_at_the_close():
    assert not session_complete(datetime(2026, 11, 27, 15, 59, tzinfo=NY), "US")
    assert session_complete(datetime(2026, 11, 27, 16, 0, tzinfo=NY), "US")
    assert not session_complete(datetime(2026, 11, 27, 15, 59, tzinfo=HK), "HK")
    assert session_complete(datetime(2026, 11, 27, 16, 0, tzinfo=HK), "HK")
