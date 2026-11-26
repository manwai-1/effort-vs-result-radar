from datetime import date, timedelta

from scanner.formulas import classify, measure, trend_20d, trend_from_return, wilder_atr
from scanner.models import (
    ANOMALY_DISPLACEMENT_MAX,
    ANOMALY_RVOL_MIN,
    ATR_PERIOD,
    DISPLACEMENT_FLOOR,
    RVOL_WINDOW,
    TREND_DEADBAND,
    Bar,
)
from scanner.numbers import round_dp
from tests.conftest import flat_bars


def test_contract_thresholds_are_the_documented_ones():
    assert RVOL_WINDOW == 20
    assert ATR_PERIOD == 14
    assert TREND_DEADBAND == 0.03
    assert ANOMALY_RVOL_MIN == 2.0
    assert ANOMALY_DISPLACEMENT_MAX == 0.5
    assert DISPLACEMENT_FLOOR == 0.1


def test_round_half_away_from_zero():
    assert round_dp(1.2345674, 6) == 1.234567
    assert round_dp(1.2345675, 6) == 1.234568
    assert round_dp(-1.2345675, 6) == -1.234568
    assert round_dp(0.0, 6) == 0.0


def test_wilder_atr_is_not_the_last_14_simple_average():
    bars = [Bar(date(2026, 1, 1), 100, 100, 100, 100, 1)]
    bars.append(Bar(date(2026, 1, 2), 100, 110, 100, 100, 1))
    for offset in range(2, 16):
        bars.append(Bar(date(2026, 1, 1) + timedelta(days=offset), 100, 101, 99, 100, 1))
    true_ranges = [10.0] + [2.0] * 14
    seed = sum(true_ranges[:14]) / 14
    expected = ((seed * 13) + 2.0) / 14
    assert wilder_atr(bars) == expected
    last_14_average = sum(true_ranges[-14:]) / 14
    assert last_14_average == 2.0
    assert wilder_atr(bars) != last_14_average


def test_flat_series_atr_is_the_true_range():
    bars = flat_bars(date(2026, 1, 1), 30)
    assert wilder_atr(bars) == 2.0


def test_trend_deadband_is_inclusive():
    assert trend_from_return(0.03) == "sideways"
    assert trend_from_return(-0.03) == "sideways"
    assert trend_from_return(0.0300001) == "up"
    assert trend_from_return(-0.0300001) == "down"
    assert trend_from_return(0.0) == "sideways"
    closes = [100.0] * 21
    assert trend_20d(closes) == "sideways"
    # Older than 20 sessions is ignored: the first close is 50, the close 20
    # sessions before the last is 100, and the last is 100.
    closes = [50.0] + [100.0] * 21
    assert trend_20d(closes) == "sideways"
    up = [100.0] * 20 + [110.0]
    down = [100.0] * 20 + [90.0]
    assert trend_20d(up) == "up"
    assert trend_20d(down) == "down"
    inside = [100.0] * 20 + [102.0]
    assert trend_20d(inside) == "sideways"


def test_measure_excludes_current_bar_and_uses_prior_close():
    bars = flat_bars(date(2026, 10, 1), 25, volume=5000)
    for bar_index in range(-21, -1):
        bars[bar_index] = Bar(
            date=bars[bar_index].date,
            open=100,
            high=101,
            low=99,
            close=100,
            volume=1000,
        )
    current = Bar(
        date=bars[-1].date,
        open=50,
        high=100.4,
        low=50,
        close=100.2,
        volume=2500,
    )
    # open 50 is inside the low, so the bar stays valid; displacement must
    # ignore it and use close minus the previous close.
    metrics = measure(current, bars[:-1])
    assert metrics is not None
    assert metrics["rvol"] == 2.5
    assert metrics["displacement"] == 0.1
    assert metrics["anomaly_score"] == 25.0
    assert metrics["is_anomaly"] is True
    assert metrics["trend_20d"] == "sideways"
    assert metrics["last_price"] == 100.2


def test_anomaly_boundaries_use_rounded_values():
    assert classify(2.0, 0.5) == (True, 4.0)
    assert classify(1.9999994, 0.5)[0] is False
    assert classify(2.0, 0.5000006)[0] is False
    flagged, score = classify(3.0, 0.05)
    assert flagged is True
    assert score == 30.0
    assert classify(2.0, 0.500001)[0] is False
