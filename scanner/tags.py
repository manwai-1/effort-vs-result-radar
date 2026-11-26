"""Bargaining-power tags. Labels are the DESIGN.md contract strings."""

from __future__ import annotations

from typing import Any

TAG_BY_TREND = {
    "down": "buyer_absorption",
    "up": "seller_distribution",
    "sideways": "stalemate_compression",
}

LABELS = {
    "buyer_absorption": ("Buyer Absorption", "買方暗中承接"),
    "seller_distribution": ("Seller Distribution", "賣方暗中出貨"),
    "stalemate_compression": ("Stalemate / Compression", "多空角力壓縮"),
}

TAG_ORDER = (
    "buyer_absorption",
    "seller_distribution",
    "stalemate_compression",
)

STALEMATE_HIT_RATE_LABEL = "不適用"


def assign_tag(is_anomaly: bool, trend_20d: str) -> dict[str, Any]:
    """Anomalies receive one tag. Everything else keeps null tag fields."""

    if not is_anomaly:
        return {
            "bargaining_power": None,
            "bargaining_power_label_en": None,
            "bargaining_power_label_zh": None,
        }
    key = TAG_BY_TREND[trend_20d]
    english, chinese = LABELS[key]
    return {
        "bargaining_power": key,
        "bargaining_power_label_en": english,
        "bargaining_power_label_zh": chinese,
    }
