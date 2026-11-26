"""Check scanner documents before they replace files on disk."""

from __future__ import annotations

import math
from typing import Any

from scanner.ledger import summarize
from scanner.models import (
    ANOMALY_DISPLACEMENT_MAX,
    ANOMALY_RVOL_MIN,
    DISPLACEMENT_FLOOR,
    RETURN_FIELDS,
    ScanError,
)
from scanner.numbers import METRIC_DP, round_dp
from scanner.tags import LABELS, STALEMATE_HIT_RATE_LABEL, TAG_BY_TREND, TAG_ORDER

RADAR_POINT_FIELDS = (
    "ticker",
    "market",
    "rvol",
    "displacement",
    "anomaly_score",
    "is_anomaly",
    "trend_20d",
    "bargaining_power",
    "bargaining_power_label_en",
    "bargaining_power_label_zh",
    "last_price",
    "currency",
)


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def validate_radar(document: dict[str, Any]) -> None:
    if not isinstance(document.get("generated_at"), str) or not document["generated_at"]:
        raise ScanError("radar.generated_at must be a non-empty ISO-8601 string", 2)
    universe = document.get("universe")
    if not isinstance(universe, dict):
        raise ScanError("radar.universe must be an object", 2)
    points = document.get("points")
    if not isinstance(points, list):
        raise ScanError("radar.points must be an array", 2)
    us_count = sum(1 for point in points if point.get("market") == "US")
    hk_count = sum(1 for point in points if point.get("market") == "HK")
    if universe.get("us_count") != us_count or universe.get("hk_count") != hk_count:
        raise ScanError("radar.universe counts must match the points written for each market", 2)
    for index, point in enumerate(points):
        for field in RADAR_POINT_FIELDS:
            if field not in point:
                raise ScanError(f"radar.points[{index}] missing {field}", 2)
        if point["market"] not in ("US", "HK"):
            raise ScanError(f"radar.points[{index}].market must be US or HK", 2)
        for field in ("rvol", "displacement", "anomaly_score", "last_price"):
            if not _finite(point[field]):
                raise ScanError(f"radar.points[{index}].{field} must be a finite number", 2)
        if point["trend_20d"] not in TAG_BY_TREND:
            raise ScanError(f"radar.points[{index}].trend_20d is invalid", 2)
        expected_score = round_dp(
            float(point["rvol"]) / max(float(point["displacement"]), DISPLACEMENT_FLOOR),
            METRIC_DP,
        )
        if point["anomaly_score"] != expected_score:
            raise ScanError(f"radar.points[{index}].anomaly_score does not match RVOL and displacement", 2)
        expected_flag = (
            float(point["rvol"]) >= ANOMALY_RVOL_MIN
            and float(point["displacement"]) <= ANOMALY_DISPLACEMENT_MAX
        )
        if bool(point["is_anomaly"]) != expected_flag:
            raise ScanError(f"radar.points[{index}].is_anomaly does not match the threshold rule", 2)
        if point["is_anomaly"]:
            expected = TAG_BY_TREND[point["trend_20d"]]
            english, chinese = LABELS[expected]
            if point["bargaining_power"] != expected:
                raise ScanError(f"radar.points[{index}] tag does not match trend", 2)
            if point["bargaining_power_label_en"] != english or point["bargaining_power_label_zh"] != chinese:
                raise ScanError(f"radar.points[{index}] labels do not match the contract", 2)
        else:
            if any(point[field] is not None for field in (
                "bargaining_power",
                "bargaining_power_label_en",
                "bargaining_power_label_zh",
            )):
                raise ScanError(f"radar.points[{index}] non-anomaly must have null tag fields", 2)
        currency = point["currency"]
        if point["market"] == "US" and currency != "USD":
            raise ScanError(f"radar.points[{index}] US currency must be USD", 2)
        if point["market"] == "HK" and currency != "HKD":
            raise ScanError(f"radar.points[{index}] HK currency must be HKD", 2)


def validate_history(document: dict[str, Any]) -> None:
    if "updated_at" in document and document["updated_at"] is not None:
        if not isinstance(document["updated_at"], str):
            raise ScanError("history.updated_at must be a string when present", 2)
    records = document.get("records")
    if not isinstance(records, list):
        raise ScanError("history.records must be an array", 2)
    seen: set[tuple[str, str]] = set()
    for index, record in enumerate(records):
        for field in (
            "date",
            "ticker",
            "market",
            "signal_price",
            "rvol",
            "displacement",
            "anomaly_score",
            "bargaining_power",
            "bargaining_power_label_en",
            "bargaining_power_label_zh",
            *RETURN_FIELDS,
        ):
            if field not in record:
                raise ScanError(f"history.records[{index}] missing {field}", 2)
        key = (record["date"], record["ticker"])
        if key in seen:
            raise ScanError(f"history duplicate {key}", 2)
        seen.add(key)
        tag = record["bargaining_power"]
        if tag not in TAG_ORDER:
            raise ScanError(f"history.records[{index}].bargaining_power must be one of the three tags", 2)
        english, chinese = LABELS[tag]
        if record["bargaining_power_label_en"] != english or record["bargaining_power_label_zh"] != chinese:
            raise ScanError(f"history.records[{index}] labels do not match the contract", 2)
        for field in ("signal_price", "rvol", "displacement", "anomaly_score"):
            if not _finite(record[field]):
                raise ScanError(f"history.records[{index}].{field} must be a finite number", 2)
        for field in RETURN_FIELDS:
            value = record[field]
            if value is not None and not _finite(value):
                raise ScanError(f"history.records[{index}].{field} must be a number or null", 2)
    if document.get("summary_by_tag") != summarize(records):
        raise ScanError("history.summary_by_tag does not match the records under the §4.1 rules", 2)
    summary = document["summary_by_tag"]
    if [entry["bargaining_power"] for entry in summary] != list(TAG_ORDER):
        raise ScanError("history.summary_by_tag must list the three tags in contract order", 2)
    for entry in summary:
        for horizon in (3, 5, 10):
            block = entry[f"t_plus_{horizon}"]
            if entry["bargaining_power"] == "stalemate_compression":
                if block["hit_rate_applicable"] is not False or block["hit_rate_pct"] is not None:
                    raise ScanError("stalemate hit rate must be 不適用, not a number", 2)
                if block["hit_rate_label"] != STALEMATE_HIT_RATE_LABEL:
                    raise ScanError("stalemate hit_rate_label must be 不適用", 2)
            elif block["hit_rate_applicable"] is not True or block["hit_rate_label"] is not None:
                raise ScanError("directional tags must keep a numeric hit-rate rule", 2)
