from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from research_core import fit_logistic, fit_platt
from v5_core import evaluate_record, prediction_id, upsert_immutable_records


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "research_work"
PUBLIC = ROOT / "public" / "data"
FEATURE_FILE = WORK / "feature_store.json"
PRICE_FILE = WORK / "prices.json"
LIVE_FILE = PUBLIC / "live_predictions.json"
LEDGER_FILE = PUBLIC / "prediction_ledger.json"
HORIZONS = (5, 20, 60)
MODEL_VERSION = "transparent-research-v5.0"


def file_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def previous_probability(records: list[dict[str, Any]], ticker: str, horizon: int, date: str) -> float | None:
    matches = [item for item in records if item.get("ticker") == ticker and int(item.get("horizonSessions", 0)) == horizon and str(item.get("predictionDate", "")) < date]
    if not matches:
        return None
    return float(max(matches, key=lambda item: str(item["predictionDate"]))["probability"])


def preserve_first_publication(existing_by_id: dict[str, dict[str, Any]], candidate: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Keep the first prediction published for a deterministic daily ID.

    Providers can revise the final daily bar and a manual workflow can run more
    than once.  Re-training may therefore produce a different probability for
    the same date/model ID.  The ledger is pre-registered: a rerun must reuse
    the original record instead of overwriting it or failing the whole pipeline.
    """
    record_id = str(candidate["id"])
    if record_id in existing_by_id:
        return dict(existing_by_id[record_id]), True
    return candidate, False


def contribution_rows(model: Any, calibrator: Any, values: np.ndarray, features: list[str]) -> list[dict[str, Any]]:
    standardized = model.standardizer.transform(values.reshape(1, -1))[0]
    contributions = standardized * model.coefficients * calibrator.slope
    output = []
    for feature, raw, zscore, weight, contribution in zip(features, values, standardized, model.coefficients, contributions):
        output.append({
            "feature": feature,
            "rawValue": round(float(raw), 8),
            "standardizedValue": round(float(zscore), 6),
            "coefficient": round(float(weight), 6),
            "logitContribution": round(float(contribution), 6),
            "formula": "z(feature) × coeficiente × pendiente_calibración",
            "source": "Precios ajustados point-in-time; feature_store.json",
        })
    return sorted(output, key=lambda item: abs(float(item["logitContribution"])), reverse=True)


def main() -> None:
    feature_payload = json.loads(FEATURE_FILE.read_text(encoding="utf-8"))
    price_payload = json.loads(PRICE_FILE.read_text(encoding="utf-8"))
    features = list(feature_payload["features"])
    frame = pd.DataFrame(feature_payload["rows"])
    frame["date"] = pd.to_datetime(frame["date"])
    frame[features] = frame[features].apply(pd.to_numeric, errors="coerce")
    data_hash = file_hash(FEATURE_FILE)
    existing_payload = json.loads(LEDGER_FILE.read_text(encoding="utf-8")) if LEDGER_FILE.exists() else {"records": []}
    existing = [evaluate_record(item, price_payload["prices"]) for item in existing_payload.get("records", [])]
    existing_by_id = {str(item["id"]): item for item in existing}
    published: list[dict[str, Any]] = []
    fit_metadata: dict[str, Any] = {}
    reused_publications = 0

    for horizon in HORIZONS:
        target = f"label_excess_positive_{horizon}"
        frame[target] = pd.to_numeric(frame[target], errors="coerce")
        matured = frame.dropna(subset=features + [target]).sort_values(["date", "ticker"])
        if len(matured) < 500:
            raise RuntimeError(f"Cobertura insuficiente para horizonte {horizon}: {len(matured)} filas")
        unique_dates = sorted(matured["date"].unique())
        split_date = unique_dates[max(1, int(len(unique_dates) * .80)) - 1]
        training = matured[matured["date"] <= split_date]
        calibration = matured[matured["date"] > split_date]
        if len(training) < 300 or len(calibration) < 80:
            raise RuntimeError(f"Split insuficiente para horizonte {horizon}")
        model = fit_logistic(training[features].to_numpy(float), training[target].to_numpy(float))
        logits = model.decision_function(calibration[features].to_numpy(float))
        calibrator = fit_platt(logits, calibration[target].to_numpy(float))
        calibrated = calibrator.transform(logits)
        labels = calibration[target].to_numpy(float)
        brier = float(np.mean((calibrated - labels) ** 2))
        fit_metadata[str(horizon)] = {
            "trainStart": training["date"].min().date().isoformat(),
            "trainEnd": training["date"].max().date().isoformat(),
            "calibrationStart": calibration["date"].min().date().isoformat(),
            "calibrationEnd": calibration["date"].max().date().isoformat(),
            "trainingRows": int(len(training)),
            "calibrationRows": int(len(calibration)),
            "brierScoreCalibration": round(brier, 6),
        }

        latest = frame.dropna(subset=features).sort_values(["ticker", "date"]).groupby("ticker", as_index=False).tail(1)
        for _, row in latest.iterrows():
            ticker = str(row["ticker"])
            date = row["date"].date().isoformat()
            series = price_payload["prices"].get(ticker, {})
            price_by_date = dict(zip(series.get("dates", []), series.get("close", [])))
            if date not in price_by_date:
                continue
            values = row[features].to_numpy(float)
            raw_logit = model.decision_function(values.reshape(1, -1))
            probability = float(calibrator.transform(raw_logit)[0])
            # Empirical uncertainty band, not a claim of a formal confidence interval.
            sampling = 1.64 * math.sqrt(max(probability * (1 - probability), 1e-6) / len(calibration))
            half_width = min(.18, max(.05, sampling + .15 * math.sqrt(max(brier, 0))))
            prior = previous_probability(existing, ticker, horizon, date)
            expires = (row["date"] + pd.offsets.BDay(horizon)).date().isoformat()
            prediction = {
                "id": prediction_id(date, ticker, horizon, MODEL_VERSION),
                "predictionDate": date,
                "ticker": ticker,
                "horizonSessions": horizon,
                "probability": round(probability, 6),
                "uncertainty": {
                    "low": round(max(0.0, probability - half_width), 6),
                    "high": round(min(1.0, probability + half_width), 6),
                    "method": "Banda empírica por calibración y tamaño de muestra; no es garantía",
                },
                "initialPrice": round(float(price_by_date[date]), 6),
                "estimatedMaturityDate": expires,
                "modelVersion": MODEL_VERSION,
                "dataHash": data_hash,
                "status": "pending",
                "changeFromPrevious": None if prior is None else round(probability - prior, 6),
                "decisionThreshold": 0.5,
                "contributions": contribution_rows(model, calibrator, values, features)[:8],
            }
            frozen, reused = preserve_first_publication(existing_by_id, prediction)
            published.append(frozen)
            reused_publications += int(reused)

    records = upsert_immutable_records(existing, published)
    evaluated = sum(item.get("status") == "evaluated" for item in records)
    generated_at = pd.Timestamp.utcnow().isoformat()
    LIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    LIVE_FILE.write_text(json.dumps({
        "generatedAt": generated_at,
        "mode": "live",
        "modelVersion": MODEL_VERSION,
        "horizons": list(HORIZONS),
        "hypothesis": "Probabilidad de superar a SPY en 5, 20 o 60 sesiones usando solo información disponible al publicar.",
        "predictions": published,
        "modelFits": fit_metadata,
        "rerunPolicy": {
            "reusedPublications": reused_publications,
            "rule": "La primera predicción publicada para cada fecha, activo, horizonte y versión permanece congelada en reruns.",
        },
        "limitations": [
            "La banda de incertidumbre es empírica y no garantiza cobertura futura.",
            "El universo actual fue seleccionado con información contemporánea y puede contener sesgo de supervivencia.",
            "Las predicciones no constituyen recomendaciones de inversión.",
        ],
    }, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    LEDGER_FILE.write_text(json.dumps({
        "generatedAt": generated_at,
        "mode": "live",
        "policy": "Los campos de publicación son inmutables; únicamente se completan resultado y evaluación al madurar el horizonte.",
        "immutableFields": list(("id", "predictionDate", "ticker", "horizonSessions", "probability", "uncertainty", "initialPrice", "modelVersion", "dataHash")),
        "recordCount": len(records),
        "evaluatedCount": evaluated,
        "records": records,
    }, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Predicciones V5: {len(published)} actuales; ledger {len(records)}, {evaluated} evaluadas; {reused_publications} reutilizadas por rerun.")


if __name__ == "__main__":
    main()
