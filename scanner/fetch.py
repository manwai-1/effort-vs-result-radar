"""Daily bars from a fixture file or from yfinance.

yfinance is imported only when a live download runs. Fixture runs and unit
tests do not import it. Downloads use auto_adjust=False and the unadjusted
Close column. Adj Close is ignored. The session date is the calendar date of
the bar timestamp in that timestamp's own timezone (Yahoo localizes daily bars
to the listing exchange). A naive timestamp uses its calendar date.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from scanner.models import Bar, ScanError


def parse_bar_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value)
    return date.fromisoformat(text[:10])


def bars_from_frame(frame: pd.DataFrame) -> list[Bar]:
    if frame is None or frame.empty:
        return []
    columns = {str(column).lower(): column for column in frame.columns}
    required = ("open", "high", "low", "close", "volume")
    if any(name not in columns for name in required):
        return []
    bars: list[Bar] = []
    for index, row in frame.iterrows():
        try:
            session = parse_bar_date(index)
            bar = Bar(
                date=session,
                open=float(row[columns["open"]]),
                high=float(row[columns["high"]]),
                low=float(row[columns["low"]]),
                close=float(row[columns["close"]]),
                volume=float(row[columns["volume"]]),
            )
        except (TypeError, ValueError):
            continue
        if bar.valid():
            bars.append(bar)
    dedup: dict[date, Bar] = {}
    for bar in bars:
        dedup[bar.date] = bar
    return [dedup[key] for key in sorted(dedup)]


def _ticker_frame(frame: pd.DataFrame, ticker: str) -> pd.DataFrame | None:
    if not isinstance(frame.columns, pd.MultiIndex):
        return frame
    level_0 = set(frame.columns.get_level_values(0))
    level_1 = set(frame.columns.get_level_values(1))
    if ticker in level_0:
        return frame[ticker]
    if ticker in level_1:
        return frame.xs(ticker, axis=1, level=1)
    return None


def yf_download(**kwargs: Any) -> Any:
    import yfinance as yf

    return yf.download(**kwargs)


def download_daily(tickers: list[str], start: date) -> dict[str, list[Bar]]:
    """Download daily bars. A missing ticker is omitted. An empty result is an error."""

    if not tickers:
        return {}
    collected: dict[str, list[Bar]] = {}
    errors: list[str] = []
    for offset in range(0, len(tickers), 40):
        chunk = tickers[offset : offset + 40]
        try:
            frame = yf_download(
                tickers=chunk if len(chunk) > 1 else chunk[0],
                start=start.isoformat(),
                interval="1d",
                auto_adjust=False,
                actions=False,
                progress=False,
                group_by="ticker",
                threads=True,
                timeout=30,
            )
        except Exception as exc:  # yfinance raises several vendor/network errors
            errors.append(str(exc))
            continue
        if frame is None or getattr(frame, "empty", True):
            errors.append(f"empty frame for {chunk[0]}..{chunk[-1]}")
            continue
        for ticker in chunk:
            sub = _ticker_frame(frame, ticker)
            if sub is None:
                continue
            bars = bars_from_frame(sub)
            if bars:
                collected[ticker] = bars
    if tickers and not collected:
        detail = "; ".join(errors) if errors else "no rows"
        raise ScanError(f"yfinance returned no usable bars ({detail})", 3)
    return collected


def load_fixture_bars(path: Path) -> dict[str, list[Bar]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ScanError(f"fixture bars not found: {path}", 2) from exc
    except json.JSONDecodeError as exc:
        raise ScanError(f"fixture bars are not valid JSON: {path}", 2) from exc
    series = document.get("series") if isinstance(document, dict) else None
    if not isinstance(series, dict):
        raise ScanError("fixture bars require a series object", 2)
    loaded: dict[str, list[Bar]] = {}
    for ticker, rows in series.items():
        if not isinstance(rows, list):
            raise ScanError(f"fixture series {ticker} must be an array", 2)
        bars: list[Bar] = []
        for row in rows:
            if not isinstance(row, dict):
                raise ScanError(f"fixture series {ticker} has a non-object bar", 2)
            try:
                bar = Bar(
                    date=date.fromisoformat(row["date"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ScanError(f"fixture series {ticker} has an invalid bar", 2) from exc
            if not bar.valid():
                raise ScanError(f"fixture series {ticker} has a bar that fails OHLC checks on {bar.date}", 2)
            bars.append(bar)
        dedup: dict[date, Bar] = {}
        for bar in bars:
            dedup[bar.date] = bar
        loaded[ticker] = [dedup[key] for key in sorted(dedup)]
    return loaded


class FixtureSource:
    def __init__(self, bars: dict[str, list[Bar]]) -> None:
        self._bars = bars

    def fetch(self, tickers: list[str], start: date) -> dict[str, list[Bar]]:
        result: dict[str, list[Bar]] = {}
        for ticker in tickers:
            rows = [bar for bar in self._bars.get(ticker, []) if bar.date >= start]
            if rows:
                result[ticker] = rows
        if tickers and not result:
            raise ScanError("fixture source had no bars for the requested tickers", 3)
        return result


class YFinanceSource:
    def fetch(self, tickers: list[str], start: date) -> dict[str, list[Bar]]:
        return download_daily(tickers, start)
