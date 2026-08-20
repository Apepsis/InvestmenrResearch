"""Fail fast if a generated market file is incomplete or unsafe to publish."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path


def validate(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("mode") != "live":
        raise ValueError("mode debe ser live")
    if not data.get("generatedAt"):
        raise ValueError("generatedAt es obligatorio")
    stocks = data.get("stocks")
    if not isinstance(stocks, dict) or not stocks:
        raise ValueError("stocks no puede estar vacio")
    required = {"ticker", "name", "price", "score", "scores", "history", "technical", "fundamental", "news", "trace", "explanation"}
    for symbol, stock in stocks.items():
        missing = required - set(stock)
        if missing:
            raise ValueError(f"{symbol}: faltan {sorted(missing)}")
        for key in ("price", "score"):
            if not isinstance(stock[key], (int, float)) or not math.isfinite(stock[key]):
                raise ValueError(f"{symbol}: {key} invalido")
        if not 0 <= stock["score"] <= 100:
            raise ValueError(f"{symbol}: score fuera de rango")
        if len(stock["history"]) < 8:
            raise ValueError(f"{symbol}: historia insuficiente")
        explanation = stock["explanation"]
        contribution_total = float(explanation["base"]) + sum(float(item["contribution"]) for item in explanation["contributions"])
        if abs(contribution_total - float(explanation["result"])) > 0.05:
            raise ValueError(f"{symbol}: explicación no reconcilia con el score")
        interval = explanation["interval"]
        if not 0 <= float(interval["low"]) <= float(interval["high"]) <= 100:
            raise ValueError(f"{symbol}: intervalo inválido")
    serialized = json.dumps(data, allow_nan=False)
    if "API_KEY" in serialized or "PRIVATE KEY" in serialized:
        raise ValueError("El archivo contiene una posible credencial")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).resolve().parents[1] / "public" / "data" / "market.json"
    validate(path)
    print("Archivo de mercado valido.")
