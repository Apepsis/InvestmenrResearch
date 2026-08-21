"""Pure helpers for the fast-news pipeline; intentionally network independent."""

from __future__ import annotations

import hashlib
from typing import Any


def fingerprint(item: dict[str, Any]) -> str:
    identity = f"{item.get('title', '').strip().lower()}|{item.get('url', '').strip()}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]


def build_signal(ticker: str, items: list[dict[str, Any]], score: float, previous: dict[str, Any] | None, observed_at: str) -> dict[str, Any]:
    prior_seen = {
        str(item.get("id")): str(item.get("firstSeenAt"))
        for item in (previous or {}).get("items", [])
        if item.get("id") and item.get("firstSeenAt")
    }
    enriched: list[dict[str, Any]] = []
    for item in items:
        item_id = fingerprint(item)
        enriched.append({
            **item,
            "id": item_id,
            "firstSeenAt": prior_seen.get(item_id, observed_at),
        })

    impacts = [abs(float(item.get("impactWeight", 0) or 0)) for item in enriched]
    strongest = max(impacts, default=0)
    high_confidence_event = any(
        bool(item.get("entityMatched"))
        and float(item.get("relevance", 0) or 0) >= .65
        and float(item.get("confidence", 0) or 0) >= .58
        and abs(float(item.get("impactWeight", 0) or 0)) >= .20
        for item in enriched
    )
    urgency = "high" if high_confidence_event or strongest >= .32 else "medium" if strongest >= .14 else "low"
    signal = "positive" if score >= 56 else "negative" if score <= 44 else "neutral"
    return {
        "ticker": ticker,
        "newsScore": round(float(score), 1),
        "signal": signal,
        "urgency": urgency,
        "signalStrength": round(min(100.0, abs(float(score) - 50) * 2), 1),
        "items": enriched,
    }
