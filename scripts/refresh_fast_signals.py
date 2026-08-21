"""Refresh recent headlines and fast signals without recalculating the research model."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from collect_market_data import collect_news
from fast_signal_core import build_signal


ROOT = Path(__file__).resolve().parents[1]
TICKER_FILE = ROOT / "data" / "tickers.json"
MARKET_FILE = ROOT / "public" / "data" / "market.json"
OUTPUT_FILE = ROOT / "public" / "data" / "fast_signals.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def comparable(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "generatedAt"}


def load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def monitored_tickers() -> list[dict[str, Any]]:
    configured = {symbol.strip().upper() for symbol in os.getenv("FAST_NEWS_SYMBOLS", "").split(",") if symbol.strip()}
    catalog = load_json(TICKER_FILE, [])
    if configured:
        return [item for item in catalog if item.get("ticker") in configured]

    market = load_json(MARKET_FILE, {})
    available = set(market.get("stocks", {}).keys())
    if available:
        return [item for item in catalog if item.get("ticker") in available]
    return [item for item in catalog if item.get("ticker") != "SPY"][:12]


def main() -> None:
    previous = load_json(OUTPUT_FILE, {})
    previous_stocks = previous.get("stocks", {}) if isinstance(previous, dict) else {}
    observed_at = now_iso()
    stocks: dict[str, Any] = {}
    errors: dict[str, str] = {}

    for meta in monitored_tickers():
        ticker = str(meta["ticker"])
        try:
            items, score = collect_news(ticker, str(meta["name"]))
            unavailable = len(items) == 1 and items[0].get("source") == "Pipeline"
            if unavailable and ticker in previous_stocks:
                stocks[ticker] = previous_stocks[ticker]
                errors[ticker] = "Sin titulares nuevos; se conserva la última señal válida."
            else:
                stocks[ticker] = build_signal(ticker, items, score, previous_stocks.get(ticker), observed_at)
        except Exception as exc:  # noqa: BLE001
            if ticker in previous_stocks:
                stocks[ticker] = previous_stocks[ticker]
            errors[ticker] = f"{type(exc).__name__}: {str(exc)[:140]}"
        time.sleep(.12)

    if not stocks:
        raise RuntimeError("No se pudo generar ninguna señal rápida.")

    payload = {
        "generatedAt": observed_at,
        "mode": "live",
        "refreshIntervalMinutes": 20,
        "policy": "Vigilancia rápida independiente: detecta eventos y urgencia, pero no modifica el score oficial hasta el pipeline diario.",
        "stocks": stocks,
        "errors": errors,
    }
    if previous and comparable(previous) == comparable(payload):
        print(f"Sin cambios en {len(stocks)} activos; no se reescribe el artefacto.")
        return

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(OUTPUT_FILE)
    print(f"Señales rápidas actualizadas para {len(stocks)} activos; errores conservados: {len(errors)}.")


if __name__ == "__main__":
    main()
