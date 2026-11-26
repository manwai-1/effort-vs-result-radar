import json
from pathlib import Path


def test_committed_data_files_are_labeled_empty_fixtures():
    radar = json.loads(Path("public/data/radar.json").read_text(encoding="utf-8"))
    history = json.loads(Path("public/data/history_results.json").read_text(encoding="utf-8"))
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


def test_repository_has_no_ui_files():
    root = Path(".")
    banned = {".html", ".css", ".tsx", ".jsx"}
    found = [
        path
        for path in root.rglob("*")
        if path.suffix in banned and ".git" not in path.parts and ".venv" not in path.parts
    ]
    assert found == []
