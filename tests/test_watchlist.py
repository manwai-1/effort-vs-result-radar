import json
from pathlib import Path

import pytest

from scanner.models import ScanError
from scanner.watchlist import load_watchlist


def test_snapshot_counts_and_required_markets():
    document = json.loads(Path("watchlist.json").read_text(encoding="utf-8"))
    symbols = load_watchlist(Path("watchlist.json"))
    us = [row for row in symbols if row["market"] == "US"]
    hk = [row for row in symbols if row["market"] == "HK"]
    assert len(us) == 101
    assert len(hk) == 95
    assert {row["ticker"] for row in us} >= {"GOOG", "GOOGL", "AAPL", "SPCX"}
    by_ticker = {row["ticker"]: row for row in symbols}
    assert by_ticker["0700.HK"]["market"] == "HK"
    assert by_ticker["0005.HK"]["market"] == "HK"
    assert by_ticker["9988.HK"]["market"] == "HK"
    assert all(row["market"] in {"US", "HK"} for row in symbols)
    assert all(row["ticker"].endswith(".HK") for row in hk)
    assert all(not row["ticker"].endswith(".HK") for row in us)
    assert document["retrieved_on"] == "2026-11-26"
    assert document["sources"][0]["as_of"] == "2026-11-02"
    assert document["sources"][0]["url"].startswith("https://www.nasdaq.com/")
    assert document["sources"][1]["as_of"] == "2026-11-20"
    assert "20261120T174500.pdf" in document["sources"][1]["url"]
    assert "Nil" in document["sources"][1]["citation"]


def test_market_must_be_explicit(tmp_path):
    path = tmp_path / "watchlist.json"
    path.write_text(
        json.dumps({"symbols": [{"ticker": "0700.HK", "name": "TENCENT"}]}),
        encoding="utf-8",
    )
    with pytest.raises(ScanError) as raised:
        load_watchlist(path)
    assert raised.value.code == 2

    path.write_text(
        json.dumps({"symbols": [{"ticker": "AAPL", "market": "HK"}]}),
        encoding="utf-8",
    )
    with pytest.raises(ScanError):
        load_watchlist(path)
