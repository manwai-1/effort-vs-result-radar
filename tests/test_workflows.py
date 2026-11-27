from pathlib import Path


def test_scan_workflow_covers_both_sessions_and_lunch_without_a_fixed_us_offset():
    text = Path(".github/workflows/scan.yml").read_text(encoding="utf-8")
    assert 'cron: "30 1 * * 1-5"' in text
    assert 'cron: "*/30 2-7 * * 1-5"' in text
    assert 'cron: "20 8 * * 1-5"' in text
    assert 'cron: "30 13 * * 1-5"' in text
    assert 'cron: "*/30 14-20 * * 1-5"' in text
    assert 'cron: "20 20 * * 1-5"' in text
    assert 'cron: "20 21 * * 1-5"' in text
    assert "16:20" in text
    assert "workflow_dispatch" in text
    assert "--scheduled" in text
    assert "--push" in text
    assert "America/New_York" in text
    assert "lunch" in text.lower()
    for closed in ('cron: "0 8 * * 1-5"', 'cron: "0 21 * * 1-5"', 'cron: "* * * * *"'):
        assert closed not in text


def test_ci_workflow_does_not_call_the_scanner():
    text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "pytest" in text
    assert "workflow_dispatch" not in text
    assert "--push" not in text
    assert "yfinance" not in text
