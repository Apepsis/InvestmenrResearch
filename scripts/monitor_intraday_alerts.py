"""Monitor fresh Alpaca quotes and send deduplicated intraday Gmail alerts.

This process is intentionally lightweight: it does not retrain the model or
rewrite published predictions. It compares fresh quotes with the last audited
daily dataset and combines that move with the latest 5/20/60-session forecast.
The script writes ``alerts.json`` only after a digest is sent, avoiding a Git
commit every five minutes.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from send_alerts import pending_after_cooldown, send_digest
from v5_core import alert_fingerprint


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
ALERTS_FILE = DATA / "alerts.json"
MAX_QUOTE_AGE_MINUTES = 20.0


def parse_time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def fresh_price(quote: dict[str, Any], now: datetime, maximum_age_minutes: float = MAX_QUOTE_AGE_MINUTES) -> float | None:
    timestamp = parse_time(str(quote.get("asOf", "")))
    try:
        price = float(quote.get("price"))
    except (TypeError, ValueError):
        return None
    if timestamp is None or price <= 0:
        return None
    age_minutes = max(0.0, (now - timestamp).total_seconds() / 60)
    return price if age_minutes <= maximum_age_minutes else None


def predictions_by_ticker(live: dict[str, Any]) -> dict[str, dict[int, dict[str, Any]]]:
    output: dict[str, dict[int, dict[str, Any]]] = {}
    for prediction in live.get("predictions", []):
        try:
            ticker = str(prediction["ticker"]).upper()
            horizon = int(prediction["horizonSessions"])
        except (KeyError, TypeError, ValueError):
            continue
        output.setdefault(ticker, {})[horizon] = prediction
    return output


def build_intraday_candidates(
    market: dict[str, Any],
    live: dict[str, Any],
    quote_payload: dict[str, Any],
    now: datetime,
) -> list[dict[str, Any]]:
    """Build conservative price alerts without changing the daily model."""
    stocks = market.get("stocks", {})
    forecasts = predictions_by_ticker(live)
    candidates: list[dict[str, Any]] = []

    for ticker, quote in quote_payload.get("quotes", {}).items():
        symbol = str(ticker).upper()
        current = fresh_price(quote, now)
        stock = stocks.get(symbol, {})
        try:
            reference = float(stock.get("price"))
        except (TypeError, ValueError):
            continue
        if current is None or reference <= 0:
            continue
        change = current / reference - 1
        move_text = f"{change * 100:+.2f}% desde la referencia diaria ({reference:.2f} → {current:.2f} USD)."

        if symbol == "SPY":
            if change <= -0.03:
                candidates.append({
                    "fingerprint": alert_fingerprint("intraday_market_shock", symbol),
                    "code": "intraday_market_shock",
                    "severity": "critical",
                    "ticker": symbol,
                    "title": "Shock intradía del mercado",
                    "message": f"SPY registra {move_text} Revisar exposición, correlaciones y límites de riesgo.",
                    "cooldownHours": 4,
                    "observedPrice": round(current, 6),
                    "referencePrice": round(reference, 6),
                    "change": round(change, 8),
                })
            continue

        horizons = forecasts.get(symbol, {})
        short, medium, long = horizons.get(5), horizons.get(20), horizons.get(60)

        if change <= -0.06:
            candidates.append({
                "fingerprint": alert_fingerprint("intraday_price_drop", symbol),
                "code": "intraday_price_drop",
                "severity": "critical",
                "ticker": symbol,
                "title": f"Caída extraordinaria para revisar: {symbol}",
                "message": f"{symbol} registra {move_text} Esto no es una orden de venta; comprobar noticia, liquidez y tesis.",
                "cooldownHours": 4,
                "observedPrice": round(current, 6),
                "referencePrice": round(reference, 6),
                "change": round(change, 8),
            })
        elif change >= 0.08:
            candidates.append({
                "fingerprint": alert_fingerprint("intraday_price_surge", symbol),
                "code": "intraday_price_surge",
                "severity": "warning",
                "ticker": symbol,
                "title": f"Subida extraordinaria para revisar: {symbol}",
                "message": f"{symbol} registra {move_text} Comprobar si existe evento material y riesgo de reversión.",
                "cooldownHours": 4,
                "observedPrice": round(current, 6),
                "referencePrice": round(reference, 6),
                "change": round(change, 8),
            })

        strong_medium = medium and float(medium.get("probability", 0)) >= 0.66
        strong_long = long and float(long.get("probability", 0)) >= 0.60
        uncertainty_floor = medium and float(medium.get("uncertainty", {}).get("low", 0)) >= 0.50
        if change <= -0.035 and strong_medium and strong_long and uncertainty_floor:
            candidates.append({
                "fingerprint": alert_fingerprint("intraday_research_opportunity", symbol),
                "code": "intraday_research_opportunity",
                "severity": "opportunity",
                "ticker": symbol,
                "title": f"Dislocación para investigar: {symbol}",
                "message": (
                    f"{symbol} registra {move_text} La predicción diaria todavía muestra "
                    f"{float(medium['probability']) * 100:.1f}% a 20 sesiones y "
                    f"{float(long['probability']) * 100:.1f}% a 60. Recalcular evidencia antes de decidir."
                ),
                "cooldownHours": 24,
                "observedPrice": round(current, 6),
                "referencePrice": round(reference, 6),
                "change": round(change, 8),
            })
        elif change <= -0.04 and (
            (short and float(short.get("probability", 1)) <= 0.35)
            or (medium and float(medium.get("probability", 1)) <= 0.45)
        ):
            candidates.append({
                "fingerprint": alert_fingerprint("intraday_thesis_risk", symbol),
                "code": "intraday_thesis_risk",
                "severity": "warning",
                "ticker": symbol,
                "title": f"Riesgo de tesis para revisar: {symbol}",
                "message": f"{symbol} registra {move_text} El modelo diario no muestra fortaleza suficiente en horizontes cortos.",
                "cooldownHours": 8,
                "observedPrice": round(current, 6),
                "referencePrice": round(reference, 6),
                "change": round(change, 8),
            })

    order = {"critical": 0, "warning": 1, "opportunity": 2, "info": 3}
    return sorted(candidates, key=lambda item: (order.get(str(item["severity"]), 9), -abs(float(item.get("change", 0)))))[:8]


def get_quotes(api_url: str, symbols: list[str]) -> dict[str, Any]:
    query = urlencode({"symbols": ",".join(symbols)})
    request = Request(
        f"{api_url.rstrip('/')}/quotes?{query}",
        headers={"Accept": "application/json", "User-Agent": "InvestmentResearchAgent/5.1"},
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - URL is a configured trusted Worker
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload.get("quotes"), dict):
        raise RuntimeError("El Worker no devolvió un mapa de cotizaciones")
    return payload


def main() -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    api_url = os.getenv("MARKET_API_URL", "").strip()
    if not api_url:
        raise SystemExit("Falta la variable MARKET_API_URL/VITE_MARKET_API_URL")

    market = json.loads((DATA / "market.json").read_text(encoding="utf-8"))
    live = json.loads((DATA / "live_predictions.json").read_text(encoding="utf-8"))
    previous = json.loads(ALERTS_FILE.read_text(encoding="utf-8")) if ALERTS_FILE.exists() else {}
    history = list(previous.get("history", []))
    symbols = sorted(str(value).upper() for value in market.get("stocks", {}).keys())
    quotes = get_quotes(api_url, symbols)
    candidates = build_intraday_candidates(market, live, quotes, now)
    pending = pending_after_cooldown(candidates, history, now)

    if not candidates:
        print("Intraday: cotizaciones recientes; 0 alertas. No se modifica el repositorio.")
        return
    if not pending:
        print(f"Intraday: {len(candidates)} alerta(s), todas dentro del cooldown. No se envía correo.")
        return

    enabled = os.getenv("ALERTS_ENABLED", "").strip().lower() in {"1", "true", "yes", "si", "sí"}
    sender = os.getenv("ALERT_EMAIL_FROM", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").strip().replace(" ", "")
    recipients = [item.strip() for item in os.getenv("ALERT_EMAIL_TO", "").replace(";", ",").split(",") if item.strip()]
    if not enabled:
        print(f"Intraday: {len(pending)} alerta(s) detectadas, pero ALERTS_ENABLED está desactivado.")
        return
    if not sender or not password or not recipients:
        raise SystemExit("Alertas intradía detectadas, pero faltan secretos de Gmail")

    send_digest(sender, recipients, password, pending, now.isoformat())
    history.extend({
        "fingerprint": item["fingerprint"],
        "code": item["code"],
        "ticker": item.get("ticker"),
        "severity": item["severity"],
        "sentAt": now.isoformat(),
        "mode": "intraday",
    } for item in pending)
    output = {
        "generatedAt": now.isoformat(),
        "mode": "intraday",
        "deliveryEnabled": True,
        "deliveryStatus": "sent",
        "deliveryErrorClass": None,
        "newAlertsSent": len(pending),
        "candidates": candidates,
        "pendingAfterCooldown": len(pending),
        "history": history[-500:],
        "quoteSource": str(quotes.get("feed", "Alpaca IEX")),
        "policy": "Monitor de 5 minutos; no reentrena ni ejecuta operaciones. Las señales exigen verificación humana.",
    }
    ALERTS_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Intraday: correo enviado con {len(pending)} alerta(s).")


if __name__ == "__main__":
    main()
