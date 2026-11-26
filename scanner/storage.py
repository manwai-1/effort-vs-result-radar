"""Atomic JSON IO for the two public data files."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from scanner.models import RETURN_FIELDS, ScanError
from scanner.validate import validate_history


def dump_json(document: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, path)


def load_history_records(path: Path) -> list[dict[str, Any]]:
    """Load ledger rows. An empty committed fixture is not a live ledger."""

    if not path.exists():
        return []
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScanError(f"history file is not valid JSON: {path}", 2) from exc
    if not isinstance(document, dict):
        raise ScanError("history file must be a JSON object", 2)
    records = document.get("records", [])
    if not isinstance(records, list):
        raise ScanError("history.records must be an array", 2)
    if document.get("data_status") == "empty_fixture":
        if records:
            raise ScanError(
                "history file is labeled empty_fixture but contains records; refusing to treat it as live performance",
                2,
            )
        return []
    validate_history(document)
    for record in records:
        for field in RETURN_FIELDS:
            record.setdefault(field, None)
    return records
