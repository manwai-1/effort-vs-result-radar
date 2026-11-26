"""Load watchlist.json. Market is a field on each symbol; it is not inferred."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from scanner.models import MARKETS, ScanError

TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,20}$")


def load_watchlist(path: Path) -> list[dict[str, Any]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ScanError(f"watchlist not found: {path}", 2) from exc
    except json.JSONDecodeError as exc:
        raise ScanError(f"watchlist is not valid JSON: {path}", 2) from exc
    symbols = document.get("symbols") if isinstance(document, dict) else None
    if not isinstance(symbols, list) or not symbols:
        raise ScanError("watchlist.symbols must be a non-empty array", 2)
    cleaned: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, entry in enumerate(symbols):
        if not isinstance(entry, dict):
            raise ScanError(f"watchlist.symbols[{index}] must be an object", 2)
        ticker = entry.get("ticker")
        market = entry.get("market")
        if not isinstance(ticker, str) or not TICKER_RE.fullmatch(ticker):
            raise ScanError(f"watchlist.symbols[{index}].ticker is missing or not a Yahoo-style symbol", 2)
        if market not in MARKETS:
            raise ScanError(f"watchlist.symbols[{index}].market must be US or HK", 2)
        if market == "HK" and not ticker.endswith(".HK"):
            raise ScanError(f"{ticker} is marked HK but the scanner symbol must end in .HK", 2)
        if market == "US" and ticker.endswith(".HK"):
            raise ScanError(f"{ticker} is marked US but uses an HK suffix", 2)
        if ticker in seen:
            raise ScanError(f"duplicate watchlist ticker {ticker}", 2)
        seen.add(ticker)
        cleaned.append({"ticker": ticker, "market": market, "name": entry.get("name")})
    return cleaned
