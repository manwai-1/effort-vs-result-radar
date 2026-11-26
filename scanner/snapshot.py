"""Turn bars into a radar snapshot and ledger anomalies."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from scanner.formulas import measure
from scanner.hours import session_date_ceiling
from scanner.models import CURRENCIES, MIN_BASELINE_BARS, Bar
from scanner.run_time import isoformat_offset
from scanner.tags import assign_tag


def select_measurement(bars: list[Bar], today: Any) -> tuple[Bar, list[Bar]] | None:
    eligible = [bar for bar in bars if bar.date <= today and bar.valid()]
    dedup: dict[Any, Bar] = {}
    for bar in eligible:
        dedup[bar.date] = bar
    ordered = [dedup[key] for key in sorted(dedup)]
    if len(ordered) < MIN_BASELINE_BARS + 1:
        return None
    return ordered[-1], ordered[:-1]


def build_points(
    symbols: list[dict[str, Any]],
    bars_by_ticker: dict[str, list[Bar]],
    now: datetime,
) -> tuple[list[dict[str, Any]], list[str]]:
    points: list[dict[str, Any]] = []
    skipped: list[str] = []
    for symbol in symbols:
        ticker = symbol["ticker"]
        market = symbol["market"]
        bars = bars_by_ticker.get(ticker)
        if not bars:
            skipped.append(f"{ticker}: no bars")
            continue
        today = session_date_ceiling(now, market)
        selected = select_measurement(bars, today)
        if selected is None:
            skipped.append(f"{ticker}: fewer than {MIN_BASELINE_BARS + 1} sessions on or before {today}")
            continue
        current, baseline = selected
        metrics = measure(current, baseline)
        if metrics is None:
            skipped.append(f"{ticker}: metrics undefined (volume, ATR, or closes)")
            continue
        point = {
            "ticker": ticker,
            "market": market,
            "rvol": metrics["rvol"],
            "displacement": metrics["displacement"],
            "anomaly_score": metrics["anomaly_score"],
            "is_anomaly": metrics["is_anomaly"],
            "trend_20d": metrics["trend_20d"],
            **assign_tag(bool(metrics["is_anomaly"]), str(metrics["trend_20d"])),
            "last_price": metrics["last_price"],
            "currency": CURRENCIES[market],
        }
        points.append(point)
    points.sort(key=lambda point: (0 if point["market"] == "US" else 1, point["ticker"]))
    return points, skipped


def build_radar(points: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    return {
        "generated_at": isoformat_offset(now),
        "universe": {
            "us_count": sum(1 for point in points if point["market"] == "US"),
            "hk_count": sum(1 for point in points if point["market"] == "HK"),
        },
        "points": points,
    }


def anomalies_from_points(points: list[dict[str, Any]], measurement_dates: dict[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for point in points:
        if not point["is_anomaly"]:
            continue
        rows.append(
            {
                "date": measurement_dates[point["ticker"]],
                "ticker": point["ticker"],
                "market": point["market"],
                "signal_price": point["last_price"],
                "currency": point["currency"],
                "rvol": point["rvol"],
                "displacement": point["displacement"],
                "anomaly_score": point["anomaly_score"],
                "bargaining_power": point["bargaining_power"],
                "bargaining_power_label_en": point["bargaining_power_label_en"],
                "bargaining_power_label_zh": point["bargaining_power_label_zh"],
            }
        )
    return rows


def measurement_dates(
    symbols: list[dict[str, Any]],
    bars_by_ticker: dict[str, list[Bar]],
    now: datetime,
) -> dict[str, str]:
    dates: dict[str, str] = {}
    for symbol in symbols:
        bars = bars_by_ticker.get(symbol["ticker"])
        if not bars:
            continue
        selected = select_measurement(bars, session_date_ceiling(now, symbol["market"]))
        if selected is None:
            continue
        dates[symbol["ticker"]] = selected[0].date.isoformat()
    return dates
