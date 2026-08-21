"""Validate public research artifacts before GitHub Pages can publish them."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
MODELS = ROOT / "models"


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


def validate_fast_signals(payload: dict[str, Any]) -> None:
    if payload.get("mode") != "live" or payload.get("refreshIntervalMinutes") != 20:
        raise ValueError("fast_signals no representa una ejecución live de 20 minutos")
    stocks = payload.get("stocks", {})
    if not stocks:
        raise ValueError("fast_signals no contiene activos")
    for ticker, stock in stocks.items():
        if stock.get("ticker") != ticker:
            raise ValueError("ticker inconsistente en fast_signals")
        if stock.get("signal") not in {"positive", "neutral", "negative"}:
            raise ValueError("dirección inválida en fast_signals")
        if stock.get("urgency") not in {"low", "medium", "high"}:
            raise ValueError("urgencia inválida en fast_signals")
        score = finite(stock.get("newsScore"), "newsScore")
        if not 0 <= score <= 100:
            raise ValueError("newsScore fuera de rango")
        for item in stock.get("items", []):
            if not item.get("id") or not item.get("firstSeenAt"):
                raise ValueError("titular rápido sin identidad o procedencia temporal")


def validate_neural_lab(payload: dict[str, Any]) -> None:
    if payload.get("mode") != "live" or payload.get("modelFamily") != "persistent-neural-research-v8":
        raise ValueError("neural_lab no representa una ejecución V8 real")
    active = payload.get("active", {})
    if active.get("role") not in {"champion", "shadow-challenger"}:
        raise ValueError("rol neural desconocido")
    architecture = active.get("architecture", {})
    if architecture.get("input") != len(payload.get("reproducibility", {}).get("features", [])):
        raise ValueError("arquitectura neural inconsistente con las variables")
    if architecture.get("output") != 3 or architecture.get("ensembleMembers", 0) < 2:
        raise ValueError("la red V8 debe conservar tres horizontes y un ensemble")
    split = payload.get("temporalSplit", {})
    if not split.get("trainEnd", "") < split.get("calibrationStart", "") <= split.get("calibrationEnd", "") < split.get("shadowStart", ""):
        raise ValueError("posible leakage en el split neural")
    if int(split.get("purgeSessions", 0)) < 60:
        raise ValueError("el split neural carece del embargo de 60 sesiones")
    for item in payload.get("currentPredictions", []):
        probability = finite(item["probability"], "neural probability")
        low = finite(item["uncertainty"]["low"], "neural uncertainty.low")
        high = finite(item["uncertainty"]["high"], "neural uncertainty.high")
        if not 0 <= low <= probability <= high <= 1:
            raise ValueError("predicción neural fuera de rango")
    for candidate in payload.get("candidates", []):
        metrics = candidate.get("metrics", {})
        for key in ("brierScore", "logLoss", "accuracy", "ece", "temporalBlockWinRate"):
            finite(metrics[key], f"neural candidate {key}")
    model_path = ROOT / str(active.get("modelPath", ""))
    if not model_path.exists() or not model_path.is_relative_to(MODELS):
        raise ValueError("el artefacto de pesos activo no existe dentro de models/")
    model = json.loads(model_path.read_text(encoding="utf-8"))
    if model.get("artifactHash") != active.get("artifactHash") or model.get("version") != active.get("version"):
        raise ValueError("los pesos activos no coinciden con neural_lab")
    serialized = json.dumps(model).lower()
    for forbidden in ("alpaca_api_secret", "gmail_app_password", "firebase-adminsdk", "private_key"):
        if forbidden in serialized:
            raise ValueError("el artefacto neural contiene una cadena compatible con credenciales")


def validate_neural_ledger(payload: dict[str, Any]) -> None:
    records = payload.get("records", [])
    identifiers = [item.get("id") for item in records]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("neural ledger contiene IDs duplicados")
    for item in records:
        if item.get("modelFamily") != "persistent-neural-research-v8":
            raise ValueError("registro neural con familia incorrecta")
        if item.get("status") not in {"pending", "evaluated"}:
            raise ValueError("estado inválido en neural ledger")


def main() -> None:
    validate_backtest(load("backtest.json"))
    validate_risk(load("risk_model.json"))
    validate_events(load("event_studies.json"))
    validate_predictions(load("live_predictions.json"))
    validate_ledger(load("prediction_ledger.json"))
    validate_registry(load("model_registry.json"))
    validate_monitoring(load("model_monitoring.json"))
    validate_alerts(load("alerts.json"))
    validate_fast_signals(load("fast_signals.json"))
    validate_neural_lab(load("neural_lab.json"))
    validate_neural_ledger(load("neural_prediction_ledger.json"))
    print("Artefactos de investigación válidos.")


if __name__ == "__main__":
    main()
