"""Measure post-news abnormal returns without pretending pending windows exist."""

from __future__ import annotations

import json
import re
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MARKET_FILE = ROOT / "public" / "data" / "market.json"
PRICE_FILE = ROOT / "research_work" / "prices.json"
OUTPUT_FILE = ROOT / "public" / "data" / "event_studies.json"


def parse_date(value: str) -> pd.Timestamp | None:
    try:
        parsed = parsedate_to_datetime(value)
        return pd.Timestamp(parsed).tz_localize(None) if parsed.tzinfo is None else pd.Timestamp(parsed).tz_convert(None)
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = pd.to_datetime(value, utc=True)
            return pd.Timestamp(parsed).tz_convert(None)
        except (TypeError, ValueError):
            return None


def token_set(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def similarity(left: str, right: str) -> float:
    a, b = token_set(left), token_set(right)
    return len(a & b) / len(a | b) if a | b else 0.0


def load_prices() -> dict[str, pd.Series]:
    payload = json.loads(PRICE_FILE.read_text(encoding="utf-8"))
    return {
        ticker: pd.Series(values["close"], index=pd.to_datetime(values["dates"]), dtype=float).sort_index()
        for ticker, values in payload["prices"].items()
    }


def abnormal_return(asset: pd.Series, spy: pd.Series, event: pd.Timestamp, sessions: int) -> float | None:
    common = pd.concat({"asset": asset, "spy": spy}, axis=1).dropna().sort_index()
    future = common[common.index >= event.normalize()]
    if len(future) <= sessions:
        return None
    start = future.iloc[0]
    end = future.iloc[sessions]
    return float((end["asset"] / start["asset"] - 1) - (end["spy"] / start["spy"] - 1))


def main() -> None:
    market = json.loads(MARKET_FILE.read_text(encoding="utf-8"))
    prices = load_prices()
    spy = prices.get("SPY")
    if spy is None:
        raise RuntimeError("SPY es obligatorio para el event study")
    items: list[dict[str, object]] = []
    for ticker, stock in market.get("stocks", {}).items():
        if ticker not in prices:
            continue
        previous_titles: list[str] = []
        company_tokens = token_set(f"{ticker} {stock.get('name', '')}")
        for news in stock.get("news", []):
            title = str(news.get("title", ""))
            published = str(news.get("publishedAt", ""))
            event_date = parse_date(published)
            title_tokens = token_set(title)
            entity_match = bool(company_tokens & title_tokens) or bool(news.get("entityMatched", False))
            relevance = float(news.get("relevance", min(1.0, .35 + .15 * len(company_tokens & title_tokens))))
            novelty = float(news.get("novelty", 1 - max((similarity(title, other) for other in previous_titles), default=0)))
            previous_titles.append(title)
            windows = {sessions: abnormal_return(prices[ticker], spy, event_date, sessions) if event_date is not None else None for sessions in (1, 5, 20)}
            measured = sum(value is not None for value in windows.values())
            status = "measured" if measured else "pending" if event_date is not None else "unavailable"
            items.append({
                "ticker": ticker,
                "title": title,
                "source": str(news.get("source", "Fuente no disponible")),
                "publishedAt": published,
                "eventType": str(news.get("eventType", "mercado")),
                "sentiment": str(news.get("sentiment", "neutral")),
                "relevance": round(relevance, 4),
                "novelty": round(novelty, 4),
                "entityMatched": entity_match,
                "abnormalReturn1d": None if windows[1] is None else round(windows[1], 6),
                "abnormalReturn5d": None if windows[5] is None else round(windows[5], 6),
                "abnormalReturn20d": None if windows[20] is None else round(windows[20], 6),
                "status": status,
            })
    measured_count = sum(item["status"] == "measured" for item in items)
    output = {
        "generatedAt": pd.Timestamp.utcnow().isoformat(),
        "mode": "live",
        "benchmark": "SPY",
        "methodology": "Retorno del activo menos retorno de SPY en 1, 5 y 20 sesiones posteriores; una ventana sin datos permanece pendiente.",
        "coverage": round(measured_count / len(items) * 100, 2) if items else 0,
        "items": items,
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Event study: {len(items)} eventos, {measured_count} con al menos una ventana medida.")


if __name__ == "__main__":
    main()
