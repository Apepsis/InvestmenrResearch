"""Run an out-of-sample walk-forward experiment against SPY.

The model is intentionally modest: L2 logistic regression over market features.
Its value is not complexity, but the fact that every training date precedes its
test date and the complete protocol is published with the output.
"""

from __future__ import annotations

import json
import hashlib
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from research_core import fit_logistic, fit_platt, performance_metrics, reliability_bins
from v5_core import risk_budget


ROOT = Path(__file__).resolve().parents[1]
FEATURE_FILE = ROOT / "research_work" / "feature_store.json"
OUTPUT_FILE = ROOT / "public" / "data" / "backtest.json"
HISTORY_FILE = ROOT / "public" / "data" / "backtest_history.json"
COST = 0.001
REBALANCE = 60


def measurement_fingerprint(payload: dict[str, object]) -> str:
    """Identify the mathematical result, ignoring its generation timestamp."""
    material = {
        "period": payload.get("period"),
        "horizonSessions": payload.get("horizonSessions"),
        "rebalanceSessions": payload.get("rebalanceSessions"),
        "transactionCostBps": payload.get("transactionCostBps"),
        "metrics": payload.get("metrics"),
        "equity": payload.get("equity"),
        "calibration": payload.get("calibration"),
    }
    canonical = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def append_measurement(history: dict[str, object], payload: dict[str, object]) -> str:
    fingerprint = measurement_fingerprint(payload)
    snapshots = history.setdefault("snapshots", [])
    if not isinstance(snapshots, list):
        raise ValueError("backtest_history.json contiene snapshots inválidos")
    if not any(isinstance(item, dict) and item.get("fingerprint") == fingerprint for item in snapshots):
        universe = payload.get("universe", [])
        snapshots.append({
            "fingerprint": fingerprint,
            "archivedAt": str(payload.get("generatedAt", pd.Timestamp.utcnow().isoformat())),
            "universeSize": len(universe) if isinstance(universe, list) else 0,
            "backtest": payload,
        })
    return fingerprint


def publish_with_history(output: dict[str, object]) -> None:
    history: dict[str, object] = {
        "schemaVersion": 1,
        "generatedAt": str(output["generatedAt"]),
        "mode": "live",
        "policy": "Cada resultado matemáticamente distinto se conserva por huella; ninguna medición anterior se reescribe.",
        "currentFingerprint": "",
        "snapshots": [],
    }
    if HISTORY_FILE.exists():
        loaded = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            history.update(loaded)
    if OUTPUT_FILE.exists():
        previous = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
        if isinstance(previous, dict) and previous.get("mode") == "live":
            append_measurement(history, previous)
    current_fingerprint = append_measurement(history, output)
    history.update({
        "schemaVersion": 1,
        "generatedAt": str(output["generatedAt"]),
        "mode": "live",
        "currentFingerprint": current_fingerprint,
    })
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def temporal_years(frame: pd.DataFrame) -> Iterable[tuple[int, pd.DataFrame, pd.DataFrame]]:
    years = sorted(frame["date"].dt.year.unique())
    for year in years[3:]:
        train = frame[frame["date"].dt.year < year].copy()
        test = frame[frame["date"].dt.year == year].copy()
        if len(train) >= 500 and len(test) >= 80:
            yield int(year), train, test


def technical_rank(frame: pd.DataFrame) -> pd.Series:
    rsi_bonus = np.where(frame["rsi_14"].between(.45, .68), 10, np.where((frame["rsi_14"] > .78) | (frame["rsi_14"] < .25), -10, 0))
    return (
        50
        + np.where(frame["sma_200_ratio"] > 0, 16, -16)
        + np.where(frame["sma_50_ratio"] > 0, 9, -7)
        + np.where(frame["ret_60"] > .05, 8, np.where(frame["ret_60"] < -.05, -8, 0))
        + rsi_bonus
        - np.clip(frame["vol_60"] - .25, 0, 1) * 18
    )


def heuristic_rank(frame: pd.DataFrame) -> pd.Series:
    technical = technical_rank(frame)
    relative = np.clip((frame["ret_60"] - frame["spy_ret_60"]) * 100, -20, 20)
    risk = 75 - np.clip(frame["vol_60"], 0, 1) * 35 + np.clip(frame["drawdown_252"], -.8, 0) * 20
    return .60 * technical + .20 * (50 + relative) + .20 * risk


def sampled_rebalance_dates(frame: pd.DataFrame) -> list[pd.Timestamp]:
    dates = sorted(frame["date"].drop_duplicates())
    return [dates[index] for index in range(0, len(dates), REBALANCE)]


def cumulative_points(dates: list[str], returns: dict[str, list[float]]) -> list[dict[str, float | str]]:
    equity = {key: 1.0 for key in returns}
    output: list[dict[str, float | str]] = []
    for index, date in enumerate(dates):
        point: dict[str, float | str] = {"date": date}
        for key, values in returns.items():
            equity[key] *= 1 + values[index]
            point[key] = round(equity[key], 6)
        output.append(point)
    return output


def drawdown_points(equity: list[dict[str, float | str]], keys: list[str]) -> list[dict[str, float | str]]:
    peaks = {key: 1.0 for key in keys}
    output = []
    for point in equity:
        row: dict[str, float | str] = {"date": str(point["date"])}
        for key in keys:
            value = float(point[key])
            peaks[key] = max(peaks[key], value)
            row[key] = round(value / peaks[key] - 1, 6)
        output.append(row)
    return output


def annual_returns(dates: list[str], returns: dict[str, list[float]]) -> list[dict[str, float | str]]:
    years = sorted({date[:4] for date in dates})
    output = []
    for year in years:
        indices = [index for index, date in enumerate(dates) if date.startswith(year)]
        row: dict[str, float | str] = {"year": year}
        for key, values in returns.items():
            row[key] = round(float(np.prod([1 + values[index] for index in indices]) - 1), 6)
        output.append(row)
    return output


def main() -> None:
    payload = json.loads(FEATURE_FILE.read_text(encoding="utf-8"))
    features: list[str] = payload["features"]
    frame = pd.DataFrame(payload["rows"])
    frame["date"] = pd.to_datetime(frame["date"])
    required = features + ["label_excess_positive", "forward_return_60", "forward_spy_60", "forward_excess_60"]
    frame[required] = frame[required].apply(pd.to_numeric, errors="coerce")
    usable = frame.dropna(subset=required).sort_values(["date", "ticker"]).copy()
    if usable.empty:
        raise RuntimeError("El feature store no contiene objetivos futuros suficientes")

    predictions: list[pd.DataFrame] = []
    split_manifest: list[dict[str, object]] = []
    for year, train, test in temporal_years(usable):
        cutoff = train["date"].quantile(.80)
        fit = train[train["date"] <= cutoff]
        calibration = train[train["date"] > cutoff]
        if len(fit) < 300 or len(calibration) < 80:
            continue
        model = fit_logistic(fit[features].to_numpy(float), fit["label_excess_positive"].to_numpy(float))
        calibrator = fit_platt(model.decision_function(calibration[features].to_numpy(float)), calibration["label_excess_positive"].to_numpy(float))
        predicted = test.copy()
        predicted["probability"] = calibrator.transform(model.decision_function(test[features].to_numpy(float)))
        predicted["technical_rank"] = technical_rank(predicted)
        predicted["heuristic_rank"] = heuristic_rank(predicted)
        predictions.append(predicted)
        split_manifest.append({
            "testYear": year,
            "trainStart": fit["date"].min().date().isoformat(),
            "trainEnd": fit["date"].max().date().isoformat(),
            "calibrationStart": calibration["date"].min().date().isoformat(),
            "calibrationEnd": calibration["date"].max().date().isoformat(),
            "testStart": test["date"].min().date().isoformat(),
            "testEnd": test["date"].max().date().isoformat(),
            "trainRows": int(len(fit)),
            "testRows": int(len(test)),
        })
    if not predictions:
        raise RuntimeError("No se pudo construir ningún split walk-forward")

    predicted = pd.concat(predictions, ignore_index=True).sort_values(["date", "ticker"])
    returns = {key: [] for key in ("spy", "technical", "heuristic", "statistical", "riskControlled")}
    dates: list[str] = []
    risk_allocations: list[dict[str, object]] = []
    for year in sorted(predicted["date"].dt.year.unique()):
        yearly = predicted[predicted["date"].dt.year == year]
        for date in sampled_rebalance_dates(yearly):
            cross_section = yearly[yearly["date"] == date].dropna(subset=["forward_return_60", "forward_spy_60"])
            if len(cross_section) < 3:
                continue
            dates.append(date.date().isoformat())
            returns["spy"].append(float(cross_section["forward_spy_60"].median()))
            for key, rank in (("technical", "technical_rank"), ("heuristic", "heuristic_rank"), ("statistical", "probability")):
                chosen = cross_section.nlargest(min(3, len(cross_section)), rank)
                returns[key].append(float(chosen["forward_return_60"].mean()) - COST)
            # Challenger V5: at least five names, maximum 20% per position,
            # volatility target, CVaR proxy and defensive SPY regime.
            selected = cross_section.nlargest(min(5, len(cross_section)), "probability")
            annual_volatility = float(selected["vol_60"].median())
            spy_above_sma200 = bool(float(cross_section["spy_sma_200_ratio"].median()) >= 0)
            budget = risk_budget(annual_volatility, spy_above_sma200)
            per_position = min(float(budget["exposure"]) / len(selected), 0.20)
            gross_exposure = per_position * len(selected)
            controlled_return = gross_exposure * float(selected["forward_return_60"].mean()) - COST * gross_exposure
            returns["riskControlled"].append(controlled_return)
            risk_allocations.append({
                "date": date.date().isoformat(),
                "tickers": selected["ticker"].astype(str).tolist(),
                "grossExposure": round(gross_exposure, 6),
                "cashWeight": round(1 - gross_exposure, 6),
                "maxPositionWeight": round(per_position, 6),
                "spyAboveSma200": spy_above_sma200,
                "estimatedAnnualVolatility": round(annual_volatility, 6),
                "dailyCvarProxy": budget["dailyCvarProxy"],
            })

    if len(dates) < 4:
        raise RuntimeError("Muy pocos periodos fuera de muestra para publicar")
    metrics = {key: performance_metrics(values, returns["spy"], periods_per_year=4) for key, values in returns.items()}
    # A benchmark regressed against itself is exactly alpha 0, beta 1.
    metrics["spy"]["alpha"] = 0.0
    metrics["spy"]["beta"] = 1.0
    equity = cumulative_points(dates, returns)
    labels = predicted["label_excess_positive"].astype(int).to_numpy()
    probabilities = predicted["probability"].to_numpy(float)
    brier = float(np.mean((probabilities - labels) ** 2))
    accuracy = float(np.mean((probabilities >= .5) == labels))
    output = {
        "generatedAt": pd.Timestamp.utcnow().isoformat(),
        "mode": "live",
        "hypothesis": "Un modelo transparente puede estimar la probabilidad de superar al SPY a 60 sesiones sin usar información futura.",
        "horizonSessions": 60,
        "rebalanceSessions": REBALANCE,
        "transactionCostBps": int(COST * 10_000),
        "universe": sorted(usable["ticker"].astype(str).unique().tolist()),
        "period": {"start": dates[0], "end": dates[-1]},
        "methodology": {
            "validation": "Walk-forward anual con entrenamiento, calibración y prueba estrictamente ordenados en el tiempo.",
            "models": {
                "spy": "Comprar y mantener SPY",
                "technical": "Regla técnica determinista",
                "heuristic": "Score transparente de mercado y riesgo",
                "statistical": "Regresión logística L2 con calibración de Platt temporal",
                "riskControlled": "Probabilidad estadística con objetivo de volatilidad, CVaR, régimen SMA 200, 20% máximo por posición y efectivo",
            },
            "safeguards": [
                "La fecha máxima de entrenamiento es anterior al inicio de calibración y prueba.",
                "La normalización se calcula exclusivamente con filas de entrenamiento.",
                "El objetivo futuro nunca aparece dentro de la matriz de features.",
                "Se descuentan 10 puntos básicos en cada rebalanceo de las estrategias.",
                "El challenger limita cada posición a 20% y mantiene efectivo cuando el presupuesto de riesgo no permite exposición completa.",
                "Los splits y sus fechas se guardan dentro del artefacto.",
            ],
            "limitations": [
                "Los fundamentales y noticias no se retroalimentan históricamente sin archivos point-in-time confiables.",
                "El universo ampliado sigue compuesto por empresas vigentes hoy; existe riesgo de sesgo de supervivencia.",
                "Las observaciones de 60 sesiones son menos numerosas que las observaciones diarias.",
                "El backtest es evidencia exploratoria y no una garantía de rentabilidad futura.",
            ],
            "features": features,
            "splits": split_manifest,
        },
        "metrics": metrics,
        "equity": equity,
        "drawdown": drawdown_points(equity, list(returns)),
        "annualReturns": annual_returns(dates, returns),
        "calibration": {
            "brierScore": round(brier, 6),
            "accuracy": round(accuracy, 6),
            "sampleSize": int(len(labels)),
            "bins": reliability_bins(probabilities, labels, bins=5),
        },
        "riskControls": {
            "targetAnnualVolatility": 0.12,
            "dailyCvarLimit": 0.02,
            "maximumPositionWeight": 0.20,
            "defensiveExposureBelowSpySma200": 0.35,
            "cashReturnAssumption": 0.0,
            "allocations": risk_allocations,
        },
    }
    publish_with_history(output)
    print(f"Backtest: {len(dates)} rebalanceos, {len(labels)} predicciones, Brier {brier:.4f}.")


if __name__ == "__main__":
    main()
