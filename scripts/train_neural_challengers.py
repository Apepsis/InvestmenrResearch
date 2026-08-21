"""Train, evaluate and persist the V8 neural Champion–Challenger system.

Every candidate is evaluated on a purged temporal shadow set.  Published
predictions are append-only.  A neural model replaces the reference only when
all trial-adjusted gates pass; otherwise the frozen Champion remains active.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from neural_core import (
    ablation_sensitivity,
    classification_metrics,
    clone_artifact,
    fit_ensemble,
    predict_ensemble,
    promotion_gate,
    temporal_block_win_rate,
)
from research_core import fit_logistic, fit_platt
from v5_core import canonical_hash, evaluate_record, prediction_id, upsert_immutable_records


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "research_work"
PUBLIC = ROOT / "public" / "data"
MODELS = ROOT / "models"
CHALLENGERS = MODELS / "challengers"
ARCHIVE = MODELS / "archive"
FEATURE_FILE = WORK / "feature_store.json"
PRICE_FILE = WORK / "prices.json"
LAB_FILE = PUBLIC / "neural_lab.json"
LEDGER_FILE = PUBLIC / "neural_prediction_ledger.json"
REGISTRY_FILE = MODELS / "neural_registry.json"
CHAMPION_FILE = MODELS / "champion.json"
INCUMBENT_FILE = CHALLENGERS / "incumbent.json"
RUNNER_UP_FILE = CHALLENGERS / "runner_up.json"
HORIZONS = [5, 20, 60]
MAX_HORIZON = max(HORIZONS)
MODEL_FAMILY = "persistent-neural-research-v8"


def read_json(path: Path, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return {} if fallback is None else fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def compatible(artifact: dict[str, Any], features: list[str]) -> bool:
    return (
        artifact.get("kind") == "multi-task-mlp-deep-ensemble"
        and artifact.get("features") == features
        and artifact.get("horizons") == HORIZONS
        and bool(artifact.get("members"))
    )


def slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value)[:100]


def temporal_frames(frame: pd.DataFrame, features: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    targets = [f"label_excess_positive_{horizon}" for horizon in HORIZONS]
    matured = frame.dropna(subset=features + targets).sort_values(["date", "ticker"]).copy()
    dates = np.asarray(sorted(matured["date"].unique()))
    if len(dates) < 700:
        raise RuntimeError(f"Se requieren al menos 700 fechas para el protocolo neural; disponibles: {len(dates)}")
    train_end_index = int(len(dates) * .60)
    calibration_end_index = int(len(dates) * .80)
    calibration_start_index = train_end_index + MAX_HORIZON
    shadow_start_index = calibration_end_index + MAX_HORIZON
    if calibration_start_index >= calibration_end_index or shadow_start_index >= len(dates):
        raise RuntimeError("No hay espacio suficiente para los embargos temporales de 60 sesiones")
    train_end = dates[train_end_index - 1]
    calibration_start = dates[calibration_start_index]
    calibration_end = dates[calibration_end_index - 1]
    shadow_start = dates[shadow_start_index]
    training = matured[matured["date"] <= train_end]
    calibration = matured[(matured["date"] >= calibration_start) & (matured["date"] <= calibration_end)]
    shadow = matured[matured["date"] >= shadow_start]
    if min(len(training), len(calibration), len(shadow)) < 600:
        raise RuntimeError(f"Split neural insuficiente: train={len(training)}, calibración={len(calibration)}, shadow={len(shadow)}")
    metadata = {
        "method": "60% entrenamiento, embargo 60 sesiones, 20% calibración, embargo 60 sesiones, 20% shadow restante",
        "trainStart": training["date"].min().date().isoformat(),
        "trainEnd": training["date"].max().date().isoformat(),
        "calibrationStart": calibration["date"].min().date().isoformat(),
        "calibrationEnd": calibration["date"].max().date().isoformat(),
        "shadowStart": shadow["date"].min().date().isoformat(),
        "shadowEnd": shadow["date"].max().date().isoformat(),
        "purgeSessions": MAX_HORIZON,
        "trainingRows": len(training),
        "calibrationRows": len(calibration),
        "shadowRows": len(shadow),
    }
    return training, calibration, shadow, metadata


def matrix(frame: pd.DataFrame, names: list[str]) -> np.ndarray:
    return frame[names].to_numpy(float)


def fit_baseline(
    training: pd.DataFrame,
    calibration: pd.DataFrame,
    shadow: pd.DataFrame,
    latest: pd.DataFrame,
    features: list[str],
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    shadow_probabilities = np.zeros((len(shadow), len(HORIZONS)))
    latest_probabilities = np.zeros((len(latest), len(HORIZONS)))
    details = {}
    for index, horizon in enumerate(HORIZONS):
        target = f"label_excess_positive_{horizon}"
        model = fit_logistic(matrix(training, features), training[target].to_numpy(float))
        calibration_logits = model.decision_function(matrix(calibration, features))
        calibrator = fit_platt(calibration_logits, calibration[target].to_numpy(float))
        shadow_probabilities[:, index] = calibrator.transform(model.decision_function(matrix(shadow, features)))
        latest_probabilities[:, index] = calibrator.transform(model.decision_function(matrix(latest, features)))
        details[str(horizon)] = {
            "coefficients": [round(float(value), 8) for value in model.coefficients],
            "calibrationSlope": round(float(calibrator.slope), 8),
            "calibrationIntercept": round(float(calibrator.intercept), 8),
        }
    return shadow_probabilities, latest_probabilities, details


def decorate_artifact(
    artifact: dict[str, Any],
    *,
    candidate_kind: str,
    data_hash: str,
    split: dict[str, Any],
    hyperparameters: dict[str, Any],
) -> dict[str, Any]:
    output = clone_artifact(artifact)
    identity = canonical_hash({
        "candidateKind": candidate_kind,
        "dataHash": data_hash,
        "features": output["features"],
        "architecture": output["architecture"],
        "members": output["members"],
    })[:10]
    date = str(split["shadowEnd"]).replace("-", "")
    output.update({
        "version": f"neural-v8-{date}-{candidate_kind}-{identity}",
        "candidateKind": candidate_kind,
        "createdAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "dataHash": data_hash,
        "trainingProtocol": split,
        "hyperparameters": hyperparameters,
        "artifactHash": "",
    })
    output["artifactHash"] = "sha256:" + canonical_hash({key: value for key, value in output.items() if key != "artifactHash"})
    return output


def evaluate_artifact(
    artifact: dict[str, Any],
    values: np.ndarray,
    target: np.ndarray,
    dates: np.ndarray,
    reference_probability: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    probability, disagreement, _ = predict_ensemble(artifact, values)
    metrics = classification_metrics(probability, target, HORIZONS)
    win_rate, blocks = temporal_block_win_rate(probability, reference_probability, target, dates)
    metrics["temporalBlockWinRate"] = round(win_rate, 6)
    metrics["temporalBlocks"] = blocks
    metrics["meanEnsembleDisagreement"] = round(float(np.mean(disagreement)), 8)
    return probability, metrics


def candidate_score(metrics: dict[str, Any]) -> float:
    return float(metrics["brierScore"]) + .20 * float(metrics["logLoss"]) + .30 * float(metrics["ece"])


def load_reusable_candidates(features: list[str]) -> list[dict[str, Any]]:
    candidates = []
    for path in (INCUMBENT_FILE, RUNNER_UP_FILE):
        artifact = read_json(path)
        if compatible(artifact, features):
            candidates.append(artifact)
    if ARCHIVE.exists():
        for path in sorted(ARCHIVE.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:5]:
            artifact = read_json(path)
            if compatible(artifact, features):
                candidates.append(artifact)
    unique = {}
    for artifact in candidates:
        unique[str(artifact.get("version"))] = artifact
    return list(unique.values())


def specific_sensitivity(artifact: dict[str, Any], values: np.ndarray, horizon_index: int) -> list[dict[str, Any]]:
    baseline, _, _ = predict_ensemble(artifact, values.reshape(1, -1))
    mean = np.asarray(artifact["normalization"]["mean"], dtype=float)
    output = []
    for index, feature in enumerate(artifact["features"]):
        changed = values.copy()
        changed[index] = mean[index]
        probability, _, _ = predict_ensemble(artifact, changed.reshape(1, -1))
        contribution = float(baseline[0, horizon_index] - probability[0, horizon_index])
        output.append({
            "feature": feature,
            "probabilityContribution": round(contribution, 8),
            "method": "Probabilidad original menos probabilidad al reemplazar la variable por su media de entrenamiento",
        })
    return sorted(output, key=lambda row: abs(float(row["probabilityContribution"])), reverse=True)


def publish_predictions(
    artifact: dict[str, Any],
    latest: pd.DataFrame,
    prices: dict[str, Any],
    role: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    probability, disagreement, _ = predict_ensemble(artifact, matrix(latest, artifact["features"]))
    existing_payload = read_json(LEDGER_FILE, {"records": []})
    existing = [evaluate_record(item, prices) for item in existing_payload.get("records", [])]
    predictions = []
    for row_index, (_, row) in enumerate(latest.iterrows()):
        ticker = str(row["ticker"])
        date = row["date"].date().isoformat()
        series = prices.get(ticker, {})
        by_date = dict(zip(series.get("dates", []), series.get("close", [])))
        if date not in by_date:
            continue
        raw_values = row[artifact["features"]].to_numpy(float)
        for horizon_index, horizon in enumerate(HORIZONS):
            current = float(probability[row_index, horizon_index])
            calibration = artifact["calibration"][horizon_index]
            radius = float(calibration["conformalRadius80"])
            ensemble_std = float(disagreement[row_index, horizon_index])
            width = min(.49, radius + ensemble_std)
            estimates = [
                item for item in existing
                if item.get("ticker") == ticker and int(item.get("horizonSessions", 0)) == horizon
                and str(item.get("predictionDate", "")) < date
            ]
            previous = float(max(estimates, key=lambda item: str(item["predictionDate"]))["probability"]) if estimates else None
            prediction = {
                "id": prediction_id(date, ticker, horizon, str(artifact["version"])),
                "predictionDate": date,
                "ticker": ticker,
                "horizonSessions": horizon,
                "probability": round(current, 8),
                "uncertainty": {
                    "low": round(max(0, current - width), 8),
                    "high": round(min(1, current + width), 8),
                    "ensembleStd": round(ensemble_std, 8),
                    "conformalRadius80": round(radius, 8),
                    "method": "Desacuerdo del deep ensemble + residual split-conformal temporal al 80%; no es garantía",
                },
                "initialPrice": round(float(by_date[date]), 6),
                "estimatedMaturityDate": (row["date"] + pd.offsets.BDay(horizon)).date().isoformat(),
                "modelVersion": artifact["version"],
                "modelFamily": MODEL_FAMILY,
                "modelRole": role,
                "modelHash": artifact["artifactHash"],
                "dataHash": artifact["dataHash"],
                "status": "pending",
                "changeFromPrevious": None if previous is None else round(current - previous, 8),
                "decisionThreshold": .5,
                "contributions": specific_sensitivity(artifact, raw_values, horizon_index)[:8],
            }
            predictions.append(prediction)
    records = upsert_immutable_records(existing, predictions)
    return predictions, records


def archive_champion(artifact: dict[str, Any]) -> None:
    if not artifact:
        return
    output = ARCHIVE / f"{slug(str(artifact.get('version', 'unknown')))}.json"
    if not output.exists():
        write_json(output, artifact)


def main() -> None:
    feature_payload = read_json(FEATURE_FILE)
    price_payload = read_json(PRICE_FILE)
    features = list(feature_payload["features"])
    targets = [f"label_excess_positive_{horizon}" for horizon in HORIZONS]
    frame = pd.DataFrame(feature_payload["rows"])
    frame["date"] = pd.to_datetime(frame["date"])
    frame[features + targets] = frame[features + targets].apply(pd.to_numeric, errors="coerce")
    latest = frame.dropna(subset=features).sort_values(["ticker", "date"]).groupby("ticker", as_index=False).tail(1).sort_values("ticker")
    training, calibration, shadow, split = temporal_frames(frame, features)
    train_x, calibration_x, shadow_x = matrix(training, features), matrix(calibration, features), matrix(shadow, features)
    train_y, calibration_y, shadow_y = matrix(training, targets), matrix(calibration, targets), matrix(shadow, targets)
    shadow_dates = shadow["date"].to_numpy(dtype="datetime64[ns]")
    data_hash = sha256(FEATURE_FILE)
    baseline_shadow, _, baseline_details = fit_baseline(training, calibration, shadow, latest, features)
    baseline_metrics = classification_metrics(baseline_shadow, shadow_y, HORIZONS)
    baseline_metrics["temporalBlockWinRate"] = 1.0

    registry = read_json(REGISTRY_FILE, {"history": [], "trialCount": 0})
    current_champion = read_json(CHAMPION_FILE)
    champion_is_neural = compatible(current_champion, features)
    if champion_is_neural:
        reference_probability, reference_metrics = evaluate_artifact(current_champion, shadow_x, shadow_y, shadow_dates, baseline_shadow)
        reference_kind = "neural-champion"
        reference_version = current_champion["version"]
    else:
        reference_probability = baseline_shadow
        reference_metrics = baseline_metrics
        reference_kind = "regularized-logistic-baseline"
        reference_version = "transparent-research-v5.0"

    new_candidates: list[dict[str, Any]] = []
    cold = fit_ensemble(
        train_x, train_y, calibration_x, calibration_y,
        features=features, horizons=HORIZONS, seeds=[11, 29, 47], hidden=(24, 12), epochs=120, l2=.002,
    )
    new_candidates.append(decorate_artifact(
        cold,
        candidate_kind="cold",
        data_hash=data_hash,
        split=split,
        hyperparameters={"epochsMaximum": 120, "l2": .002, "seeds": [11, 29, 47], "earlyStopping": True},
    ))
    if champion_is_neural:
        warm = fit_ensemble(
            train_x, train_y, calibration_x, calibration_y,
            features=features, horizons=HORIZONS, seeds=[11, 29, 47], hidden=(24, 12), epochs=90, l2=.002,
            warm_artifact=current_champion, memory_strength=.035,
        )
        new_candidates.append(decorate_artifact(
            warm,
            candidate_kind="warm-ewc",
            data_hash=data_hash,
            split=split,
            hyperparameters={"epochsMaximum": 90, "l2": .002, "memoryStrength": .035, "seeds": [11, 29, 47], "earlyStopping": True},
        ))
    else:
        conservative = fit_ensemble(
            train_x, train_y, calibration_x, calibration_y,
            features=features, horizons=HORIZONS, seeds=[71, 89, 107], hidden=(24, 12), epochs=120, l2=.006,
        )
        new_candidates.append(decorate_artifact(
            conservative,
            candidate_kind="regularized",
            data_hash=data_hash,
            split=split,
            hyperparameters={"epochsMaximum": 120, "l2": .006, "seeds": [71, 89, 107], "earlyStopping": True},
        ))

    reusable = load_reusable_candidates(features)
    candidates_by_version = {str(item["version"]): item for item in [*new_candidates, *reusable] if str(item.get("version")) != reference_version}
    trial_count = int(registry.get("trialCount", 0)) + len(new_candidates)
    evaluated_candidates = []
    artifacts = {}
    for artifact in candidates_by_version.values():
        try:
            _, metrics = evaluate_artifact(artifact, shadow_x, shadow_y, shadow_dates, reference_probability)
        except (KeyError, ValueError, IndexError):
            continue
        qualified, checks, required = promotion_gate(reference_metrics, metrics, trial_count=trial_count)
        row = {
            "version": artifact["version"],
            "candidateKind": artifact.get("candidateKind", "archived"),
            "parentVersion": artifact.get("memory", {}).get("parentVersion"),
            "artifactHash": artifact.get("artifactHash"),
            "metrics": metrics,
            "promotionChecks": checks,
            "requiredBrierImprovement": round(required, 8),
            "qualified": qualified,
            "source": "trained-this-run" if artifact in new_candidates else "re-evaluated-saved-model",
        }
        evaluated_candidates.append(row)
        artifacts[str(artifact["version"])] = artifact
    if not evaluated_candidates:
        raise RuntimeError("No se pudo evaluar ningún challenger neural")
    evaluated_candidates.sort(key=lambda row: candidate_score(row["metrics"]))
    best = evaluated_candidates[0]
    best_artifact = artifacts[str(best["version"])]
    promoted = bool(best["qualified"])
    if promoted:
        archive_champion(current_champion)
        write_json(CHAMPION_FILE, best_artifact)
        active_artifact = best_artifact
        active_role = "champion"
        decision = f"{best['version']} fue promovido: superó todos los gates temporales y ajustados por {trial_count} ensayos."
    elif champion_is_neural:
        active_artifact = current_champion
        active_role = "champion"
        decision = f"El Champion {reference_version} permanece congelado; el mejor challenger no superó todos los gates."
    else:
        active_artifact = best_artifact
        active_role = "shadow-challenger"
        decision = "La regresión logística sigue siendo la referencia oficial; la red se publica en modo shadow hasta demostrar mejora."

    # Preserve the strongest failed network so it can be reconsidered under a
    # later market regime.  The second slot prevents a single lineage from
    # monopolizing the model zoo.
    failed = [row for row in evaluated_candidates if row["version"] != active_artifact.get("version")]
    if not promoted or best["version"] != active_artifact.get("version"):
        write_json(INCUMBENT_FILE, best_artifact)
    elif failed:
        write_json(INCUMBENT_FILE, artifacts[str(failed[0]["version"])])
    if len(failed) > 1:
        write_json(RUNNER_UP_FILE, artifacts[str(failed[1]["version"])])

    predictions, records = publish_predictions(active_artifact, latest, price_payload["prices"], active_role)
    sensitivity = ablation_sensitivity(active_artifact, shadow_x)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    history = list(registry.get("history", []))
    history.append({
        "generatedAt": generated_at,
        "dataHash": data_hash,
        "referenceVersion": reference_version,
        "bestChallenger": best["version"],
        "promoted": promoted,
        "decision": decision,
    })
    registry_output = {
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "modelFamily": MODEL_FAMILY,
        "trialCount": trial_count,
        "championKind": "neural" if CHAMPION_FILE.exists() else "logistic-baseline",
        "championVersion": read_json(CHAMPION_FILE).get("version", "transparent-research-v5.0"),
        "bestChallengerVersion": best["version"],
        "lastDecision": decision,
        "history": history[-200:],
        "policy": "Nunca reescribir predicciones; promover solo con shadow temporal purgado, corrección por ensayos y estabilidad por bloques.",
    }
    write_json(REGISTRY_FILE, registry_output)
    write_json(LEDGER_FILE, {
        "generatedAt": generated_at,
        "mode": "live",
        "modelFamily": MODEL_FAMILY,
        "policy": "Append-only: pesos/versiones y probabilidades publicadas no se modifican; el resultado se completa al madurar.",
        "recordCount": len(records),
        "evaluatedCount": sum(item.get("status") == "evaluated" for item in records),
        "records": records,
    })
    write_json(LAB_FILE, {
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "mode": "live",
        "modelFamily": MODEL_FAMILY,
        "status": "neural-champion" if active_role == "champion" else "shadow-challenger",
        "hypothesis": "Una red pequeña y persistente puede mejorar probabilidades fuera de muestra frente a la regresión logística sin usar información futura.",
        "active": {
            "role": active_role,
            "version": active_artifact["version"],
            "artifactHash": active_artifact["artifactHash"],
            "dataHash": active_artifact["dataHash"],
            "architecture": active_artifact["architecture"],
            "memory": active_artifact["memory"],
            "modelPath": "models/champion.json" if active_role == "champion" else "models/challengers/incumbent.json",
        },
        "reference": {"kind": reference_kind, "version": reference_version, "metrics": reference_metrics},
        "baseline": {"version": "transparent-research-v5.0", "metrics": baseline_metrics, "fit": baseline_details},
        "bestChallenger": best,
        "candidates": evaluated_candidates,
        "decision": decision,
        "promotedThisRun": promoted,
        "governance": {
            "trialCount": trial_count,
            "selectionMetric": "Brier + 0.20×log loss + 0.30×ECE",
            "promotionPolicy": "Todos los checks deben pasar. Un fallo conserva el Champion sin cambios.",
            "archivedModelsReevaluated": sum(row["source"] == "re-evaluated-saved-model" for row in evaluated_candidates),
            "automaticTrading": False,
        },
        "temporalSplit": split,
        "currentPredictions": predictions,
        "ledger": {"records": len(records), "evaluated": sum(item.get("status") == "evaluated" for item in records)},
        "globalSensitivity": sensitivity[:12],
        "reproducibility": {
            "framework": "NumPy auditable",
            "features": features,
            "horizons": HORIZONS,
            "sourceFile": "scripts/neural_core.py",
            "trainingFile": "scripts/train_neural_challengers.py",
            "savedWeights": True,
            "seedsPublished": True,
        },
        "limitations": [
            "La red aprende asociaciones, no causalidad, y no garantiza rendimientos.",
            "El universo actual puede contener sesgo de supervivencia.",
            "Los horizontes solapados reducen la independencia efectiva de las observaciones.",
            "Noticias y fundamentales no entran a la red histórica hasta contar con archivos point-in-time fiables; permanecen en el score auditable separado.",
            "Las predicciones activan investigación y alertas; el sistema no compra ni vende.",
        ],
        "researchBasis": [
            {"method": "Deep ensembles", "purpose": "incertidumbre por desacuerdo entre inicializaciones"},
            {"method": "EWC-style anchoring", "purpose": "reducir olvido catastrófico al continuar desde el Champion"},
            {"method": "Purged temporal shadow set", "purpose": "evitar que un objetivo futuro cruce los cortes"},
            {"method": "Split-conformal residual band", "purpose": "hacer visible la incertidumbre empírica"},
            {"method": "Trial-adjusted promotion", "purpose": "dificultar promociones por probar muchos candidatos"},
        ],
    })
    print(
        f"Neural V8: active={active_artifact['version']} ({active_role}); "
        f"best={best['version']}; promoted={promoted}; ledger={len(records)}."
    )


if __name__ == "__main__":
    main()
