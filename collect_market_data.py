"""Build the static market dataset consumed by the GitHub Pages application.

The collector uses free/public endpoints only. Every output record carries a
timestamp and source metadata. Failures are isolated per ticker so one provider
problem does not corrupt the complete dataset.
"""

from __future__ import annotations

import json
import io
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
import re

import feedparser
import numpy as np
import pandas as pd
import requests
import yfinance as yf

from research_core import score_explanation


ROOT = Path(__file__).resolve().parents[1]
TICKER_FILE = ROOT / "data" / "tickers.json"
OUTPUT_FILE = ROOT / "public" / "data" / "market.json"
WEIGHTS = {"technical": 0.25, "fundamental": 0.30, "news": 0.15, "macro": 0.15, "risk": 0.15}
USER_AGENT = os.getenv("SEC_USER_AGENT") or "investment-research-agent/1.0 contact@example.com"


def finite(value: Any, fallback: float | None = None) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else fallback
    except (TypeError, ValueError):
        return fallback


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def tone(value: float, positive: float = 60.0, negative: float = 40.0) -> str:
    if value >= positive:
        return "positive"
    if value <= negative:
        return "negative"
    return "neutral"


def display_percent(value: float | None) -> str:
    return "N/D" if value is None else f"{value * 100:+.1f}%"


def fred_series(series_id: str) -> pd.Series:
    urls = [
        f"https://fredgraph.stlouisfed.org/graph/fredgraph.csv?id={series_id}",
        f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",
    ]
    last_error: Exception | None = None
    response = None
    for url in urls:
        for attempt in range(3):
            try:
                response = requests.get(url, timeout=40, headers={"User-Agent": USER_AGENT, "Accept": "text/csv"})
                response.raise_for_status()
                if len(response.text) < 20:
                    raise ValueError("Respuesta FRED vacía")
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                time.sleep(.6 * (attempt + 1))
        if response is not None and response.ok and len(response.text) >= 20:
            break
    if response is None or not response.ok:
        raise RuntimeError(f"FRED no disponible: {last_error}")
    frame = pd.read_csv(io.StringIO(response.text))
    value_column = frame.columns[-1]
    frame[value_column] = pd.to_numeric(frame[value_column], errors="coerce")
    frame = frame.dropna(subset=[value_column])
    series = pd.Series(frame[value_column].values, index=pd.to_datetime(frame.iloc[:, 0]))
    return series.sort_index()


def collect_macro(previous: dict[str, dict[str, Any]] | None = None) -> tuple[dict[str, dict[str, Any]], float]:
    definitions = {
        "fedRate": ("FEDFUNDS", "Tasa FED", "%"),
        "cpi": ("CPIAUCSL", "Inflacion EE. UU.", "%"),
        "unemployment": ("UNRATE", "Desempleo EE. UU.", "%"),
        "dollar": ("DTWEXBGS", "Indice dolar", "indice"),
        "oil": ("DCOILWTICO", "Petroleo WTI", "USD"),
    }
    output: dict[str, dict[str, Any]] = {}
    raw: dict[str, float | None] = {}
    for key, (series_id, label, unit) in definitions.items():
        try:
            series = fred_series(series_id)
            value = finite(series.iloc[-1])
            if key == "cpi" and len(series) >= 13:
                value = finite(series.pct_change(12).iloc[-1] * 100)
            raw[key] = value
            output[key] = {
                "label": label,
                "value": round(value, 3) if value is not None else None,
                "unit": unit,
                "asOf": series.index[-1].date().isoformat(),
                "source": f"FRED:{series_id}",
            }
        except Exception as exc:  # noqa: BLE001 - provider isolation is intentional
            old = (previous or {}).get(key, {})
            old_value = finite(old.get("value"))
            raw[key] = old_value
            output[key] = {
                "label": label,
                "value": old_value,
                "unit": unit,
                "asOf": old.get("asOf", "No disponible"),
                "source": f"FRED:{series_id}" + (" · último valor verificado" if old_value is not None else ""),
                "error": type(exc).__name__,
                "stale": old_value is not None,
            }

    score = 50.0
    if raw.get("fedRate") is not None:
        score += 8 if raw["fedRate"] < 4 else -5 if raw["fedRate"] > 5 else 0
    if raw.get("cpi") is not None:
        score += 10 if raw["cpi"] < 3 else -10 if raw["cpi"] > 4 else 0
    if raw.get("unemployment") is not None:
        score += 7 if raw["unemployment"] < 5 else -8 if raw["unemployment"] > 6 else 0
    return output, clamp(score)


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    relative_strength = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + relative_strength))


def technical_analysis(history: pd.DataFrame) -> tuple[float, float, list[dict[str, str]], list[float], float, float]:
    close = history["Close"].dropna().astype(float)
    price = finite(close.iloc[-1], 0.0) or 0.0
    sma50 = finite(close.rolling(50).mean().iloc[-1])
    sma200 = finite(close.rolling(200).mean().iloc[-1])
    rsi14 = finite(rsi(close).iloc[-1])
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_value = finite((ema12 - ema26).iloc[-1], 0.0) or 0.0
    daily_returns = close.pct_change().dropna()
    volatility = finite(daily_returns.std() * math.sqrt(252), 0.5) or 0.5
    drawdown = close / close.cummax() - 1
    max_drawdown = finite(drawdown.min(), -0.5) or -0.5
    change_pct = finite(close.pct_change().iloc[-1] * 100, 0.0) or 0.0

    score = 50.0
    score += 13 if sma200 and price > sma200 else -13
    score += 10 if sma50 and sma200 and sma50 > sma200 else -8
    if rsi14 is not None:
        score += 9 if 45 <= rsi14 <= 68 else -9 if rsi14 >= 78 or rsi14 <= 25 else 0
    score += 7 if macd_value > 0 else -5
    three_month_return = finite(close.pct_change(63).iloc[-1], 0.0) or 0.0
    score += 8 if three_month_return > 0.05 else -8 if three_month_return < -0.05 else 0

    sampled = close.tail(90)
    if len(sampled) > 18:
        indices = np.linspace(0, len(sampled) - 1, 18, dtype=int)
        sampled = sampled.iloc[indices]
    chart = [round(float(value), 3) for value in sampled.tolist()]

    indicators = [
        {
            "label": "Tendencia",
            "value": "Sobre SMA 200" if sma200 and price > sma200 else "Bajo SMA 200" if sma200 else "N/D",
            "interpretation": "La media de 200 sesiones define el contexto de largo plazo.",
            "tone": "positive" if sma200 and price > sma200 else "negative" if sma200 else "neutral",
        },
        {
            "label": "RSI 14",
            "value": "N/D" if rsi14 is None else f"{rsi14:.1f}",
            "interpretation": "Momentum relativo; extremos requieren confirmacion adicional.",
            "tone": "positive" if rsi14 and 45 <= rsi14 <= 68 else "negative" if rsi14 and (rsi14 >= 78 or rsi14 <= 25) else "neutral",
        },
        {
            "label": "MACD",
            "value": "Positivo" if macd_value > 0 else "Negativo",
            "interpretation": "Diferencia entre EMA 12 y EMA 26; no se usa como senal aislada.",
            "tone": "positive" if macd_value > 0 else "negative",
        },
        {
            "label": "Drawdown maximo",
            "value": f"{max_drawdown * 100:.1f}%",
            "interpretation": "Mayor caida desde un maximo durante la ventana de cinco anos.",
            "tone": "negative" if max_drawdown < -0.30 else "neutral",
        },
    ]
    return clamp(score), price, indicators, chart, change_pct, max_drawdown


def sec_revenue_growth(cik: str | None) -> float | None:
    if not cik:
        return None
    response = requests.get(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"},
        timeout=30,
    )
    response.raise_for_status()
    facts = response.json().get("facts", {}).get("us-gaap", {})
    concept = next((facts.get(name) for name in ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet") if facts.get(name)), None)
    if not concept:
        return None
    entries = concept.get("units", {}).get("USD", [])
    annual = [entry for entry in entries if entry.get("form") == "10-K" and entry.get("fp") == "FY" and entry.get("fy") and entry.get("val")]
    latest_by_year: dict[int, dict[str, Any]] = {}
    for entry in annual:
        year = int(entry["fy"])
        if year not in latest_by_year or entry.get("filed", "") > latest_by_year[year].get("filed", ""):
            latest_by_year[year] = entry
    years = sorted(latest_by_year)
    if len(years) < 2:
        return None
    previous = finite(latest_by_year[years[-2]]["val"])
    current = finite(latest_by_year[years[-1]]["val"])
    if not previous or current is None:
        return None
    return current / previous - 1


def fundamental_analysis(ticker: yf.Ticker, cik: str | None) -> tuple[float, list[dict[str, str]], int]:
    try:
        info = ticker.info or {}
    except Exception:  # noqa: BLE001
        info = {}
    revenue_growth = finite(info.get("revenueGrowth"))
    try:
        sec_growth = sec_revenue_growth(cik)
        if sec_growth is not None:
            revenue_growth = sec_growth
    except Exception:  # noqa: BLE001
        pass
    earnings_growth = finite(info.get("earningsGrowth"))
    margin = finite(info.get("profitMargins"))
    free_cash_flow = finite(info.get("freeCashflow"))
    debt_to_equity = finite(info.get("debtToEquity"))
    current_ratio = finite(info.get("currentRatio"))
    forward_pe = finite(info.get("forwardPE"))

    signals: list[float] = []
    if revenue_growth is not None:
        signals.append(clamp(50 + revenue_growth * 180))
    if earnings_growth is not None:
        signals.append(clamp(50 + earnings_growth * 140))
    if margin is not None:
        signals.append(clamp(45 + margin * 160))
    if free_cash_flow is not None:
        signals.append(72 if free_cash_flow > 0 else 25)
    if debt_to_equity is not None:
        signals.append(clamp(82 - debt_to_equity * 0.25))
    if current_ratio is not None:
        signals.append(clamp(42 + min(current_ratio, 3) * 16))
    if forward_pe is not None:
        signals.append(72 if 0 < forward_pe < 20 else 58 if forward_pe < 35 else 38)
    score = float(np.mean(signals)) if signals else 50.0

    indicators = [
        {"label": "Ingresos", "value": display_percent(revenue_growth), "interpretation": "Crecimiento anual; SEC se prioriza cuando esta disponible.", "tone": tone(clamp(50 + (revenue_growth or 0) * 180))},
        {"label": "Margen neto", "value": display_percent(margin), "interpretation": "Rentabilidad despues de costos, intereses e impuestos.", "tone": tone(clamp(45 + (margin or 0) * 160))},
        {"label": "Flujo de caja libre", "value": "Positivo" if free_cash_flow and free_cash_flow > 0 else "Negativo / N/D", "interpretation": "Caja despues de inversiones operativas.", "tone": "positive" if free_cash_flow and free_cash_flow > 0 else "neutral" if free_cash_flow is None else "negative"},
        {"label": "Valoracion", "value": "N/D" if forward_pe is None else f"P/E {forward_pe:.1f}", "interpretation": "Multiplo esperado; requiere comparacion con sector y crecimiento.", "tone": "positive" if forward_pe and forward_pe < 20 else "negative" if forward_pe and forward_pe > 35 else "neutral"},
    ]
    return clamp(score), indicators, len(signals)


POSITIVE_WORDS = {"beat", "growth", "profit", "record", "upgrade", "expands", "surge", "approval", "partnership", "launch", "wins", "raises"}
NEGATIVE_WORDS = {"miss", "lawsuit", "probe", "downgrade", "decline", "cuts", "layoff", "ban", "recall", "fraud", "investigation", "warning"}


def title_tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def title_similarity(left: str, right: str) -> float:
    first, second = title_tokens(left), title_tokens(right)
    return len(first & second) / len(first | second) if first | second else 0.0


def classify_news(title: str) -> tuple[str, float, str, str]:
    words = {word.strip(".,:;!?()[]\"").lower() for word in title.split()}
    positive = len(words & POSITIVE_WORDS)
    negative = len(words & NEGATIVE_WORDS)
    sentiment = "positive" if positive > negative else "negative" if negative > positive else "neutral"
    confidence = min(0.85, 0.45 + abs(positive - negative) * 0.13)
    lowered = title.lower()
    if any(word in lowered for word in ("lawsuit", "court", "litigation")):
        event_type, duration = "litigio", "structural"
    elif any(word in lowered for word in ("probe", "ban", "regulator", "regulation")):
        event_type, duration = "regulación", "structural"
    elif any(word in lowered for word in ("earnings", "revenue", "profit", "quarter")):
        event_type, duration = "resultados", "medium"
    elif any(word in lowered for word in ("ceo", "cfo", "executive", "management")):
        event_type, duration = "administración", "medium"
    elif any(word in lowered for word in ("competitor", "competition", "market share")):
        event_type, duration = "competencia", "medium"
    elif any(word in lowered for word in ("launch", "product", "service")):
        event_type, duration = "producto", "medium"
    elif any(word in lowered for word in ("partnership", "acquisition", "merger")):
        event_type, duration = "estratégico", "medium"
    else:
        event_type, duration = "mercado", "temporary"
    return sentiment, confidence, event_type, duration


def collect_news(ticker: str, company: str) -> tuple[list[dict[str, Any]], float]:
    query = quote_plus(f'("{company}" OR {ticker}) stock')
    feed = feedparser.parse(f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en")
    items: list[dict[str, Any]] = []
    values: list[float] = []
    company_tokens = title_tokens(f"{ticker} {company}")
    seen_titles: list[str] = []
    impacts: list[float] = []
    for entry in feed.entries[:16]:
        title = str(entry.get("title", "Sin titulo"))
        if any(title_similarity(title, previous) >= .82 for previous in seen_titles):
            continue
        sentiment, confidence, event_type, duration = classify_news(title)
        tokens = title_tokens(title)
        matched = bool(tokens & company_tokens)
        relevance = min(1.0, .35 + .16 * len(tokens & company_tokens) + (.18 if matched else 0))
        novelty = 1 - max((title_similarity(title, previous) for previous in seen_titles), default=0)
        direction = 1 if sentiment == "positive" else -1 if sentiment == "negative" else 0
        impact = direction * confidence * relevance * novelty
        impacts.append(impact)
        values.append(50 + impact * 42)
        source = entry.get("source", {})
        source_name = source.get("title", "Google News RSS") if isinstance(source, dict) else "Google News RSS"
        items.append({
            "title": title,
            "source": source_name,
            "url": str(entry.get("link", "#")),
            "publishedAt": str(entry.get("published", "Fecha no disponible")),
            "sentiment": sentiment,
            "eventType": event_type,
            "duration": duration,
            "confidence": round(confidence, 2),
            "relevance": round(relevance, 3),
            "novelty": round(novelty, 3),
            "entityMatched": matched,
            "impactWeight": round(impact, 4),
        })
        seen_titles.append(title)
        if len(items) >= 8:
            break
    if not items:
        items.append({"title": "No se recuperaron noticias en esta ejecución", "source": "Pipeline", "url": "#", "publishedAt": datetime.now(timezone.utc).isoformat(), "sentiment": "neutral", "eventType": "disponibilidad", "duration": "temporary", "confidence": 0, "relevance": 0, "novelty": 0, "entityMatched": False, "impactWeight": 0})
    return items, clamp(float(np.mean(values)) if values else 50.0)


def risk_score(volatility: float, max_drawdown: float) -> float:
    score = 88 - min(volatility, 1.2) * 42 - min(abs(max_drawdown), 0.8) * 38
    return clamp(score)


def verdict(score: float) -> str:
    if score >= 80:
        return "Oportunidad interesante"
    if score >= 60:
        return "Analizar entrada"
    if score >= 40:
        return "Mantener vigilancia"
    return "Evitar"


def build_stock(meta: dict[str, Any], macro_score: float, macro_coverage: float) -> dict[str, Any]:
    symbol = meta["ticker"]
    ticker = yf.Ticker(symbol)
    history = yf.download(symbol, period="5y", interval="1d", auto_adjust=True, progress=False, threads=False)
    if history.empty:
        raise RuntimeError("Sin precios historicos")
    if isinstance(history.columns, pd.MultiIndex):
        history.columns = history.columns.get_level_values(0)

    technical_score, price, technical, chart, change_pct, max_drawdown = technical_analysis(history)
    daily = history["Close"].dropna().pct_change().dropna()
    volatility = finite(daily.std() * math.sqrt(252), 0.5) or 0.5
    fundamental_score, fundamental, fundamental_signal_count = fundamental_analysis(ticker, meta.get("cik"))
    news, news_score = collect_news(symbol, meta["name"])
    safety_score = risk_score(volatility, max_drawdown)
    scores = {
        "technical": technical_score,
        "fundamental": fundamental_score,
        "news": news_score,
        "macro": macro_score,
        "risk": safety_score,
    }
    total = sum(scores[key] * WEIGHTS[key] for key in WEIGHTS)
    technical_coverage = min(len(history) / 252, 1)
    fundamental_coverage = min(fundamental_signal_count / 7, 1)
    news_coverage = min(sum(item.get("entityMatched", False) for item in news) / 4, 1)
    data_coverage = .30 * technical_coverage + .35 * fundamental_coverage + .20 * news_coverage + .15 * macro_coverage
    confidence = clamp(data_coverage * 100, 0, 100)
    trend_positive = technical_score >= 60
    fundamentals_positive = fundamental_score >= 60

    thesis = [
        f"La estructura tecnica es {'favorable' if trend_positive else 'mixta o debil'} con score {technical_score:.0f}/100.",
        f"Los fundamentales disponibles resultan {'favorables' if fundamentals_positive else 'insuficientes o exigentes'} con score {fundamental_score:.0f}/100.",
        "La conclusion pondera tecnico, fundamental, noticias, macro y riesgo; ninguna senal aislada decide.",
    ]
    risks = [
        f"Volatilidad anualizada observada: {volatility * 100:.1f}%.",
        f"Drawdown maximo en cinco anos: {max_drawdown * 100:.1f}%.",
        "Noticias, regulacion o expectativas de valoracion pueden cambiar la tesis antes de la siguiente actualizacion.",
    ]
    invalidation = [
        "Deterioro material y repetido de ingresos, margenes o flujo de caja.",
        "Ruptura persistente de la tendencia de largo plazo con volumen elevado.",
        "Evento regulatorio o competitivo que altere estructuralmente la economia del negocio.",
    ]
    committee = [
        {"agent": "Calidad", "focus": "Regla fundamental", "view": "Calidad favorable." if fundamentals_positive else "Calidad aún no concluyente.", "tone": "positive" if fundamentals_positive else "neutral"},
        {"agent": "Valoración", "focus": "Múltiplos", "view": next((item["interpretation"] for item in fundamental if item["label"] == "Valoracion"), "Requiere comparables."), "tone": next((item["tone"] for item in fundamental if item["label"] == "Valoracion"), "neutral")},
        {"agent": "Crecimiento", "focus": "Ingresos y caja", "view": "Crecimiento verificable en los datos disponibles." if fundamental_score >= 58 else "El crecimiento necesita más evidencia.", "tone": "positive" if fundamental_score >= 58 else "neutral"},
        {"agent": "Mercado", "focus": "Regla estadística", "view": "Momentum y tendencia favorables." if trend_positive else "Señales estadísticas sin confirmación.", "tone": "positive" if trend_positive else "neutral"},
        {"agent": "Riesgo", "focus": "Volatilidad y drawdown", "view": "Riesgo controlable con dimensión prudente." if safety_score >= 60 else "Riesgo elevado; reducir tamaño o esperar.", "tone": "positive" if safety_score >= 60 else "negative"},
    ]

    trace = {
        "prices": "Yahoo Finance via yfinance",
        "fundamentals": "SEC EDGAR company facts when available; Yahoo Finance fallback",
        "news": "Google News RSS y fuente original",
        "macro": "FRED",
        "method": "Deterministic weighted score v2 with auditable baseline decomposition",
    }
    explanation = score_explanation(
        scores,
        WEIGHTS,
        {"technical": trace["prices"], "fundamental": trace["fundamentals"], "news": trace["news"], "macro": trace["macro"], "risk": trace["prices"]},
        history.index[-1].date().isoformat(),
        data_coverage,
    )

    return {
        "ticker": symbol,
        "name": meta["name"],
        "sector": meta["sector"],
        "currency": "USD",
        "price": round(price, 3),
        "changePct": round(change_pct, 3),
        "asOf": history.index[-1].date().isoformat(),
        "score": round(total, 1),
        "verdict": verdict(total),
        "source": "live",
        "confidence": round(confidence, 1),
        "scores": {key: round(value, 1) for key, value in scores.items()},
        "history": chart,
        "technical": technical,
        "fundamental": fundamental,
        "thesis": thesis,
        "risks": risks,
        "invalidation": invalidation,
        "committee": committee,
        "news": news,
        "trace": trace,
        "explanation": explanation,
    }


def main() -> None:
    tickers = json.loads(TICKER_FILE.read_text(encoding="utf-8"))
    previous_macro: dict[str, dict[str, Any]] = {}
    if OUTPUT_FILE.exists():
        try:
            previous_macro = json.loads(OUTPUT_FILE.read_text(encoding="utf-8")).get("macro", {})
        except (json.JSONDecodeError, OSError):
            previous_macro = {}
    macro, macro_score = collect_macro(previous_macro)
    macro_coverage = sum(item.get("value") is not None for item in macro.values()) / max(len(macro), 1)
    stocks: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for meta in tickers:
        try:
            stocks[meta["ticker"]] = build_stock(meta, macro_score, macro_coverage)
        except Exception as exc:  # noqa: BLE001
            errors[meta["ticker"]] = f"{type(exc).__name__}: {str(exc)[:160]}"
        time.sleep(0.35)

    if not stocks:
        raise RuntimeError(f"No se genero ningun activo. Errores: {errors}")
    dataset = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "mode": "live",
        "macro": macro,
        "stocks": stocks,
        "errors": errors,
        "methodology": {
            "weights": {key: int(value * 100) for key, value in WEIGHTS.items()},
            "horizon": "1 mes a 1 ano",
            "disclaimer": "Investigacion informativa; no constituye asesoria financiera ni orden de inversion.",
        },
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(dataset, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(OUTPUT_FILE)
    print(f"Generados {len(stocks)} activos; {len(errors)} errores aislados.")


if __name__ == "__main__":
    main()
