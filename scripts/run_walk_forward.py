"""Run an out-of-sample walk-forward experiment against SPY.

The model is intentionally modest: L2 logistic regression over market features.
Its value is not complexity, but the fact that every training date precedes its
test date and the complete protocol is published with the output.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from research_core import fit_logistic, fit_platt, performance_metrics, reliability_bins


ROOT = Path(__file__).resolve().parents[1]
FEATURE_FILE = ROOT / "research_work" / "feature_store.json"
OUTPUT_FILE = ROOT / "public" / "data" / "backtest.json"
COST = 0.001
REBALANCE = 60


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
    returns = {key: [] for key in ("spy", "technical", "heuristic", "statistical")}
    dates: list[str] = []
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
        "period": {"start": dates[0], "end": dates[-1]},
        "methodology": {
            "validation": "Walk-forward anual con entrenamiento, calibración y prueba estrictamente ordenados en el tiempo.",
            "models": {
                "spy": "Comprar y mantener SPY",
                "technical": "Regla técnica determinista",
                "heuristic": "Score transparente de mercado y riesgo",
                "statistical": "Regresión logística L2 con calibración de Platt temporal",
            },
            "safeguards": [
                "La fecha máxima de entrenamiento es anterior al inicio de calibración y prueba.",
                "La normalización se calcula exclusivamente con filas de entrenamiento.",
                "El objetivo futuro nunca aparece dentro de la matriz de features.",
                "Se descuentan 10 puntos básicos en cada rebalanceo de las estrategias.",
                "Los splits y sus fechas se guardan dentro del artefacto.",
            ],
            "limitations": [
                "Los fundamentales y noticias no se retroalimentan históricamente sin archivos point-in-time confiables.",
                "El universo actual es pequeño y está compuesto por empresas que sobreviven hoy; existe riesgo de sesgo de supervivencia.",
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
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Backtest: {len(dates)} rebalanceos, {len(labels)} predicciones, Brier {brier:.4f}.")


if __name__ == "__main__":
    main()
