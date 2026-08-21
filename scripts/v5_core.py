"""Pure helpers for the V5 prediction ledger, governance and alerting.

The functions in this module are deliberately independent from network access
so immutability, maturation and promotion rules can be tested deterministically.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable


IMMUTABLE_PREDICTION_FIELDS = (
    "id",
    "predictionDate",
    "ticker",
    "horizonSessions",
    "probability",
    "uncertainty",
    "initialPrice",
    "modelVersion",
    "dataHash",
)


def canonical_hash(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def prediction_id(date: str, ticker: str, horizon: int, model_version: str) -> str:
    return f"{date}:{ticker.upper()}:{int(horizon)}:{model_version}"


def upsert_immutable_records(existing: Iterable[dict[str, Any]], additions: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Append new predictions without ever rewriting their publication fields."""
    records = [dict(item) for item in existing]
    positions = {str(item.get("id")): index for index, item in enumerate(records)}
    for candidate in additions:
        record_id = str(candidate["id"])
        if record_id in positions:
            current = records[positions[record_id]]
            for field in IMMUTABLE_PREDICTION_FIELDS:
                if field in current and field in candidate and current[field] != candidate[field]:
                    raise ValueError(f"Intento de reescribir {field} en {record_id}")
            continue
        positions[record_id] = len(records)
        records.append(dict(candidate))
    return sorted(records, key=lambda item: (str(item.get("predictionDate", "")), str(item.get("ticker", "")), int(item.get("horizonSessions", 0))))


def evaluate_record(record: dict[str, Any], prices: dict[str, dict[str, list[Any]]]) -> dict[str, Any]:
    """Mature one prediction when exactly `horizonSessions` later observations exist."""
    if record.get("status") == "evaluated":
        return dict(record)
    ticker = str(record["ticker"])
    horizon = int(record["horizonSessions"])
    start_date = str(record["predictionDate"])
    asset = prices.get(ticker)
    spy = prices.get("SPY")
    if not asset or not spy:
        return dict(record)
    asset_dates = [str(value) for value in asset.get("dates", [])]
    try:
        start_index = asset_dates.index(start_date)
    except ValueError:
        return dict(record)
    end_index = start_index + horizon
    if end_index >= len(asset_dates):
        return dict(record)
    end_date = asset_dates[end_index]
    spy_by_date = dict(zip((str(value) for value in spy.get("dates", [])), spy.get("close", [])))
    if start_date not in spy_by_date or end_date not in spy_by_date:
        return dict(record)
    initial_asset = float(record.get("initialPrice") or asset["close"][start_index])
    final_asset = float(asset["close"][end_index])
    initial_spy = float(spy_by_date[start_date])
    final_spy = float(spy_by_date[end_date])
    asset_return = final_asset / initial_asset - 1
    spy_return = final_spy / initial_spy - 1
    excess = asset_return - spy_return
    predicted_positive = float(record["probability"]) >= 0.5
    output = dict(record)
    output.update({
        "status": "evaluated",
        "evaluatedOn": end_date,
        "finalPrice": round(final_asset, 6),
        "assetReturn": round(asset_return, 8),
        "spyReturn": round(spy_return, 8),
        "excessReturn": round(excess, 8),
        "outcome": 1 if excess > 0 else 0,
        "correct": bool(predicted_positive == (excess > 0)),
    })
    return output


def risk_budget(volatility: float, spy_above_sma200: bool, *, target_volatility: float = 0.12, cvar_limit: float = 0.02) -> dict[str, float]:
    """Return an auditable gross-exposure cap with a daily 95% CVaR proxy."""
    annual_volatility = max(float(volatility), 1e-6)
    volatility_cap = min(1.0, target_volatility / annual_volatility)
    daily_cvar_proxy = annual_volatility / (252 ** 0.5) * 2.0627
    cvar_cap = min(1.0, cvar_limit / max(daily_cvar_proxy, 1e-6))
    regime_cap = 1.0 if spy_above_sma200 else 0.35
    exposure = max(0.0, min(volatility_cap, cvar_cap, regime_cap))
    return {
        "exposure": round(exposure, 8),
        "cash": round(1 - exposure, 8),
        "volatilityCap": round(volatility_cap, 8),
        "cvarCap": round(cvar_cap, 8),
        "regimeCap": regime_cap,
        "dailyCvarProxy": round(daily_cvar_proxy * exposure, 8),
    }


def promotion_qualified(champion: dict[str, Any], challenger: dict[str, Any]) -> tuple[bool, dict[str, bool]]:
    checks = {
        "minimumObservations": int(challenger.get("observations", 0)) >= 12,
        "sharpeImprovement": float(challenger.get("sharpe", 0)) >= float(champion.get("sharpe", 0)) + 0.05,
        "drawdownImprovement": float(challenger.get("maxDrawdown", -1)) >= float(champion.get("maxDrawdown", -1)) + 0.05,
        "cagrTolerance": float(challenger.get("cagr", -1)) >= float(champion.get("cagr", 0)) - 0.02,
    }
    return all(checks.values()), checks


def alert_fingerprint(code: str, ticker: str | None = None) -> str:
    return hashlib.sha256(f"{code}:{ticker or 'SYSTEM'}".encode("utf-8")).hexdigest()[:20]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
