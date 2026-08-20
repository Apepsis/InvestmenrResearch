"""Generate the public risk model consumed locally by the portfolio screen."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PRICE_FILE = ROOT / "research_work" / "prices.json"
OUTPUT_FILE = ROOT / "public" / "data" / "risk_model.json"
WINDOW = 756


def price_series(payload: dict[str, object]) -> dict[str, pd.Series]:
    output: dict[str, pd.Series] = {}
    for ticker, values in payload["prices"].items():
        dates = pd.to_datetime(values["dates"])
        close = pd.Series(values["close"], index=dates, dtype=float).sort_index()
        output[ticker] = close[~close.index.duplicated(keep="last")]
    return output


def period_return(series: pd.Series, start: str, end: str) -> float | None:
    window = series[(series.index >= pd.Timestamp(start)) & (series.index <= pd.Timestamp(end))]
    if len(window) < 2:
        return None
    return float(window.iloc[-1] / window.iloc[0] - 1)


def clean(value: float, fallback: float = 0.0) -> float:
    return round(float(value), 7) if math.isfinite(float(value)) else fallback


def main() -> None:
    payload = json.loads(PRICE_FILE.read_text(encoding="utf-8"))
    prices = price_series(payload)
    returns = pd.concat({ticker: series.pct_change() for ticker, series in prices.items()}, axis=1).sort_index().tail(WINDOW).dropna(how="all")
    if "SPY" not in returns:
        raise RuntimeError("SPY es obligatorio para calcular beta")
    tickers = sorted(returns.columns)
    correlation = returns.corr(min_periods=60)
    spy_variance = float(returns["SPY"].var())
    beta = {
        ticker: 1.0 if ticker == "SPY" else clean(returns[ticker].cov(returns["SPY"]) / spy_variance if spy_variance else 0)
        for ticker in tickers
    }
    annual_volatility = {ticker: clean(returns[ticker].std() * np.sqrt(252)) for ticker in tickers}

    covid = {ticker: period_return(prices[ticker], "2020-02-19", "2020-03-23") for ticker in tickers}
    rates_2022 = {ticker: period_return(prices[ticker], "2022-01-03", "2022-10-12") for ticker in tickers}
    scenarios = [
        {
            "id": "market-20",
            "label": "Mercado -20%",
            "description": "Shock hipotético proporcional a la beta histórica frente a SPY.",
            "shocks": {ticker: clean(-0.20 * beta[ticker]) for ticker in tickers},
        },
        {
            "id": "covid-2020",
            "label": "Estrés histórico 2020",
            "description": "Retorno observado entre 19-feb-2020 y 23-mar-2020; no recrea todos los detalles de la crisis.",
            "shocks": {ticker: clean(covid[ticker]) for ticker in tickers if covid[ticker] is not None},
        },
        {
            "id": "rates-2022",
            "label": "Estrés de tasas 2022",
            "description": "Retorno observado entre 03-ene-2022 y 12-oct-2022.",
            "shocks": {ticker: clean(rates_2022[ticker]) for ticker in tickers if rates_2022[ticker] is not None},
        },
        {
            "id": "volatility-spike",
            "label": "Shock de volatilidad",
            "description": "Pérdida hipotética equivalente a dos desviaciones estándar diarias por activo.",
            "shocks": {ticker: clean(-2 * annual_volatility[ticker] / np.sqrt(252)) for ticker in tickers},
        },
        {
            "id": "single-30",
            "label": "Mayor posición -30%",
            "description": "El navegador aplica una caída de 30% a la posición con mayor peso.",
            "shocks": {},
        },
    ]
    output = {
        "generatedAt": pd.Timestamp.utcnow().isoformat(),
        "mode": "live",
        "windowSessions": int(len(returns)),
        "tickers": tickers,
        "dailyReturns": {
            ticker: [clean(value) for value in returns[ticker].dropna().tail(WINDOW).tolist()]
            for ticker in tickers
        },
        "correlation": {
            row: {column: clean(correlation.loc[row, column]) for column in tickers}
            for row in tickers
        },
        "beta": beta,
        "annualVolatility": annual_volatility,
        "stressScenarios": scenarios,
        "methodology": {
            "var": "Percentil empírico 5% de retornos diarios del portafolio.",
            "cvar": "Promedio de retornos iguales o inferiores al VaR 95%.",
            "correlation": "Correlación de Pearson con observaciones pareadas.",
            "warning": "Métricas históricas y escenarios; no constituyen una pérdida máxima ni una predicción.",
        },
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Risk model: {len(tickers)} activos, {len(returns)} sesiones.")


if __name__ == "__main__":
    main()
