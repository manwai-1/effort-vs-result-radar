import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from scanner.fetch import yf_download
from scanner.models import Bar
from scanner.run import RunConfig, run
from scanner.validate import validate_history, validate_radar
from tests.conftest import flat_bars


NOW = datetime.fromisoformat("2026-11-27T15:00:00-05:00")


def _write_inputs(tmp_path, series: dict[str, list[Bar]], symbols: list[dict]):
    watchlist = tmp_path / "watchlist.json"
    bars = tmp_path / "bars.json"
    watchlist.write_text(
        json.dumps({"note": "Synthetic fixture universe. Not an index.", "symbols": symbols}),
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


def _symbols():
    return [
        {"ticker": "FIXU", "market": "US", "name": "Fixture US anomaly"},
        {"ticker": "FIXN", "market": "US", "name": "Fixture US normal"},
        {"ticker": "FIXH.HK", "market": "HK", "name": "Fixture HK normal"},
    ]


def _series():
    start = date(2026, 10, 28)
    fixu = flat_bars(start, 31)
    last = fixu[-1]
    fixu[-1] = Bar(last.date, 50.0, 100.4, 50.0, 100.2, 2500.0)
    fixn = flat_bars(start, 31)
    fixh = flat_bars(start, 31)
    return {"FIXU": fixu, "FIXN": fixn, "FIXH.HK": fixh}


def test_fixture_scan_writes_the_contract_and_does_not_call_yfinance(tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("yfinance was called")

    monkeypatch.setattr("scanner.fetch.yf_download", boom)
    assert yf_download is not None
    watchlist, bars = _write_inputs(tmp_path, _series(), _symbols())
    radar_path = tmp_path / "radar.json"
    history_path = tmp_path / "history.json"
    code = run(
        RunConfig(
            watchlist_path=watchlist,
            radar_path=radar_path,
            history_path=history_path,
            now=NOW,
            scheduled=True,
            bars_path=bars,
            push=False,
        )
    )
    assert code == 0
    radar = json.loads(radar_path.read_text(encoding="utf-8"))
    history = json.loads(history_path.read_text(encoding="utf-8"))
    validate_radar(radar)
    validate_history(history)
    assert radar["generated_at"] == "2026-11-27T15:00:00-05:00"
    assert radar["universe"] == {"us_count": 2, "hk_count": 1}
    assert "data_status" not in radar
    by_ticker = {point["ticker"]: point for point in radar["points"]}
    anomaly = by_ticker["FIXU"]
    assert anomaly["market"] == "US"
    assert anomaly["rvol"] == 2.5
    assert anomaly["displacement"] == 0.1
    assert anomaly["anomaly_score"] == 25.0
    assert anomaly["is_anomaly"] is True
    assert anomaly["trend_20d"] == "sideways"
    assert anomaly["bargaining_power"] == "stalemate_compression"
    assert anomaly["bargaining_power_label_en"] == "Stalemate / Compression"
    assert anomaly["bargaining_power_label_zh"] == "多空角力壓縮"
    assert anomaly["last_price"] == 100.2
    assert anomaly["currency"] == "USD"
    normal = by_ticker["FIXN"]
    assert normal["is_anomaly"] is False
    assert normal["rvol"] == 1.0
    assert normal["bargaining_power"] is None
    assert normal["bargaining_power_label_en"] is None
    assert normal["bargaining_power_label_zh"] is None
    assert by_ticker["FIXH.HK"]["market"] == "HK"
    assert by_ticker["FIXH.HK"]["currency"] == "HKD"
    assert by_ticker["FIXH.HK"]["is_anomaly"] is False
    assert [row["ticker"] for row in history["records"]] == ["FIXU"]
    assert history["records"][0]["date"] == "2026-11-27"
    assert history["records"][0]["signal_price"] == 100.2
    assert history["records"][0]["t_plus_3_return_pct"] is None
    assert history["records"][0]["t_plus_10_return_pct"] is None
    stalemate = history["summary_by_tag"][2]
    assert stalemate["bargaining_power"] == "stalemate_compression"
    assert stalemate["sample_count"] == 1
    assert stalemate["t_plus_3"]["hit_rate_label"] == "不適用"
    assert stalemate["t_plus_3"]["average_return_pct"] is None

    # Same session again, still an anomaly, at a different price: keep the first flag.
    series = _series()
    last = series["FIXU"][-1]
    series["FIXU"][-1] = Bar(last.date, 100.0, 100.5, 99.9, 100.4, 3000.0)
    watchlist, bars = _write_inputs(tmp_path, series, _symbols())
    code = run(
        RunConfig(
            watchlist_path=watchlist,
            radar_path=radar_path,
            history_path=history_path,
            now=NOW,
            scheduled=False,
            bars_path=bars,
            push=False,
        )
    )
    assert code == 0
    history = json.loads(history_path.read_text(encoding="utf-8"))
    validate_history(history)
    assert len(history["records"]) == 1
    assert history["records"][0]["signal_price"] == 100.2


def test_second_run_backfills_without_rewriting_a_closed_market_radar(tmp_path, monkeypatch):
    monkeypatch.setattr("scanner.fetch.yf_download", lambda **kwargs: (_ for _ in ()).throw(AssertionError("yfinance")))
    watchlist, bars_path = _write_inputs(tmp_path, _series(), _symbols())
    radar_path = tmp_path / "radar.json"
    history_path = tmp_path / "history.json"
    assert run(
        RunConfig(watchlist, radar_path, history_path, NOW, True, bars_path, False)
    ) == 0
    original_radar = radar_path.read_bytes()
    series = _series()
    last_date = series["FIXU"][-1].date
    for offset in range(1, 11):
        session = last_date + timedelta(days=offset)
        series["FIXU"].append(Bar(session, 110.22, 111.22, 109.22, 110.22, 1000.0))
    _, extended = _write_inputs(tmp_path, series, _symbols())
    # 2026-12-07 21:00 UTC is 16:00 EST and 05:00 the next day in Hong Kong.
    later = datetime(2026, 12, 7, 21, 0, tzinfo=timezone.utc)
    assert run(
        RunConfig(watchlist, radar_path, history_path, later, True, extended, False)
    ) == 0
    assert radar_path.read_bytes() == original_radar
    history = json.loads(history_path.read_text(encoding="utf-8"))
    validate_history(history)
    assert len(history["records"]) == 1
    row = history["records"][0]
    assert row["signal_price"] == 100.2
    assert row["t_plus_3_return_pct"] == 10.0
    assert row["t_plus_5_return_pct"] == 10.0
    assert row["t_plus_10_return_pct"] == 10.0
    card = history["summary_by_tag"][2]
    assert card["sample_count"] == 1
    assert card["t_plus_10"]["sample_count"] == 1
    assert card["t_plus_10"]["average_return_pct"] == 10.0
    assert card["t_plus_10"]["hit_rate_pct"] is None
    assert card["t_plus_10"]["hit_rate_label"] == "不適用"


def test_committed_mini_fixture_matches_the_flat_case(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "scanner.fetch.yf_download",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("yfinance")),
    )
    radar_path = tmp_path / "radar.json"
    history_path = tmp_path / "history.json"
    code = run(
        RunConfig(
            watchlist_path=Path("tests/fixtures/mini_watchlist.json"),
            radar_path=radar_path,
            history_path=history_path,
            now=NOW,
            scheduled=False,
            bars_path=Path("tests/fixtures/mini_bars.json"),
            push=False,
        )
    )
    assert code == 0
    radar = json.loads(radar_path.read_text(encoding="utf-8"))
    fixu = next(point for point in radar["points"] if point["ticker"] == "FIXU")
    assert fixu["rvol"] == 2.5
    assert fixu["displacement"] == 0.1
    assert fixu["anomaly_score"] == 25.0
    assert fixu["is_anomaly"] is True
    assert fixu["bargaining_power"] == "stalemate_compression"


def test_fixture_run_cannot_overwrite_committed_data():
    radar_path = Path("public/data/radar.json")
    history_path = Path("public/data/history_results.json")
    before_radar = radar_path.read_bytes()
    before_history = history_path.read_bytes()
    try:
        run(
            RunConfig(
                watchlist_path=Path("tests/fixtures/mini_watchlist.json"),
                radar_path=radar_path,
                history_path=history_path,
                now=NOW,
                scheduled=False,
                bars_path=Path("tests/fixtures/mini_bars.json"),
                push=False,
            )
        )
        raised = None
    except Exception as exc:
        raised = exc
    assert getattr(raised, "code", None) == 2
    assert "public/data" in str(raised)
    assert radar_path.read_bytes() == before_radar
    assert history_path.read_bytes() == before_history


def test_closed_schedule_does_not_invent_a_new_flag(tmp_path, monkeypatch):
    monkeypatch.setattr("scanner.fetch.yf_download", lambda **kwargs: (_ for _ in ()).throw(AssertionError("yfinance")))
    watchlist, bars = _write_inputs(tmp_path, _series(), _symbols())
    radar_path = tmp_path / "radar.json"
    history_path = tmp_path / "history.json"
    sunday = datetime(2026, 11, 29, 15, 0, tzinfo=timezone.utc)
    code = run(RunConfig(watchlist, radar_path, history_path, sunday, True, bars, False))
    assert code == 0
    assert not radar_path.exists()
    assert not history_path.exists()


def test_insufficient_history_does_not_replace_files(tmp_path, monkeypatch):
    monkeypatch.setattr("scanner.fetch.yf_download", lambda **kwargs: (_ for _ in ()).throw(AssertionError("yfinance")))
    short = {"FIXU": flat_bars(date(2026, 11, 1), 5)}
    symbols = [{"ticker": "FIXU", "market": "US", "name": "short"}]
    watchlist, bars = _write_inputs(tmp_path, short, symbols)
    radar_path = tmp_path / "radar.json"
    history_path = tmp_path / "history.json"
    radar_path.write_text('{"keep": true}\n', encoding="utf-8")
    try:
        run(RunConfig(watchlist, radar_path, history_path, NOW, False, bars, False))
        raised = None
    except Exception as exc:
        raised = exc
    assert getattr(raised, "code", None) == 3
    assert radar_path.read_text(encoding="utf-8") == '{"keep": true}\n'
    assert not history_path.exists()
