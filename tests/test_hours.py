from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from scanner.hours import (
    is_post_close_window,
    is_regular_session,
    post_close_markets,
    session_complete,
    session_date_ceiling,
)

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


def test_post_close_window_is_1620_local_and_not_the_1600_close():
    assert not is_post_close_window(datetime(2026, 11, 27, 16, 0, tzinfo=NY), "US")
    assert not is_post_close_window(datetime(2026, 11, 27, 16, 19, tzinfo=NY), "US")
    assert is_post_close_window(datetime(2026, 11, 27, 16, 20, tzinfo=NY), "US")
    assert is_post_close_window(datetime(2026, 11, 27, 23, 59, tzinfo=NY), "US")
    assert not is_post_close_window(datetime(2026, 11, 28, 16, 20, tzinfo=NY), "US")
    assert not is_post_close_window(datetime(2026, 11, 27, 16, 19, tzinfo=HK), "HK")
    assert is_post_close_window(datetime(2026, 11, 27, 16, 20, tzinfo=HK), "HK")


def test_post_close_cron_slots_follow_us_dst_and_hong_kong_has_no_dst():
    # 16:20 HKT is 08:20 UTC in both seasons.
    assert is_post_close_window(datetime(2026, 7, 15, 8, 20, tzinfo=UTC), "HK")
    assert is_post_close_window(datetime(2026, 1, 15, 8, 20, tzinfo=UTC), "HK")
    assert not is_post_close_window(datetime(2026, 11, 27, 8, 19, tzinfo=UTC), "HK")
    # 20:20 UTC is 16:20 EDT and 15:20 EST. Only the summer slot finalizes.
    assert is_post_close_window(datetime(2026, 7, 15, 20, 20, tzinfo=UTC), "US")
    assert not is_post_close_window(datetime(2026, 1, 15, 20, 20, tzinfo=UTC), "US")
    assert is_regular_session(datetime(2026, 1, 15, 20, 20, tzinfo=UTC), "US")
    # 21:20 UTC is 16:20 EST and 17:20 EDT. Both are inside the US window:
    # winter is the 16:20 capture, summer is still the same local date after 16:20.
    assert is_post_close_window(datetime(2026, 1, 15, 21, 20, tzinfo=UTC), "US")
    assert is_post_close_window(datetime(2026, 7, 15, 21, 20, tzinfo=UTC), "US")
    assert not is_regular_session(datetime(2026, 7, 15, 21, 20, tzinfo=UTC), "US")


def test_one_markets_1620_does_not_put_the_other_market_in_the_window():
    hk_close = datetime(2026, 11, 27, 8, 20, tzinfo=UTC)  # 16:20 HKT, 03:20 EST
    assert post_close_markets(hk_close) == ["HK"]
    assert not is_regular_session(hk_close, "US")
    assert not is_post_close_window(hk_close, "US")
    us_close = datetime(2026, 11, 27, 21, 20, tzinfo=UTC)  # 16:20 EST, 05:20 next day HKT
    assert post_close_markets(us_close) == ["US"]
    assert not is_regular_session(us_close, "HK")
    assert not is_post_close_window(us_close, "HK")


def test_post_close_can_overlap_the_other_markets_regular_session():
    # Tuesday 09:30 HKT is still Monday 20:30 EST.
    hk_open = datetime(2026, 12, 1, 1, 30, tzinfo=UTC)
    assert is_regular_session(hk_open, "HK")
    assert is_post_close_window(hk_open, "US")
    assert post_close_markets(hk_open) == ["US"]
    # Friday 22:00 HKT during EDT is Friday 10:00 in New York.
    us_open = datetime(2026, 7, 17, 14, 0, tzinfo=UTC)
    assert is_post_close_window(us_open, "HK")
    assert is_regular_session(us_open, "US")
    assert not is_post_close_window(us_open, "US")
    assert post_close_markets(us_open) == ["HK"]


def test_session_date_ceiling_excludes_today_before_the_open():
    before_open = datetime(2026, 11, 27, 3, 20, tzinfo=NY)
    assert session_date_ceiling(before_open, "US") == date(2026, 11, 26)
    at_open = datetime(2026, 11, 27, 9, 30, tzinfo=NY)
    assert session_date_ceiling(at_open, "US") == date(2026, 11, 27)
    hk_close = datetime(2026, 11, 27, 16, 20, tzinfo=HK)
    assert session_date_ceiling(hk_close, "HK") == date(2026, 11, 27)
    assert session_date_ceiling(hk_close, "US") == date(2026, 11, 26)
