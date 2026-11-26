"""Anomaly ledger, T+N backfill, and summary_by_tag.

Dedup key is (session date, ticker).

While a market's session is still open, the first flag of that session is
kept. A later intraday scan does not overwrite signal price, RVOL,
displacement, score, or tag, and it does not delete the row if the name
stops looking like an anomaly.

The post-close run of that market replaces those same-day fields with the
completed session. signal_price becomes the official close and RVOL uses
the full-day volume. The tag is replaced with the completed session's tag.
A filled T+N return is not cleared or revised. If the completed session is
not an anomaly, the same-day partial row is removed so it cannot lock a
flag. Rows from other dates are not rewritten. Only a still-null T+N return
is filled, and a filled return is not revised.

T+N is N sessions present in that ticker's daily bars after the signal
session, not N calendar days. A weekend or a missing session is not invented.
The return is filled only when the target session's bar is completed:
its date is before the market's local date, or it is the local date and the
local clock is at or past 16:00.

return_pct = (completed close at T+N / signal_price − 1) × 100
1.25 means +1.25 percentage points. Both prices are rounded to 4 decimal
places before the division, and the result is rounded to 4 decimal places.

Hit rates (summary_by_tag), using only non-null returns for that horizon:
- buyer_absorption: a hit is a return strictly greater than 0
- seller_distribution: a hit is a return strictly less than 0
- a return of exactly 0 is in the sample and is not a hit
- stalemate_compression has no directional rule; hit_rate_pct is null and
  hit_rate_label is 不適用
- a horizon with no non-null returns has a null average and, when the tag
  has a directional rule, a null hit rate (not a numeric 0)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from scanner.hours import market_local, session_complete
from scanner.models import HORIZONS, RETURN_FIELDS, Bar
from scanner.numbers import HIT_RATE_DP, PRICE_DP, RETURN_DP, round_dp
from scanner.run_time import isoformat_offset
from scanner.tags import LABELS, STALEMATE_HIT_RATE_LABEL, TAG_ORDER


def empty_history() -> dict[str, Any]:
    return {"records": []}


def _horizon_block(tag: str, returns: list[float]) -> dict[str, Any]:
    applicable = tag != "stalemate_compression"
    block: dict[str, Any] = {
        "sample_count": len(returns),
        "average_return_pct": None,
        "hit_rate_pct": None,
        "hit_rate_applicable": applicable,
        "hit_rate_label": None if applicable else STALEMATE_HIT_RATE_LABEL,
    }
    if not returns:
        return block
    average = sum(returns) / len(returns)
    block["average_return_pct"] = round_dp(average, RETURN_DP)
    if not applicable:
        return block
    if tag == "buyer_absorption":
        hits = sum(1 for value in returns if value > 0)
    elif tag == "seller_distribution":
        hits = sum(1 for value in returns if value < 0)
    else:
        raise ValueError(f"unknown tag {tag}")
    block["hit_rate_pct"] = round_dp((hits / len(returns)) * 100.0, HIT_RATE_DP)
    return block


def summarize(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Unfiltered per-tag cards. Always three entries, in contract order."""

    summary: list[dict[str, Any]] = []
    for tag in TAG_ORDER:
        english, chinese = LABELS[tag]
        rows = [row for row in records if row.get("bargaining_power") == tag]
        entry: dict[str, Any] = {
            "bargaining_power": tag,
            "bargaining_power_label_en": english,
            "bargaining_power_label_zh": chinese,
            "sample_count": len(rows),
        }
        for horizon in HORIZONS:
            field = f"t_plus_{horizon}_return_pct"
            values = [row[field] for row in rows if row.get(field) is not None]
            entry[f"t_plus_{horizon}"] = _horizon_block(tag, values)
        summary.append(entry)
    return summary


def history_fetch_start(records: list[dict[str, Any]], today: date) -> date:
    """How far back a download must reach.

    420 calendar days covers the 21-session baseline and a year of T+N.
    Signals that still have a null return pull the start earlier so an older
    row can still be filled. Rows whose three returns are already set do not
    extend the download.
    """

    start = today - timedelta(days=420)
    pending_dates: list[date] = []
    for record in records:
        if any(record.get(field) is None for field in RETURN_FIELDS):
            pending_dates.append(date.fromisoformat(record["date"]))
    if pending_dates:
        earliest = min(pending_dates) - timedelta(days=5)
        if earliest < start:
            start = earliest
    return start


def _completed_closes(bars: list[Bar], market: str, now: datetime) -> dict[date, float]:
    today = market_local(now, market).date()
    closed_today = session_complete(now, market)
    closes: dict[date, float] = {}
    for bar in bars:
        if bar.date < today or (bar.date == today and closed_today):
            closes[bar.date] = bar.close
    return closes


def backfill_record(record: dict[str, Any], bars: list[Bar], now: datetime) -> bool:
    """Fill null T+N fields. Return True when a value changes."""

    if not bars:
        return False
    market = record["market"]
    signal_date = date.fromisoformat(record["date"])
    session_dates = sorted({bar.date for bar in bars if bar.date <= market_local(now, market).date()})
    if signal_date not in session_dates:
        return False
    index = session_dates.index(signal_date)
    completed = _completed_closes(bars, market, now)
    changed = False
    signal_price = record["signal_price"]
    if not isinstance(signal_price, (int, float)) or isinstance(signal_price, bool) or signal_price == 0:
        return False
    for horizon in HORIZONS:
        field = f"t_plus_{horizon}_return_pct"
        if record.get(field) is not None:
            continue
        target_index = index + horizon
        if target_index >= len(session_dates):
            continue
        target = session_dates[target_index]
        if target not in completed:
            continue
        future_close = round_dp(completed[target], PRICE_DP)
        stored_signal = round_dp(float(signal_price), PRICE_DP)
        if stored_signal == 0:
            continue
        record[field] = round_dp(((future_close / stored_signal) - 1.0) * 100.0, RETURN_DP)
        changed = True
    return changed


_FINAL_FIELDS = (
    "signal_price",
    "currency",
    "rvol",
    "displacement",
    "anomaly_score",
    "bargaining_power",
    "bargaining_power_label_en",
    "bargaining_power_label_zh",
)


def _new_row(anomaly: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": anomaly["date"],
        "ticker": anomaly["ticker"],
        "market": anomaly["market"],
        "signal_price": anomaly["signal_price"],
        "currency": anomaly["currency"],
        "rvol": anomaly["rvol"],
        "displacement": anomaly["displacement"],
        "anomaly_score": anomaly["anomaly_score"],
        "bargaining_power": anomaly["bargaining_power"],
        "bargaining_power_label_en": anomaly["bargaining_power_label_en"],
        "bargaining_power_label_zh": anomaly["bargaining_power_label_zh"],
        "t_plus_3_return_pct": None,
        "t_plus_5_return_pct": None,
        "t_plus_10_return_pct": None,
    }


def append_anomalies(records: list[dict[str, Any]], anomalies: list[dict[str, Any]]) -> int:
    """Append first-seen (date, ticker) rows. Return how many were added.

    This is the intraday rule. An existing same-day row is left as it is,
    including a partial close. Post-close replacement is finalize_completed_session.
    """

    seen = {(row["date"], row["ticker"]) for row in records}
    added = 0
    ordered = sorted(anomalies, key=lambda row: (row["date"], row["market"], row["ticker"]))
    for anomaly in ordered:
        key = (anomaly["date"], anomaly["ticker"])
        if key in seen:
            continue
        records.append(_new_row(anomaly))
        seen.add(key)
        added += 1
    return added


def finalize_completed_session(
    records: list[dict[str, Any]],
    anomalies: list[dict[str, Any]],
    measured_tickers: set[str],
    market: str,
    session_date: str,
) -> tuple[int, int, int]:
    """Replace same-day rows for one market's completed session.

    `measured_tickers` are names that have a real bar on `session_date`.
    A measured anomaly replaces `signal_price`, RVOL, displacement, score,
    tag, and labels, and keeps any T+N returns already stored. If no row
    exists, the completed anomaly is appended. A measured name that is not
    an anomaly loses its same-day row, so a partial bar cannot lock a flag.
    Other dates, other markets, and tickers with no bar on this session are
    unchanged.

    Returns (replaced, added, removed).
    """

    if not measured_tickers:
        return (0, 0, 0)
    anomaly_by_ticker = {
        row["ticker"]: row
        for row in anomalies
        if row.get("market") == market
        and row.get("date") == session_date
        and row.get("ticker") in measured_tickers
    }
    replaced = 0
    removed = 0
    seen: set[str] = set()
    kept: list[dict[str, Any]] = []
    for record in records:
        same_session = (
            record.get("market") == market
            and record.get("date") == session_date
            and record.get("ticker") in measured_tickers
        )
        if not same_session:
            kept.append(record)
            continue
        ticker = str(record["ticker"])
        seen.add(ticker)
        anomaly = anomaly_by_ticker.get(ticker)
        if anomaly is None:
            removed += 1
            continue
        for field in _FINAL_FIELDS:
            record[field] = anomaly[field]
        kept.append(record)
        replaced += 1
    records.clear()
    records.extend(kept)
    added_rows: list[dict[str, Any]] = []
    for ticker in sorted(anomaly_by_ticker):
        if ticker in seen:
            continue
        added_rows.append(_new_row(anomaly_by_ticker[ticker]))
    added_rows.sort(key=lambda row: (row["date"], row["market"], row["ticker"]))
    records.extend(added_rows)
    return (replaced, len(added_rows), removed)


def apply_backfill(
    records: list[dict[str, Any]],
    bars_by_ticker: dict[str, list[Bar]],
    now: datetime,
) -> int:
    changed = 0
    for record in records:
        bars = bars_by_ticker.get(record["ticker"])
        if not bars:
            continue
        if backfill_record(record, bars, now):
            changed += 1
    return changed


def build_history_document(records: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    return {
        "updated_at": isoformat_offset(now),
        "records": records,
        "summary_by_tag": summarize(records),
    }
