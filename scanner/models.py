"""Bars and the thresholds shared by the scanner."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

RVOL_WINDOW = 20
ATR_PERIOD = 14
TREND_SESSIONS = 20
TREND_DEADBAND = 0.03
ANOMALY_RVOL_MIN = 2.0
ANOMALY_DISPLACEMENT_MAX = 0.5
DISPLACEMENT_FLOOR = 0.1
MIN_BASELINE_BARS = TREND_SESSIONS + 1  # 21 closes: the latest and the one 20 sessions earlier

RETURN_FIELDS = (
    "t_plus_3_return_pct",
    "t_plus_5_return_pct",
    "t_plus_10_return_pct",
)
HORIZONS = (3, 5, 10)

MARKETS = ("US", "HK")
CURRENCIES = {"US": "USD", "HK": "HKD"}


@dataclass(frozen=True)
class Bar:
    """One daily session. `date` is that market's session date."""

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float

    def valid(self) -> bool:
        values = (self.open, self.high, self.low, self.close, self.volume)
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
            return False
        if not all(math.isfinite(float(v)) for v in values):
            return False
        if self.high < self.low:
            return False
        if self.close <= 0 or self.open <= 0:
            return False
        if self.volume < 0:
            return False
        if self.close > self.high or self.close < self.low:
            return False
        return True


class ScanError(Exception):
    def __init__(self, message: str, code: int) -> None:
        super().__init__(message)
        self.code = code
