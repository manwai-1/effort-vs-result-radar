"""RVOL, displacement, anomaly score, and the 20-session trend.

Definitions (also stated in API_SPEC.md):

- The measurement session is the latest daily bar on or before the
  session-date ceiling. From the local 09:30 open onward, the ceiling is the
  market's local date. Before the open it is the previous calendar date, so
  a bar dated today is not used as a price for a session that has not
  started. While that session is still inside regular hours the bar may be
  partial (the current yfinance daily bar). From the post-close window the
  same date is the completed session: its close is the official close and
  its volume is the full-day volume. The bar is never copied forward to
  invent a missing day.
- Baseline sessions are the daily bars strictly before the measurement
  session. The measurement bar is excluded from the average volume, the ATR,
  and the trend.
- RVOL = measurement volume / arithmetic mean of the last 20 baseline volumes.
- price_change = measurement close − previous baseline close (a price, not a
  percent). Displacement = abs(price_change) / 14-day Wilder ATR of the
  baseline. True range uses the previous close. The seed ATR is the simple
  average of the first 14 true ranges; later true ranges use Wilder's
  smoothing: ATR_t = (ATR_(t-1) * 13 + TR_t) / 14.
- The rounded RVOL and displacement (6 decimal places, half away from zero)
  are the values written to JSON and the values the anomaly rule sees.
  Anomaly score = rounded RVOL / max(rounded displacement, 0.1), then rounded
  to 6 decimal places.
- is_anomaly when rounded RVOL >= 2.0 and rounded displacement <= 0.5.
- trend_20d compares the last baseline close with the close 20 sessions
  before it: return = close[-1] / close[-21] − 1.
  "up" when return > 0.03, "down" when return < −0.03, otherwise "sideways".
  A move of exactly 3% is sideways. The band is 3 percentage points.
"""

from __future__ import annotations

from scanner.models import (
    ANOMALY_DISPLACEMENT_MAX,
    ANOMALY_RVOL_MIN,
    ATR_PERIOD,
    DISPLACEMENT_FLOOR,
    MIN_BASELINE_BARS,
    RVOL_WINDOW,
    TREND_DEADBAND,
    TREND_SESSIONS,
    Bar,
)
from scanner.numbers import METRIC_DP, PRICE_DP, round_dp


def wilder_atr(baseline: list[Bar], period: int = ATR_PERIOD) -> float:
    """Wilder ATR over completed baseline bars only, oldest first."""

    if len(baseline) < period + 1:
        raise ValueError(f"ATR needs at least {period + 1} baseline bars")
    true_ranges: list[float] = []
    for index in range(1, len(baseline)):
        previous_close = baseline[index - 1].close
        high = baseline[index].high
        low = baseline[index].low
        true_range = max(
            high - low,
            abs(high - previous_close),
            abs(low - previous_close),
        )
        true_ranges.append(true_range)
    if len(true_ranges) < period:
        raise ValueError(f"ATR needs at least {period} true ranges")
    atr = sum(true_ranges[:period]) / period
    for true_range in true_ranges[period:]:
        atr = ((atr * (period - 1)) + true_range) / period
    return atr


def trend_from_return(return_fraction: float, deadband: float = TREND_DEADBAND) -> str:
    if return_fraction > deadband:
        return "up"
    if return_fraction < -deadband:
        return "down"
    return "sideways"


def trend_20d(baseline_closes: list[float], deadband: float = TREND_DEADBAND) -> str:
    """Classify the last `TREND_SESSIONS` baseline intervals.

    `baseline_closes` is oldest first and must contain at least 21 closes.
    """

    needed = TREND_SESSIONS + 1
    if len(baseline_closes) < needed:
        raise ValueError(f"trend needs at least {needed} baseline closes")
    latest = baseline_closes[-1]
    earlier = baseline_closes[-needed]
    if earlier <= 0 or latest <= 0:
        raise ValueError("trend closes must be positive")
    return trend_from_return((latest / earlier) - 1.0, deadband)


def classify(rvol: float, displacement: float) -> tuple[bool, float]:
    """Return (is_anomaly, anomaly_score) from raw ratios, after rounding."""

    rvol_rounded = round_dp(rvol, METRIC_DP)
    displacement_rounded = round_dp(displacement, METRIC_DP)
    score = round_dp(
        rvol_rounded / max(displacement_rounded, DISPLACEMENT_FLOOR),
        METRIC_DP,
    )
    is_anomaly = (
        rvol_rounded >= ANOMALY_RVOL_MIN
        and displacement_rounded <= ANOMALY_DISPLACEMENT_MAX
    )
    return is_anomaly, score


def measure(current: Bar, baseline: list[Bar]) -> dict[str, float | str | bool] | None:
    """Compute one point's metrics. Return None when the series cannot support them."""

    if len(baseline) < MIN_BASELINE_BARS:
        return None
    if not current.valid() or any(not bar.valid() for bar in baseline):
        return None
    window = baseline[-RVOL_WINDOW:]
    average_volume = sum(bar.volume for bar in window) / RVOL_WINDOW
    if average_volume <= 0:
        return None
    try:
        atr = wilder_atr(baseline)
    except ValueError:
        return None
    if atr <= 0:
        return None
    rvol = current.volume / average_volume
    price_change = current.close - baseline[-1].close
    displacement = abs(price_change) / atr
    try:
        is_anomaly, anomaly_score = classify(rvol, displacement)
        trend = trend_20d([bar.close for bar in baseline])
    except (ValueError, ZeroDivisionError):
        return None
    rvol_rounded = round_dp(rvol, METRIC_DP)
    displacement_rounded = round_dp(displacement, METRIC_DP)
    return {
        "rvol": rvol_rounded,
        "displacement": displacement_rounded,
        "anomaly_score": anomaly_score,
        "is_anomaly": is_anomaly,
        "trend_20d": trend,
        "last_price": round_dp(current.close, PRICE_DP),
    }
