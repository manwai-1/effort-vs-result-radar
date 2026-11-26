"""Post-close scans use synthetic bars. These are not market prices."""

import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

from scanner.hours import is_post_close_window, is_regular_session, open_markets
from scanner.ledger import summarize
from scanner.models import Bar
from scanner.run import RunConfig, run
from scanner.validate import validate_history, validate_radar
from tests.conftest import flat_bars

NY = ZoneInfo("America/New_York")
HK = ZoneInfo("Asia/Hong_Kong")


def _symbols():
    return [
        {"ticker": "FIXU", "market": "US", "name": "Fixture US"},
        {"ticker": "FIXH.HK", "market": "HK", "name": "Fixture HK"},
    ]


def _series(end: date) -> dict[str, list[Bar]]:
    start = date(2026, 6, 1)
    count = (end - start).days + 1
    return {
        "FIXU": flat_bars(start, count),
        "FIXH.HK": flat_bars(start, count),
    }


def _set_bar(rows: list[Bar], session: date, *, close: float, volume: float, high: float | None = None) -> None:
    top = close if high is None else high
    if top < close:
        top = close
    replacement = Bar(session, 100.0, top, min(99.0, close), close, volume)
    for index, bar in enumerate(rows):
        if bar.date == session:
            rows[index] = replacement
            return
    raise AssertionError(f"no bar on {session}")


def _write_inputs(tmp_path, series: dict[str, list[Bar]]):
    watchlist = tmp_path / "watchlist.json"
    bars = tmp_path / "bars.json"
    watchlist.write_text(
        json.dumps({"note": "Synthetic fixture universe. Not an index.", "symbols": _symbols()}),
        encoding="utf-8",
    )
    payload = {
        "note": "Synthetic fixture bars. Not market prices and not performance.",
        "series": {
            ticker: [
                {
                    "date": bar.date.isoformat(),
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                }
                for bar in rows
            ]
            for ticker, rows in series.items()
        },
    }
    bars.write_text(json.dumps(payload), encoding="utf-8")
    return watchlist, bars


def _run(tmp_path, watchlist, bars, when: datetime, *, scheduled: bool = True) -> tuple[dict, dict]:
    radar_path = tmp_path / "radar.json"
    history_path = tmp_path / "history.json"
    code = run(
        RunConfig(
            watchlist_path=watchlist,
            radar_path=radar_path,
            history_path=history_path,
            now=when,
            scheduled=scheduled,
            bars_path=bars,
            push=False,
        )
    )
    assert code == 0
    radar = json.loads(radar_path.read_text(encoding="utf-8"))
    history = json.loads(history_path.read_text(encoding="utf-8"))
    validate_radar(radar)
    validate_history(history)
    return radar, history


def _point(radar: dict, ticker: str) -> dict:
    return next(point for point in radar["points"] if point["ticker"] == ticker)


def _row(history: dict, ticker: str, session: str) -> dict:
    matches = [row for row in history["records"] if row["ticker"] == ticker and row["date"] == session]
    assert len(matches) == 1
    return matches[0]


def _corrupt_tag(path, ticker: str, session: str) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    row = next(record for record in document["records"] if record["ticker"] == ticker and record["date"] == session)
    row["bargaining_power"] = "buyer_absorption"
    row["bargaining_power_label_en"] = "Buyer Absorption"
    row["bargaining_power_label_zh"] = "買方暗中承接"
    document["summary_by_tag"] = summarize(document["records"])
    path.write_text(json.dumps(document), encoding="utf-8")


def test_1620_rewrites_radar_and_replaces_the_partial_same_day_row(tmp_path, monkeypatch):
    monkeypatch.setattr("scanner.fetch.yf_download", lambda **kwargs: (_ for _ in ()).throw(AssertionError("yfinance")))
    session = date(2026, 11, 27)
    series = _series(session)
    _set_bar(series["FIXU"], session, close=100.2, volume=2500.0, high=100.4)
    _set_bar(series["FIXH.HK"], session, close=101.0, volume=3000.0, high=101.0)
    watchlist, bars = _write_inputs(tmp_path, series)
    radar_path = tmp_path / "radar.json"
    history_path = tmp_path / "history.json"

    hk_partial = datetime(2026, 11, 27, 15, 30, tzinfo=HK)
    assert is_regular_session(hk_partial, "HK")
    assert not is_regular_session(hk_partial, "US")
    radar, history = _run(tmp_path, watchlist, bars, hk_partial)
    assert _row(history, "FIXH.HK", "2026-11-27")["signal_price"] == 101.0
    assert _row(history, "FIXH.HK", "2026-11-27")["rvol"] == 3.0
    assert [row["ticker"] for row in history["records"]] == ["FIXH.HK"]

    us_partial = datetime(2026, 11, 27, 15, 30, tzinfo=NY)
    radar, history = _run(tmp_path, watchlist, bars, us_partial)
    assert radar["generated_at"] == "2026-11-27T15:30:00-05:00"
    assert _point(radar, "FIXU")["last_price"] == 100.2
    assert _point(radar, "FIXU")["rvol"] == 2.5
    assert _point(radar, "FIXU")["displacement"] == 0.1
    us_row = _row(history, "FIXU", "2026-11-27")
    assert us_row["signal_price"] == 100.2
    assert us_row["rvol"] == 2.5
    assert us_row["displacement"] == 0.1
    assert us_row["anomaly_score"] == 25.0
    assert us_row["bargaining_power"] == "stalemate_compression"
    assert _row(history, "FIXH.HK", "2026-11-27")["signal_price"] == 101.0
    partial_radar = radar_path.read_bytes()

    _corrupt_tag(history_path, "FIXU", "2026-11-27")
    _set_bar(series["FIXU"], session, close=100.4, volume=4000.0, high=100.4)
    _, bars = _write_inputs(tmp_path, series)

    # 16:19 is closed for the session and is not the post-close window.
    us_1619 = datetime(2026, 11, 27, 16, 19, tzinfo=NY)
    assert not open_markets(us_1619)
    assert not is_post_close_window(us_1619, "US")
    code = run(
        RunConfig(watchlist, radar_path, history_path, us_1619, True, bars, False)
    )
    assert code == 0
    assert radar_path.read_bytes() == partial_radar
    stale = json.loads(history_path.read_text(encoding="utf-8"))
    assert _row(stale, "FIXU", "2026-11-27")["signal_price"] == 100.2
    assert _row(stale, "FIXU", "2026-11-27")["bargaining_power"] == "buyer_absorption"

    us_close = datetime(2026, 11, 27, 16, 20, tzinfo=NY)
    assert not open_markets(us_close)
    assert is_post_close_window(us_close, "US")
    assert not is_post_close_window(us_close, "HK")
    radar, history = _run(tmp_path, watchlist, bars, us_close)
    assert radar_path.read_bytes() != partial_radar
    assert radar["generated_at"] == "2026-11-27T16:20:00-05:00"
    official = _point(radar, "FIXU")
    assert official["last_price"] == 100.4
    assert official["rvol"] == 4.0
    assert official["displacement"] == 0.2
    assert official["anomaly_score"] == 20.0
    assert official["is_anomaly"] is True
    # Hong Kong's Friday bar is the latest real bar. Saturday is not invented.
    assert _point(radar, "FIXH.HK")["last_price"] == 101.0
    assert all(row["date"] != "2026-11-28" for row in history["records"])
    finalized = _row(history, "FIXU", "2026-11-27")
    assert finalized["signal_price"] == 100.4
    assert finalized["rvol"] == 4.0
    assert finalized["displacement"] == 0.2
    assert finalized["anomaly_score"] == 20.0
    assert finalized["bargaining_power"] == "stalemate_compression"
    assert finalized["bargaining_power_label_en"] == "Stalemate / Compression"
    assert finalized["bargaining_power_label_zh"] == "多空角力壓縮"
    assert finalized["t_plus_3_return_pct"] is None
    untouched = _row(history, "FIXH.HK", "2026-11-27")
    assert untouched["signal_price"] == 101.0
    assert untouched["rvol"] == 3.0
    assert untouched["displacement"] == 0.5
    assert untouched["anomaly_score"] == 6.0


def test_hk_1620_finalizes_hk_and_does_not_price_a_us_session_that_has_not_opened(tmp_path, monkeypatch):
    monkeypatch.setattr("scanner.fetch.yf_download", lambda **kwargs: (_ for _ in ()).throw(AssertionError("yfinance")))
    session = date(2026, 11, 27)
    series = _series(session)
    _set_bar(series["FIXU"], date(2026, 11, 26), close=90.0, volume=1000.0, high=91.0)
    _set_bar(series["FIXU"], session, close=100.4, volume=4000.0, high=100.4)
    _set_bar(series["FIXH.HK"], session, close=100.2, volume=2500.0, high=100.4)
    watchlist, bars = _write_inputs(tmp_path, series)

    hk_partial = datetime(2026, 11, 27, 15, 30, tzinfo=HK)
    _, history = _run(tmp_path, watchlist, bars, hk_partial)
    assert _row(history, "FIXH.HK", "2026-11-27")["signal_price"] == 100.2
    assert _row(history, "FIXH.HK", "2026-11-27")["rvol"] == 2.5
    assert [row for row in history["records"] if row["market"] == "US"] == []

    _set_bar(series["FIXH.HK"], session, close=100.4, volume=4000.0, high=100.4)
    _, bars = _write_inputs(tmp_path, series)
    hk_close = datetime(2026, 11, 27, 16, 20, tzinfo=HK)
    assert is_post_close_window(hk_close, "HK")
    assert not is_regular_session(hk_close, "US")
    assert not is_post_close_window(hk_close, "US")
    radar, history = _run(tmp_path, watchlist, bars, hk_close)
    assert radar["generated_at"] == "2026-11-27T16:20:00+08:00"
    hk = _point(radar, "FIXH.HK")
    assert hk["last_price"] == 100.4
    assert hk["rvol"] == 4.0
    assert hk["displacement"] == 0.2
    assert hk["currency"] == "HKD"
    us = _point(radar, "FIXU")
    assert us["last_price"] == 90.0
    assert us["is_anomaly"] is False
    finalized = _row(history, "FIXH.HK", "2026-11-27")
    assert finalized["signal_price"] == 100.4
    assert finalized["rvol"] == 4.0
    assert finalized["displacement"] == 0.2
    assert finalized["anomaly_score"] == 20.0
    assert [row for row in history["records"] if row["market"] == "US"] == []
    assert all(row["date"] != "2026-11-27" or row["market"] == "HK" for row in history["records"])


def test_us_stays_final_while_hong_kong_is_open(tmp_path, monkeypatch):
    monkeypatch.setattr("scanner.fetch.yf_download", lambda **kwargs: (_ for _ in ()).throw(AssertionError("yfinance")))
    monday = date(2026, 11, 30)
    tuesday = date(2026, 12, 1)
    series = _series(tuesday)
    _set_bar(series["FIXU"], monday, close=100.2, volume=2500.0, high=100.4)
    _set_bar(series["FIXH.HK"], tuesday, close=100.2, volume=2500.0, high=100.4)
    watchlist, bars = _write_inputs(tmp_path, series)

    us_partial = datetime(2026, 11, 30, 15, 30, tzinfo=NY)
    _, history = _run(tmp_path, watchlist, bars, us_partial)
    assert _row(history, "FIXU", "2026-11-30")["signal_price"] == 100.2
    assert [row for row in history["records"] if row["market"] == "HK"] == []

    _set_bar(series["FIXU"], monday, close=100.4, volume=4000.0, high=100.4)
    _, bars = _write_inputs(tmp_path, series)
    # Tuesday 09:30 HKT is still Monday 20:30 EST: HK is open, US just closed.
    overlap = datetime(2026, 12, 1, 9, 30, tzinfo=HK)
    assert is_regular_session(overlap, "HK")
    assert is_post_close_window(overlap, "US")
    radar, history = _run(tmp_path, watchlist, bars, overlap)
    assert _row(history, "FIXU", "2026-11-30")["signal_price"] == 100.4
    assert _row(history, "FIXU", "2026-11-30")["rvol"] == 4.0
    assert _row(history, "FIXH.HK", "2026-12-01")["signal_price"] == 100.2
    assert _row(history, "FIXH.HK", "2026-12-01")["rvol"] == 2.5
    assert _point(radar, "FIXU")["last_price"] == 100.4
    assert _point(radar, "FIXH.HK")["last_price"] == 100.2

    _set_bar(series["FIXH.HK"], tuesday, close=100.8, volume=5000.0, high=100.8)
    _, bars = _write_inputs(tmp_path, series)
    later = datetime(2026, 12, 1, 10, 0, tzinfo=HK)
    assert is_regular_session(later, "HK")
    assert is_post_close_window(later, "US")
    radar, history = _run(tmp_path, watchlist, bars, later)
    assert _point(radar, "FIXH.HK")["last_price"] == 100.8
    assert _point(radar, "FIXH.HK")["rvol"] == 5.0
    assert _row(history, "FIXH.HK", "2026-12-01")["signal_price"] == 100.2
    assert _row(history, "FIXH.HK", "2026-12-01")["rvol"] == 2.5
    assert _row(history, "FIXU", "2026-11-30")["signal_price"] == 100.4
    assert _row(history, "FIXU", "2026-11-30")["rvol"] == 4.0
    assert _point(radar, "FIXU")["last_price"] == 100.4


def test_hk_finalizes_while_the_us_session_is_open(tmp_path, monkeypatch):
    monkeypatch.setattr("scanner.fetch.yf_download", lambda **kwargs: (_ for _ in ()).throw(AssertionError("yfinance")))
    session = date(2026, 7, 17)
    series = _series(session)
    _set_bar(series["FIXH.HK"], session, close=100.2, volume=2500.0, high=100.4)
    _set_bar(series["FIXU"], session, close=100.2, volume=2500.0, high=100.4)
    watchlist, bars = _write_inputs(tmp_path, series)

    hk_partial = datetime(2026, 7, 17, 15, 30, tzinfo=HK)
    assert not is_regular_session(hk_partial, "US")
    _, history = _run(tmp_path, watchlist, bars, hk_partial)
    assert _row(history, "FIXH.HK", "2026-07-17")["signal_price"] == 100.2
    assert [row for row in history["records"] if row["market"] == "US"] == []

    _set_bar(series["FIXH.HK"], session, close=100.4, volume=4000.0, high=100.4)
    _, bars = _write_inputs(tmp_path, series)
    # Friday 22:00 HKT is Friday 10:00 EDT. HK is still post-close; US is open.
    overlap = datetime(2026, 7, 17, 22, 0, tzinfo=HK)
    assert is_post_close_window(overlap, "HK")
    assert is_regular_session(overlap, "US")
    radar, history = _run(tmp_path, watchlist, bars, overlap)
    assert _row(history, "FIXH.HK", "2026-07-17")["signal_price"] == 100.4
    assert _row(history, "FIXH.HK", "2026-07-17")["rvol"] == 4.0
    assert _row(history, "FIXH.HK", "2026-07-17")["displacement"] == 0.2
    assert _row(history, "FIXU", "2026-07-17")["signal_price"] == 100.2
    assert _point(radar, "FIXH.HK")["last_price"] == 100.4
    assert _point(radar, "FIXU")["last_price"] == 100.2

    _set_bar(series["FIXU"], session, close=110.0, volume=9000.0, high=110.0)
    _, bars = _write_inputs(tmp_path, series)
    later = datetime(2026, 7, 17, 22, 30, tzinfo=HK)
    assert is_regular_session(later, "US")
    assert is_post_close_window(later, "HK")
    radar, history = _run(tmp_path, watchlist, bars, later)
    assert _point(radar, "FIXU")["last_price"] == 110.0
    assert _row(history, "FIXU", "2026-07-17")["signal_price"] == 100.2
    assert _row(history, "FIXU", "2026-07-17")["rvol"] == 2.5
    assert _row(history, "FIXH.HK", "2026-07-17")["signal_price"] == 100.4
    assert _row(history, "FIXH.HK", "2026-07-17")["rvol"] == 4.0


def test_post_close_appends_when_the_partial_bar_was_not_an_anomaly(tmp_path, monkeypatch):
    monkeypatch.setattr("scanner.fetch.yf_download", lambda **kwargs: (_ for _ in ()).throw(AssertionError("yfinance")))
    session = date(2026, 11, 27)
    series = _series(session)
    watchlist, bars = _write_inputs(tmp_path, series)
    _, history = _run(tmp_path, watchlist, bars, datetime(2026, 11, 27, 15, 30, tzinfo=NY))
    assert history["records"] == []

    _set_bar(series["FIXU"], session, close=100.4, volume=4000.0, high=100.4)
    _, bars = _write_inputs(tmp_path, series)
    radar, history = _run(tmp_path, watchlist, bars, datetime(2026, 11, 27, 16, 20, tzinfo=NY))
    assert _point(radar, "FIXU")["last_price"] == 100.4
    assert _point(radar, "FIXU")["rvol"] == 4.0
    row = _row(history, "FIXU", "2026-11-27")
    assert row["signal_price"] == 100.4
    assert row["rvol"] == 4.0
    assert row["bargaining_power"] == "stalemate_compression"
    assert [record["ticker"] for record in history["records"]] == ["FIXU"]


def test_post_close_removes_a_partial_row_the_close_does_not_confirm(tmp_path, monkeypatch):
    monkeypatch.setattr("scanner.fetch.yf_download", lambda **kwargs: (_ for _ in ()).throw(AssertionError("yfinance")))
    session = date(2026, 11, 27)
    series = _series(session)
    _set_bar(series["FIXU"], session, close=100.2, volume=2500.0, high=100.4)
    watchlist, bars = _write_inputs(tmp_path, series)
    _, history = _run(tmp_path, watchlist, bars, datetime(2026, 11, 27, 15, 30, tzinfo=NY))
    assert _row(history, "FIXU", "2026-11-27")["signal_price"] == 100.2

    _set_bar(series["FIXU"], session, close=100.0, volume=1000.0, high=101.0)
    _, bars = _write_inputs(tmp_path, series)
    radar, history = _run(tmp_path, watchlist, bars, datetime(2026, 11, 27, 16, 20, tzinfo=NY))
    assert _point(radar, "FIXU")["last_price"] == 100.0
    assert _point(radar, "FIXU")["rvol"] == 1.0
    assert _point(radar, "FIXU")["is_anomaly"] is False
    assert history["records"] == []
    assert history["summary_by_tag"][0]["sample_count"] == 0
    assert history["summary_by_tag"][2]["sample_count"] == 0
