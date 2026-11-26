from datetime import date, datetime, timezone

from scanner.ledger import (
    append_anomalies,
    apply_backfill,
    backfill_record,
    finalize_completed_session,
    summarize,
)
from scanner.models import Bar
from scanner.tags import STALEMATE_HIT_RATE_LABEL


def _anomaly(ticker: str, session: str, price: float, tag: str = "buyer_absorption") -> dict:
    labels = {
        "buyer_absorption": ("Buyer Absorption", "買方暗中承接"),
        "seller_distribution": ("Seller Distribution", "賣方暗中出貨"),
        "stalemate_compression": ("Stalemate / Compression", "多空角力壓縮"),
    }
    english, chinese = labels[tag]
    return {
        "date": session,
        "ticker": ticker,
        "market": "US",
        "signal_price": price,
        "currency": "USD",
        "rvol": 2.5,
        "displacement": 0.1,
        "anomaly_score": 25.0,
        "bargaining_power": tag,
        "bargaining_power_label_en": english,
        "bargaining_power_label_zh": chinese,
    }


def test_dedupe_keeps_the_first_signal_and_appends_a_new_day():
    records: list[dict] = []
    assert append_anomalies(records, [_anomaly("AAA", "2026-11-27", 100.0)]) == 1
    assert append_anomalies(records, [_anomaly("AAA", "2026-11-27", 999.0)]) == 0
    assert records[0]["signal_price"] == 100.0
    assert append_anomalies(records, [_anomaly("AAA", "2026-11-30", 110.0), _anomaly("BBB", "2026-11-27", 50.0)]) == 2
    assert [(row["date"], row["ticker"]) for row in records] == [
        ("2026-11-27", "AAA"),
        ("2026-11-27", "BBB"),
        ("2026-11-30", "AAA"),
    ]
    assert records[0]["t_plus_3_return_pct"] is None


def test_backfill_counts_trading_sessions_and_skips_a_partial_day():
    bars = [
        Bar(date(2026, 11, 27), 100, 101, 99, 100, 1),
        Bar(date(2026, 11, 30), 110, 111, 109, 110, 1),
        Bar(date(2026, 12, 1), 110, 111, 109, 110, 1),
        Bar(date(2026, 12, 2), 101, 102, 100, 101, 1),
        Bar(date(2026, 12, 3), 100, 101, 99, 100, 1),
        Bar(date(2026, 12, 4), 90, 91, 89, 90, 1),
    ]
    record = _anomaly("AAA", "2026-11-27", 100.0)
    record.update({"t_plus_3_return_pct": None, "t_plus_5_return_pct": None, "t_plus_10_return_pct": None})
    # Friday 15:00 ET: the signal day is still partial, so nothing is filled.
    assert backfill_record(record, bars, datetime(2026, 11, 27, 20, 0, tzinfo=timezone.utc)) is False
    assert record["t_plus_3_return_pct"] is None
    # Friday 16:00 ET the following week: T+3 is Wednesday 101, not Monday 110.
    assert backfill_record(record, bars, datetime(2026, 12, 4, 21, 0, tzinfo=timezone.utc)) is True
    assert record["t_plus_3_return_pct"] == 1.0
    assert record["t_plus_5_return_pct"] == -10.0
    assert record["t_plus_10_return_pct"] is None
    # A later run does not revise a filled return.
    bars[-1] = Bar(date(2026, 12, 4), 90, 91, 89, 50, 1)
    assert backfill_record(record, bars, datetime(2026, 12, 4, 21, 0, tzinfo=timezone.utc)) is False
    assert record["t_plus_5_return_pct"] == -10.0


def test_summary_hit_rules_and_stalemate_label():
    records = []
    append_anomalies(
        records,
        [
            _anomaly("ABS", "2026-11-02", 10, "buyer_absorption"),
            _anomaly("DST", "2026-11-02", 10, "seller_distribution"),
            _anomaly("STL", "2026-11-02", 10, "stalemate_compression"),
        ],
    )
    for record, values in zip(records, ([1.0, 0.0, -1.0], [1.0, 0.0, -1.0], [1.0, 0.0, -1.0])):
        record["t_plus_3_return_pct"] = values[0]
        record["t_plus_5_return_pct"] = values[1]
        record["t_plus_10_return_pct"] = values[2]
    # A fourth absorption row has no returns and must not enter the horizon samples.
    append_anomalies(records, [_anomaly("PEND", "2026-11-03", 10, "buyer_absorption")])
    summary = {entry["bargaining_power"]: entry for entry in summarize(records)}

    absorption = summary["buyer_absorption"]
    assert absorption["sample_count"] == 2
    assert absorption["t_plus_3"]["sample_count"] == 1
    assert absorption["t_plus_3"]["average_return_pct"] == 1.0
    assert absorption["t_plus_3"]["hit_rate_pct"] == 100.0
    assert absorption["t_plus_5"]["sample_count"] == 1
    assert absorption["t_plus_5"]["hit_rate_pct"] == 0.0
    assert absorption["t_plus_5"]["average_return_pct"] == 0.0
    assert absorption["t_plus_10"]["hit_rate_pct"] == 0.0
    assert absorption["t_plus_3"]["hit_rate_applicable"] is True

    distribution = summary["seller_distribution"]
    assert distribution["t_plus_3"]["hit_rate_pct"] == 0.0
    assert distribution["t_plus_10"]["hit_rate_pct"] == 100.0
    assert distribution["sample_count"] == 1

    stalemate = summary["stalemate_compression"]
    assert stalemate["sample_count"] == 1
    assert stalemate["t_plus_3"]["average_return_pct"] == 1.0
    assert stalemate["t_plus_3"]["sample_count"] == 1
    assert stalemate["t_plus_3"]["hit_rate_pct"] is None
    assert stalemate["t_plus_3"]["hit_rate_applicable"] is False
    assert stalemate["t_plus_3"]["hit_rate_label"] == STALEMATE_HIT_RATE_LABEL
    assert stalemate["t_plus_5"]["hit_rate_label"] == "不適用"
    assert stalemate["t_plus_10"]["hit_rate_label"] == "不適用"


def test_empty_summary_has_three_tags_and_null_averages():
    summary = summarize([])
    assert [entry["bargaining_power"] for entry in summary] == [
        "buyer_absorption",
        "seller_distribution",
        "stalemate_compression",
    ]
    assert summary[0]["sample_count"] == 0
    assert summary[0]["t_plus_3"]["average_return_pct"] is None
    assert summary[0]["t_plus_3"]["hit_rate_pct"] is None
    assert summary[2]["t_plus_10"]["hit_rate_label"] == "不適用"


def test_finalize_replaces_same_day_metrics_and_keeps_other_rows():
    records: list[dict] = []
    append_anomalies(records, [_anomaly("AAA", "2026-11-26", 90.0), _anomaly("AAA", "2026-11-27", 100.0)])
    records[1]["t_plus_3_return_pct"] = 1.5
    completed = _anomaly("AAA", "2026-11-27", 110.0, "seller_distribution")
    completed["rvol"] = 4.0
    completed["displacement"] = 0.2
    completed["anomaly_score"] = 20.0
    replaced, added, removed = finalize_completed_session(
        records,
        [completed],
        {"AAA"},
        "US",
        "2026-11-27",
    )
    assert (replaced, added, removed) == (1, 0, 0)
    prior = next(row for row in records if row["date"] == "2026-11-26")
    current = next(row for row in records if row["date"] == "2026-11-27")
    assert prior["signal_price"] == 90.0
    assert prior["bargaining_power"] == "buyer_absorption"
    assert current["signal_price"] == 110.0
    assert current["rvol"] == 4.0
    assert current["displacement"] == 0.2
    assert current["anomaly_score"] == 20.0
    assert current["bargaining_power"] == "seller_distribution"
    assert current["bargaining_power_label_en"] == "Seller Distribution"
    assert current["bargaining_power_label_zh"] == "賣方暗中出貨"
    assert current["t_plus_3_return_pct"] == 1.5
    assert current["t_plus_5_return_pct"] is None


def test_finalize_appends_or_removes_and_ignores_an_unmeasured_name():
    records: list[dict] = []
    append_anomalies(
        records,
        [
            _anomaly("KEEP", "2026-11-27", 50.0),
            _anomaly("DROP", "2026-11-27", 80.0),
            _anomaly("OTHER", "2026-11-26", 70.0),
        ],
    )
    completed = _anomaly("NEW", "2026-11-27", 110.0)
    replaced, added, removed = finalize_completed_session(
        records,
        [completed],
        {"DROP", "NEW"},
        "US",
        "2026-11-27",
    )
    assert (replaced, added, removed) == (0, 1, 1)
    by_key = {(row["date"], row["ticker"]): row for row in records}
    assert by_key[("2026-11-27", "KEEP")]["signal_price"] == 50.0
    assert ("2026-11-27", "DROP") not in by_key
    assert by_key[("2026-11-26", "OTHER")]["signal_price"] == 70.0
    assert by_key[("2026-11-27", "NEW")]["signal_price"] == 110.0
    assert by_key[("2026-11-27", "NEW")]["t_plus_10_return_pct"] is None


def test_apply_backfill_only_touches_rows_with_bars():
    records: list[dict] = []
    append_anomalies(records, [_anomaly("AAA", "2026-11-27", 100.0)])
    bars = {
        "AAA": [
            Bar(date(2026, 11, 27), 100, 101, 99, 100, 1),
            Bar(date(2026, 11, 30), 100, 101, 99, 103, 1),
            Bar(date(2026, 12, 1), 100, 101, 99, 100, 1),
            Bar(date(2026, 12, 2), 100, 101, 99, 100, 1),
        ]
    }
    changed = apply_backfill(records, bars, datetime(2026, 12, 2, 21, 0, tzinfo=timezone.utc))
    assert changed == 1
    assert records[0]["t_plus_3_return_pct"] == 0.0
    assert records[0]["t_plus_5_return_pct"] is None
