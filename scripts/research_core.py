"""Pure quantitative utilities shared by the reproducible research pipeline.

The module deliberately avoids opaque AutoML libraries.  The logistic model,
temporal split, calibration, risk metrics and score decomposition are small
enough to inspect directly and are covered by tests.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


EPSILON = 1e-12


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.astype(float).diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    strength = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + strength))


def sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -35, 35)
    return 1 / (1 + np.exp(-clipped))


@dataclass
class Standardizer:
    mean: np.ndarray
    scale: np.ndarray

    @classmethod
    def fit(cls, values: np.ndarray) -> "Standardizer":
        mean = np.nanmean(values, axis=0)
        scale = np.nanstd(values, axis=0)
        scale = np.where(scale < EPSILON, 1.0, scale)
        return cls(mean=mean, scale=scale)

    def transform(self, values: np.ndarray) -> np.ndarray:
        clean = np.where(np.isfinite(values), values, self.mean)
        return (clean - self.mean) / self.scale


@dataclass
class LogisticModel:
    coefficients: np.ndarray
    intercept: float
    standardizer: Standardizer

    def decision_function(self, values: np.ndarray) -> np.ndarray:
        transformed = self.standardizer.transform(values)
        return transformed @ self.coefficients + self.intercept

    def predict_proba(self, values: np.ndarray) -> np.ndarray:
        return sigmoid(self.decision_function(values))


def fit_logistic(
    values: np.ndarray,
    target: np.ndarray,
    *,
    l2: float = 0.12,
    learning_rate: float = 0.035,
    iterations: int = 900,
) -> LogisticModel:
    """Fit a deterministic L2-regularized logistic regression by gradient descent."""
    x = np.asarray(values, dtype=float)
    y = np.asarray(target, dtype=float)
    if x.ndim != 2 or len(x) != len(y) or len(x) < 8:
        raise ValueError("Se requieren al menos ocho observaciones válidas")
    standardizer = Standardizer.fit(x)
    z = standardizer.transform(x)
    coefficients = np.zeros(z.shape[1], dtype=float)
    positive_rate = float(np.clip(y.mean(), 0.01, 0.99))
    intercept = math.log(positive_rate / (1 - positive_rate))
    for _ in range(iterations):
        probability = sigmoid(z @ coefficients + intercept)
        error = probability - y
        gradient = z.T @ error / len(z) + l2 * coefficients
        intercept_gradient = float(error.mean())
        coefficients -= learning_rate * gradient
        intercept -= learning_rate * intercept_gradient
    return LogisticModel(coefficients=coefficients, intercept=intercept, standardizer=standardizer)


@dataclass
class PlattCalibrator:
    slope: float = 1.0
    intercept: float = 0.0

    def transform(self, logits: np.ndarray) -> np.ndarray:
        return sigmoid(self.slope * np.asarray(logits, dtype=float) + self.intercept)


def fit_platt(logits: np.ndarray, target: np.ndarray, iterations: int = 500) -> PlattCalibrator:
    x = np.asarray(logits, dtype=float)
    y = np.asarray(target, dtype=float)
    if len(x) < 8 or len(np.unique(y)) < 2:
        return PlattCalibrator()
    slope = 1.0
    intercept = 0.0
    for _ in range(iterations):
        probability = sigmoid(slope * x + intercept)
        error = probability - y
        slope -= 0.025 * float(np.mean(error * x))
        intercept -= 0.025 * float(error.mean())
    return PlattCalibrator(slope=slope, intercept=intercept)


def maximum_drawdown(period_returns: Sequence[float]) -> float:
    equity = 1.0
    peak = 1.0
    worst = 0.0
    for value in period_returns:
        equity *= 1 + float(value)
        peak = max(peak, equity)
        worst = min(worst, equity / peak - 1)
    return float(worst)


def regression_alpha_beta(strategy: np.ndarray, benchmark: np.ndarray, periods_per_year: int) -> tuple[float, float]:
    if len(strategy) < 3 or np.var(benchmark) < EPSILON:
        return 0.0, 0.0
    beta = float(np.cov(strategy, benchmark, ddof=1)[0, 1] / np.var(benchmark, ddof=1))
    alpha_period = float(strategy.mean() - beta * benchmark.mean())
    return alpha_period * periods_per_year, beta


def performance_metrics(period_returns: Sequence[float], benchmark_returns: Sequence[float], periods_per_year: int = 4) -> dict[str, float | int]:
    values = np.asarray(list(period_returns), dtype=float)
    benchmark = np.asarray(list(benchmark_returns), dtype=float)
    if not len(values):
        return {key: 0 for key in ("totalReturn", "cagr", "sharpe", "sortino", "maxDrawdown", "volatility", "hitRate", "alpha", "beta", "observations")}
    total = float(np.prod(1 + values) - 1)
    years = max(len(values) / periods_per_year, 1 / periods_per_year)
    cagr = float((max(1 + total, EPSILON) ** (1 / years)) - 1)
    standard_deviation = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    downside = values[values < 0]
    downside_deviation = float(downside.std(ddof=1)) if len(downside) > 1 else 0.0
    sharpe = float(values.mean() / standard_deviation * math.sqrt(periods_per_year)) if standard_deviation > EPSILON else 0.0
    sortino = float(values.mean() / downside_deviation * math.sqrt(periods_per_year)) if downside_deviation > EPSILON else 0.0
    alpha, beta = regression_alpha_beta(values, benchmark[: len(values)], periods_per_year)
    return {
        "totalReturn": total,
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "maxDrawdown": maximum_drawdown(values),
        "volatility": standard_deviation * math.sqrt(periods_per_year),
        "hitRate": float(np.mean(values > 0)),
        "alpha": alpha,
        "beta": beta,
        "observations": int(len(values)),
    }


def reliability_bins(probabilities: Sequence[float], target: Sequence[int], bins: int = 5) -> list[dict[str, float | int]]:
    probability = np.asarray(list(probabilities), dtype=float)
    labels = np.asarray(list(target), dtype=float)
    output: list[dict[str, float | int]] = []
    for index in range(bins):
        low = index / bins
        high = (index + 1) / bins
        mask = (probability >= low) & (probability <= high if index == bins - 1 else probability < high)
        if not mask.any():
            continue
        output.append({
            "predicted": round(float(probability[mask].mean()), 5),
            "observed": round(float(labels[mask].mean()), 5),
            "count": int(mask.sum()),
        })
    return output


def score_explanation(
    scores: dict[str, float],
    weights: dict[str, float],
    sources: dict[str, str],
    as_of: str,
    coverage: float,
) -> dict[str, object]:
    """Decompose a weighted 0–100 score around the neutral baseline of 50."""
    base = 50.0
    contributions = []
    for group, weight in weights.items():
        value = clamp(scores[group])
        contribution = (value - base) * float(weight)
        contributions.append({
            "feature": {
                "technical": "Señales técnicas",
                "fundamental": "Calidad y valoración",
                "news": "Eventos informativos",
                "macro": "Entorno macroeconómico",
                "risk": "Penalización de riesgo",
            }.get(group, group),
            "group": group,
            "rawValue": f"{value:.1f}/100",
            "normalized": round(value, 4),
            "weight": round(float(weight) * 100, 3),
            "contribution": round(contribution, 4),
            "formula": f"({value:.2f} - 50) × {weight:.3f}",
            "source": sources.get(group, "Pipeline"),
            "asOf": as_of,
            "status": "verified" if coverage >= 0.75 else "estimated",
        })
    result = clamp(base + sum(float(item["contribution"]) for item in contributions))
    disagreement = float(np.std(list(scores.values()))) / 100
    half_width = 4 + (1 - clamp(coverage, 0, 1)) * 18 + disagreement * 10
    return {
        "base": base,
        "result": round(result, 3),
        "interval": {"low": round(clamp(result - half_width), 2), "high": round(clamp(result + half_width), 2), "level": 80},
        "dataQuality": round(clamp(coverage, 0, 1) * 100, 2),
        "method": "Neutral-baseline weighted decomposition v2",
        "contributions": contributions,
    }


def portfolio_returns(series: dict[str, Sequence[float]], weights: dict[str, float]) -> np.ndarray:
    available = {ticker: np.asarray(values, dtype=float) for ticker, values in series.items() if ticker in weights and len(values)}
    if not available:
        return np.asarray([], dtype=float)
    length = min(len(values) for values in available.values())
    total_weight = sum(weights[ticker] for ticker in available)
    if total_weight <= 0:
        raise ValueError("Los pesos del portafolio deben sumar un valor positivo")
    return sum(values[-length:] * (weights[ticker] / total_weight) for ticker, values in available.items())


def historical_var_cvar(values: Iterable[float], confidence: float = 0.95) -> tuple[float, float]:
    returns = np.asarray(list(values), dtype=float)
    if not len(returns):
        return 0.0, 0.0
    threshold = float(np.quantile(returns, 1 - confidence))
    tail = returns[returns <= threshold]
    return threshold, float(tail.mean()) if len(tail) else threshold
