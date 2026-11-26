from datetime import date

import pandas as pd

from scanner.fetch import _ticker_frame, bars_from_frame


def test_daily_session_date_is_the_exchange_wall_date_and_close_is_unadjusted():
    index = pd.to_datetime(["2026-11-27 00:00"]).tz_localize("Asia/Hong_Kong")
    frame = pd.DataFrame(
        {
            "Open": [10.0],
            "High": [11.0],
            "Low": [9.0],
            "Close": [10.5],
            "Adj Close": [1.0],
            "Volume": [100.0],
        },
        index=index,
    )
    bars = bars_from_frame(frame)
    assert len(bars) == 1
    assert bars[0].date == date(2026, 11, 27)
    assert bars[0].close == 10.5

    us_index = pd.to_datetime(["2026-01-15 00:00"]).tz_localize("America/New_York")
    us_frame = frame.copy()
    us_frame.index = us_index
    assert bars_from_frame(us_frame)[0].date == date(2026, 1, 15)


def test_ticker_level_of_a_grouped_download():
    index = pd.to_datetime(["2026-11-21"])
    columns = pd.MultiIndex.from_product(
        [["FIXU"], ["Open", "High", "Low", "Close", "Adj Close", "Volume"]]
    )
    frame = pd.DataFrame([[10.0, 11.0, 9.0, 10.5, 1.0, 100.0]], index=index, columns=columns)
    bars = bars_from_frame(_ticker_frame(frame, "FIXU"))
    assert bars[0].date == date(2026, 11, 21)
    assert bars[0].close == 10.5


def test_invalid_bars_are_dropped():
    index = pd.to_datetime(["2026-11-20", "2026-11-21"])
    frame = pd.DataFrame(
        {
            "Open": [10.0, 10.0],
            "High": [9.0, 12.0],
            "Low": [11.0, 9.0],
            "Close": [10.0, 11.0],
            "Volume": [100.0, 100.0],
        },
        index=index,
    )
    bars = bars_from_frame(frame)
    assert [bar.date for bar in bars] == [date(2026, 11, 21)]
