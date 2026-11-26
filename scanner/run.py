"""One scanner pass: read the watchlist, measure, write JSON."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from scanner.fetch import FixtureSource, YFinanceSource, load_fixture_bars
from scanner.hours import market_local, open_markets
from scanner.ledger import (
    append_anomalies,
    apply_backfill,
    build_history_document,
    history_fetch_start,
)
from scanner.models import ScanError
from scanner.publish import git_publish, publish_allowed
from scanner.snapshot import anomalies_from_points, build_points, build_radar, measurement_dates
from scanner.storage import dump_json, load_history_records
from scanner.validate import validate_history, validate_radar
from scanner.watchlist import load_watchlist

PUBLISH_MESSAGE = (
    "scan: update radar and history ledger\n\n"
    "Automated market scan. No AI. Prices come from yfinance daily bars."
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_COMMITTED_OUTPUTS = {
    _REPO_ROOT / "public" / "data" / "radar.json",
    _REPO_ROOT / "public" / "data" / "history_results.json",
}


@dataclass
class RunConfig:
    watchlist_path: Path
    radar_path: Path
    history_path: Path
    now: datetime
    scheduled: bool
    bars_path: Path | None
    push: bool
    repo_root: Path | None = None


def _latest_market_date(symbols: list[dict], now: datetime) -> date:
    dates = [market_local(now, symbol["market"]).date() for symbol in symbols]
    return max(dates) if dates else now.date()


def _reject_fixture_write_into_committed_data(config: RunConfig) -> None:
    if config.bars_path is None:
        return
    banned = {path.resolve() for path in _COMMITTED_OUTPUTS}
    for path in (config.radar_path, config.history_path):
        if path.resolve() in banned:
            raise ScanError(
                "Refusing to write fixture bars into public/data. "
                "Pass --radar and --history outside that directory. "
                "Fixture numbers must not replace the committed empty ledger.",
                2,
            )


def run(config: RunConfig) -> int:
    if config.now.tzinfo is None or config.now.utcoffset() is None:
        raise ScanError("--now must be timezone-aware (ISO-8601 with an offset)", 2)
    _reject_fixture_write_into_committed_data(config)
    if config.push:
        publish_allowed(fixture_mode=config.bars_path is not None)

    symbols = load_watchlist(config.watchlist_path)
    markets = open_markets(config.now)
    records = load_history_records(config.history_path)
    backfill_only = config.scheduled and not markets

    if backfill_only:
        pending = [
            record["ticker"]
            for record in records
            if record.get("t_plus_3_return_pct") is None
            or record.get("t_plus_5_return_pct") is None
            or record.get("t_plus_10_return_pct") is None
        ]
        if not pending:
            print(
                "scheduled run: both US and HK regular sessions are closed; "
                "no pending T+N returns; radar.json and history_results.json unchanged"
            )
            return 0
        source = _source(config)
        start = history_fetch_start(records, _latest_market_date(symbols, config.now))
        bars = source.fetch(sorted(set(pending)), start)
        filled = apply_backfill(records, bars, config.now)
        if filled == 0:
            print(
                "scheduled run: both markets closed; backfill checked real bars and "
                "found no completed T+N session to write; files unchanged"
            )
            return 0
        document = build_history_document(records, config.now)
        validate_history(document)
        dump_json(document, config.history_path)
        print(
            f"scheduled run: both markets closed; radar.json unchanged; "
            f"backfilled {filled} ledger row(s) from completed sessions"
        )
        _maybe_publish(config)
        return 0

    source = _source(config)
    start = history_fetch_start(records, _latest_market_date(symbols, config.now))
    bars = source.fetch([symbol["ticker"] for symbol in symbols], start)
    points, skipped = build_points(symbols, bars, config.now)
    for line in skipped:
        print(f"skip {line}", file=sys.stderr)
    if not points:
        raise ScanError(
            "no points could be measured; leaving radar.json and history_results.json unchanged",
            3,
        )
    radar = build_radar(points, config.now)
    validate_radar(radar)
    dates = measurement_dates(symbols, bars, config.now)
    added = append_anomalies(records, anomalies_from_points(points, dates))
    filled = apply_backfill(records, bars, config.now)
    history = build_history_document(records, config.now)
    validate_history(history)
    dump_json(radar, config.radar_path)
    dump_json(history, config.history_path)
    open_label = ",".join(markets) if markets else "none (manual run; latest real bars)"
    print(
        f"scan wrote {len(points)} points "
        f"({radar['universe']['us_count']} US, {radar['universe']['hk_count']} HK); "
        f"open={open_label}; new ledger rows={added}; backfilled rows={filled}; "
        f"skipped={len(skipped)}"
    )
    _maybe_publish(config)
    return 0


def _source(config: RunConfig) -> FixtureSource | YFinanceSource:
    if config.bars_path is not None:
        return FixtureSource(load_fixture_bars(config.bars_path))
    return YFinanceSource()


def _maybe_publish(config: RunConfig) -> None:
    if not config.push:
        return
    root = config.repo_root
    if root is None:
        raise ScanError("internal: repo root missing for --push", 4)
    paths = [path for path in (config.radar_path, config.history_path) if path.exists()]
    if not paths:
        raise ScanError("refusing to publish: scanner output files are missing", 4)
    git_publish(root, paths, PUBLISH_MESSAGE)


def default_now() -> datetime:
    return datetime.now(timezone.utc)
