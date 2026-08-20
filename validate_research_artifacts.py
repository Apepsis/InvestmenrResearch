"""Validate public research artifacts before GitHub Pages can publish them."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"


def load(name: str) -> dict[str, Any]:
    path = DATA / name
    if not path.exists():
        raise ValueError(f"Falta {name}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    json.dumps(payload, allow_nan=False)
    return payload


def finite(value: object, label: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} no es finito")
    return number


def validate_backtest(payload: dict[str, Any]) -> None:
    if payload.get("mode") != "live":
        raise ValueError("backtest debe ser live")
    if payload.get("horizonSessions") != 60:
        raise ValueError("horizonte inesperado")
    if len(payload.get("equity", [])) < 4:
        raise ValueError("backtest insuficiente")
    for name in ("spy", "technical", "heuristic", "statistical"):
        metric = payload.get("metrics", {}).get(name)
        if not metric:
            raise ValueError(f"falta métrica {name}")
        for key in ("totalReturn", "cagr", "sharpe", "sortino", "maxDrawdown", "volatility", "hitRate", "alpha", "beta"):
            finite(metric[key], f"{name}.{key}")
    for split in payload.get("methodology", {}).get("splits", []):
        if not split["trainEnd"] < split["calibrationStart"] <= split["calibrationEnd"] < split["testStart"]:
            raise ValueError(f"posible leakage temporal en {split}")


def validate_risk(payload: dict[str, Any]) -> None:
    tickers = payload.get("tickers", [])
    if "SPY" not in tickers or len(tickers) < 3:
        raise ValueError("modelo de riesgo sin benchmark o cobertura")
    for row in tickers:
        if len(payload["dailyReturns"].get(row, [])) < 60:
            raise ValueError(f"{row}: retornos insuficientes")
        for column in tickers:
            left = finite(payload["correlation"][row][column], f"corr {row}/{column}")
            right = finite(payload["correlation"][column][row], f"corr {column}/{row}")
            if abs(left - right) > 1e-5:
                raise ValueError("matriz de correlación no simétrica")


def validate_events(payload: dict[str, Any]) -> None:
    if payload.get("benchmark") != "SPY":
        raise ValueError("event study sin benchmark SPY")
    for item in payload.get("items", []):
        if item.get("status") not in {"measured", "pending", "unavailable"}:
            raise ValueError("estado de evento inválido")
        for key in ("relevance", "novelty"):
            value = finite(item[key], key)
            if not 0 <= value <= 1:
                raise ValueError(f"{key} fuera de rango")


def main() -> None:
    validate_backtest(load("backtest.json"))
    validate_risk(load("risk_model.json"))
    validate_events(load("event_studies.json"))
    print("Artefactos de investigación válidos.")


if __name__ == "__main__":
    main()
