import json
import re
from datetime import datetime
from pathlib import Path

from scanner.validate import validate_history, validate_radar

EMPTY_RADAR = Path("tests/fixtures/empty_radar.json")
EMPTY_HISTORY = Path("tests/fixtures/empty_history.json")
COMMITTED_RADAR = Path("public/data/radar.json")
COMMITTED_HISTORY = Path("public/data/history_results.json")

# Second precision, with a numeric offset or Z. Matches scanner isoformat output.
_OFFSET_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$"
)


def _assert_offset_timestamp(value: object) -> None:
    assert isinstance(value, str)
    assert _OFFSET_TIMESTAMP.fullmatch(value), value
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None and parsed.utcoffset() is not None


def test_empty_fixture_files_are_labeled_placeholders():
    """Empty-fixture behavior stays covered, but not by the live public/data files."""
    radar = json.loads(EMPTY_RADAR.read_text(encoding="utf-8"))
    history = json.loads(EMPTY_HISTORY.read_text(encoding="utf-8"))
    assert radar["data_status"] == "empty_fixture"
    assert radar["points"] == []
    assert radar["universe"] == {"us_count": 0, "hk_count": 0}
    assert "Not a live scan" in radar["data_status_note"]
    assert history["data_status"] == "empty_fixture"
    assert history["records"] == []
    assert "Not live performance" in history["data_status_note"]
    assert [row["bargaining_power"] for row in history["summary_by_tag"]] == [
        "buyer_absorption",
        "seller_distribution",
        "stalemate_compression",
    ]
    assert history["summary_by_tag"][0]["sample_count"] == 0
    assert history["summary_by_tag"][0]["t_plus_3"]["average_return_pct"] is None
    assert history["summary_by_tag"][2]["t_plus_3"]["hit_rate_label"] == "不適用"
    assert history["summary_by_tag"][2]["t_plus_3"]["hit_rate_pct"] is None


def test_committed_public_data_accepts_live_scan_output():
    """A later scanner --push may replace these files. Schema stays; emptiness does not."""
    radar = json.loads(COMMITTED_RADAR.read_text(encoding="utf-8"))
    history = json.loads(COMMITTED_HISTORY.read_text(encoding="utf-8"))
    assert "data_status" not in radar
    assert "data_status" not in history
    validate_radar(radar)
    validate_history(history)
    _assert_offset_timestamp(radar["generated_at"])
    _assert_offset_timestamp(history["updated_at"])


def test_scanner_package_stays_free_of_ui_files():
    """The product UI lives outside the scanner. This guard stays on the Python package."""
    banned = {".html", ".css", ".tsx", ".jsx"}
    found = [
        path
        for path in Path("scanner").rglob("*")
        if path.suffix in banned
    ]
    assert found == []
    assert Path("app/page.tsx").is_file()
