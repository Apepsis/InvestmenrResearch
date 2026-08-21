"""Detect data, feature and realized-performance drift for V5."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data"
FEATURE_FILE = ROOT / "research_work" / "feature_store.json"
TICKERS_FILE = ROOT / "data" / "tickers.json"
OUTPUT_FILE = DATA / "model_monitoring.json"


def parse_time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def main() -> None:
    feature_payload = json.loads(FEATURE_FILE.read_text(encoding="utf-8"))
    live = json.loads((DATA / "live_predictions.json").read_text(encoding="utf-8"))
    ledger = json.loads((DATA / "prediction_ledger.json").read_text(encoding="utf-8"))
    market = json.loads((DATA / "market.json").read_text(encoding="utf-8"))
    registry = json.loads((DATA / "model_registry.json").read_text(encoding="utf-8"))
    tickers = [item["ticker"] for item in json.loads(TICKERS_FILE.read_text(encoding="utf-8")) if item["ticker"] != "SPY"]
    features = list(feature_payload["features"])
    frame = pd.DataFrame(feature_payload["rows"])
    frame["date"] = pd.to_datetime(frame["date"])
    frame[features] = frame[features].apply(pd.to_numeric, errors="coerce")
    ordered_dates = sorted(frame["date"].dropna().unique())
    cutoff = ordered_dates[max(1, int(len(ordered_dates) * .80)) - 1]
    reference = frame[frame["date"] <= cutoff]
    latest = frame.dropna(subset=features).sort_values(["ticker", "date"]).groupby("ticker", as_index=False).tail(1)
    shifts: list[dict[str, Any]] = []
    for feature in features:
        mean = float(reference[feature].mean())
        scale = float(reference[feature].std(ddof=0))
        latest_mean = float(latest[feature].mean())
        zscore = 0.0 if not np.isfinite(scale) or scale < 1e-12 else (latest_mean - mean) / scale
        shifts.append({"feature": feature, "referenceMean": round(mean, 8), "latestMean": round(latest_mean, 8), "standardizedShift": round(float(zscore), 5)})
    shifts.sort(key=lambda item: abs(float(item["standardizedShift"])), reverse=True)
    max_shift = abs(float(shifts[0]["standardizedShift"])) if shifts else 0.0

    expected = len(tickers) * len(live.get("horizons", [5, 20, 60]))
    predictions = [item for item in live.get("predictions", []) if item.get("ticker") in tickers]
    coverage = len(predictions) / max(expected, 1)
    market_time = parse_time(str(market.get("generatedAt", "")))
    age_hours = (datetime.now(timezone.utc) - market_time).total_seconds() / 3600 if market_time else 9999.0
    evaluated = [item for item in ledger.get("records", []) if item.get("status") == "evaluated"]
    recent = evaluated[-120:]
    realized_accuracy = float(np.mean([bool(item.get("correct")) for item in recent])) if recent else None
    realized_brier = float(np.mean([(float(item["probability"]) - float(item["outcome"])) ** 2 for item in recent])) if recent else None

    issues: list[dict[str, str]] = []
    if coverage < .80:
        issues.append({"code": "prediction_coverage", "severity": "critical", "message": f"Cobertura de predicciones {coverage * 100:.1f}%"})
    if age_hours > 72:
        issues.append({"code": "stale_market_data", "severity": "critical", "message": f"Datos de mercado con {age_hours:.1f} horas de antigüedad"})
    elif age_hours > 36:
        issues.append({"code": "stale_market_data", "severity": "warning", "message": f"Datos de mercado con {age_hours:.1f} horas de antigüedad"})
    if max_shift >= 3:
        issues.append({"code": "feature_drift", "severity": "critical", "message": f"Cambio estandarizado máximo {max_shift:.2f}σ"})
    elif max_shift >= 2:
        issues.append({"code": "feature_drift", "severity": "warning", "message": f"Cambio estandarizado máximo {max_shift:.2f}σ"})
    if len(recent) >= 30 and realized_brier is not None and realized_brier > .30:
        issues.append({"code": "performance_drift", "severity": "warning", "message": f"Brier reciente {realized_brier:.3f} en {len(recent)} predicciones"})
    status = "critical" if any(item["severity"] == "critical" for item in issues) else "warning" if issues else "healthy"
    output = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "mode": "live",
        "status": status,
        "data": {
            "predictionCoverage": round(coverage, 6),
            "predictionsPublished": len(predictions),
            "predictionsExpected": expected,
            "marketDataAgeHours": round(age_hours, 3),
            "providerErrors": len(market.get("errors", {})),
        },
        "featureDrift": {"maximumAbsoluteShift": round(max_shift, 5), "thresholdWarning": 2.0, "thresholdCritical": 3.0, "topShifts": shifts[:8]},
        "performance": {
            "evaluatedPredictions": len(evaluated),
            "recentWindow": len(recent),
            "accuracy": None if realized_accuracy is None else round(realized_accuracy, 6),
            "brierScore": None if realized_brier is None else round(realized_brier, 6),
            "minimumWindowForAlert": 30,
        },
        "governance": {
            "champion": registry["champion"]["key"],
            "challengerQualified": registry["qualifiedThisRun"],
            "qualificationStreak": registry["qualificationStreak"],
        },
        "issues": issues,
        "interpretation": "Las alertas detectan cambios o fallas; no prueban causalidad ni predicen precios.",
    }
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Monitoring: {status}; cobertura {coverage * 100:.1f}%; shift máximo {max_shift:.2f}σ.")


if __name__ == "__main__":
    main()
