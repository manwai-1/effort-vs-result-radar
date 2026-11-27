"""Command line entry for the scanner."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from scanner.models import ScanError
from scanner.publish import publish_allowed
from scanner.run import RunConfig, default_now, run


def parse_now(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ScanError("--now must be ISO-8601 with an offset, for example 2026-11-27T15:00:00-05:00", 2) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ScanError("--now must include a timezone offset", 2)
    return parsed


def repo_root_from(start: Path) -> Path:
    completed = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise ScanError("could not find the git repository root for --push", 4)
    return Path(completed.stdout.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scanner",
        description=(
            "Deterministic Effort vs Result Radar scan. "
            "Reads watchlist.json, writes public/data/radar.json and "
            "public/data/history_results.json. Does not call an AI model."
        ),
    )
    parser.add_argument("--watchlist", type=Path, default=Path("watchlist.json"))
    parser.add_argument("--radar", type=Path, default=Path("public/data/radar.json"))
    parser.add_argument("--history", type=Path, default=Path("public/data/history_results.json"))
    parser.add_argument(
        "--now",
        help="Override the clock with an ISO-8601 timestamp that includes an offset. For tests and fixtures.",
    )
    parser.add_argument(
        "--bars",
        type=Path,
        help="Read daily bars from a fixture JSON file instead of yfinance. Cannot be combined with --push.",
    )
    parser.add_argument(
        "--scheduled",
        action="store_true",
        help=(
            "Scheduled GitHub Actions run. An open market refreshes the live radar "
            "from the partial daily bar. A market in its post-close window "
            "(16:20 local until the local date changes) is a full scan of that "
            "completed session: radar.json is rewritten with the official close "
            "and full-day volume, and only that market's same-day ledger rows are "
            "finalized. When neither is true, do not rewrite radar.json. "
            "Backfill completed T+N returns only."
        ),
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Commit and push the JSON files. Allowed only inside GitHub Actions, and never with --bars.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.push:
            publish_allowed(fixture_mode=args.bars is not None)
        now = parse_now(args.now) if args.now else default_now()
        root = repo_root_from(Path.cwd()) if args.push else None
        config = RunConfig(
            watchlist_path=args.watchlist,
            radar_path=args.radar,
            history_path=args.history,
            now=now,
            scheduled=args.scheduled,
            bars_path=args.bars,
            push=args.push,
            repo_root=root,
        )
        return run(config)
    except ScanError as exc:
        print(str(exc), file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
