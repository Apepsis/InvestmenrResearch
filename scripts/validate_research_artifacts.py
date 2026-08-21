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
    for name in ("spy", "technical", "heuristic", "statistical", "riskControlled"):
        metric = payload.get("metrics", {}).get(name)
        if not metric:
            raise ValueError(f"falta métrica {name}")
        for key in ("totalReturn", "cagr", "sharpe", "sortino", "maxDrawdown", "volatility", "hitRate", "alpha", "beta"):
            finite(metric[key], f"{name}.{key}")
    for split in payload.get("methodology", {}).get("splits", []):
        if not split["trainEnd"] < split["calibrationStart"] <= split["calibrationEnd"] < split["testStart"]:
            raise ValueError(f"posible leakage temporal en {split}")
    for allocation in payload.get("riskControls", {}).get("allocations", []):
        if finite(allocation["maxPositionWeight"], "maxPositionWeight") > .200001:
            raise ValueError("el challenger excede 20% por posición")
        if not 0 <= finite(allocation["grossExposure"], "grossExposure") <= 1:
            raise ValueError("exposición bruta fuera de rango")


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


def validate_predictions(payload: dict[str, Any]) -> None:
    if payload.get("horizons") != [5, 20, 60]:
        raise ValueError("horizontes V5 inesperados")
    for item in payload.get("predictions", []):
        probability = finite(item["probability"], "probability")
        low = finite(item["uncertainty"]["low"], "uncertainty.low")
        high = finite(item["uncertainty"]["high"], "uncertainty.high")
        if not 0 <= low <= probability <= high <= 1:
            raise ValueError("probabilidad o incertidumbre fuera de rango")


def validate_ledger(payload: dict[str, Any]) -> None:
    records = payload.get("records", [])
    identifiers = [item.get("id") for item in records]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("prediction ledger contiene IDs duplicados")
    for item in records:
        if item.get("status") not in {"pending", "evaluated"}:
            raise ValueError("estado inválido en prediction ledger")
        if item.get("status") == "evaluated" and "excessReturn" not in item:
            raise ValueError("predicción evaluada sin resultado")


def validate_registry(payload: dict[str, Any]) -> None:
    if payload.get("champion", {}).get("key") not in {"statistical", "riskControlled"}:
        raise ValueError("champion desconocido")
    if int(payload.get("qualificationStreak", -1)) < 0:
        raise ValueError("streak inválido")


def validate_monitoring(payload: dict[str, Any]) -> None:
    if payload.get("status") not in {"healthy", "warning", "critical"}:
        raise ValueError("estado de monitoring inválido")
    coverage = finite(payload.get("data", {}).get("predictionCoverage"), "predictionCoverage")
    if not 0 <= coverage <= 1:
        raise ValueError("cobertura de monitoring fuera de rango")


def validate_alerts(payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload).lower()
    for forbidden in ("gmail_app_password", "alert_email_to", "alert_email_from", "smtp.gmail.com"):
        if forbidden in serialized:
            raise ValueError("alerts.json expone configuración privada")


def main() -> None:
    validate_backtest(load("backtest.json"))
    validate_risk(load("risk_model.json"))
    validate_events(load("event_studies.json"))
    validate_predictions(load("live_predictions.json"))
    validate_ledger(load("prediction_ledger.json"))
    validate_registry(load("model_registry.json"))
    validate_monitoring(load("model_monitoring.json"))
    validate_alerts(load("alerts.json"))
    print("Artefactos de investigación válidos.")


if __name__ == "__main__":
    main()
