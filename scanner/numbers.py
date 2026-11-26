"""Rounding used at the JSON boundary.

Metrics are rounded with half-away-from-zero (Decimal ROUND_HALF_UP) so a
repeated scan of the same bars emits the same JSON numbers.
"""

from __future__ import annotations

import math
from decimal import Decimal, ROUND_HALF_UP

METRIC_DP = 6
RETURN_DP = 4
PRICE_DP = 4
HIT_RATE_DP = 4


def round_dp(value: float, places: int) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"expected a real number, got {type(value).__name__}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("cannot round a non-finite number")
    quant = Decimal(10) ** -places
    # str() is the shortest round-trip, so quantize sees the decimal the float
    # represents rather than a 6-place format that would round first.
    decimal_value = Decimal(str(number))
    rounded = float(decimal_value.quantize(quant, rounding=ROUND_HALF_UP))
    if rounded == 0:
        return 0.0
    return rounded
