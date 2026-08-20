"""Create a point-in-time market feature store for temporal validation.

Only features computable from information available on each date are included.
The future 60-session return is stored as a target and is never passed to the
model as an input.  Fundamentals and news are intentionally excluded from the
historical model until reliable point-in-time archives exist.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from research_core import rsi


ROOT = Path(__file__).resolve().parents[1]
TICKERS_FILE = ROOT / "data" / "tickers.json"
WORK_DIR = ROOT / "research_work"
FEATURE_FILE = WORK_DIR / "feature_store.json"
PRICE_FILE = WORK_DIR / "prices.json"
HORIZON = 60


def download_history(symbol: str) -> pd.DataFrame:
    frame = yf.download(symbol, period="10y", interval="1d", auto_adjust=True, progress=False, threads=False)
    if frame.empty:
        raise RuntimeError(f"Sin precios para {symbol}")
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    required = {"Close", "Volume"}
    if not required.issubset(frame.columns):
        raise RuntimeError(f"{symbol}: columnas incompletas")
    output = frame[["Close", "Volume"]].copy()
    output.index = pd.to_datetime(output.index).tz_localize(None)
    output = output[~output.index.duplicated(keep="last")].sort_index()
    output["Close"] = pd.to_numeric(output["Close"], errors="coerce")
    output["Volume"] = pd.to_numeric(output["Volume"], errors="coerce")
    return output.dropna(subset=["Close"])


def market_features(frame: pd.DataFrame, spy: pd.Series) -> pd.DataFrame:
    close = frame["Close"].astype(float)
    volume = frame["Volume"].astype(float)
    daily = close.pct_change()
    aligned_spy = spy.reindex(close.index).ffill()
    spy_daily = aligned_spy.pct_change()
    rolling_covariance = daily.rolling(60).cov(spy_daily)
    rolling_variance = spy_daily.rolling(60).var()
    rolling_peak = close.rolling(252, min_periods=60).max()
    feature = pd.DataFrame(index=close.index)
    feature["ret_5"] = close.pct_change(5)
    feature["ret_20"] = close.pct_change(20)
    feature["ret_60"] = close.pct_change(60)
    feature["sma_50_ratio"] = close / close.rolling(50).mean() - 1
    feature["sma_200_ratio"] = close / close.rolling(200).mean() - 1
    feature["rsi_14"] = rsi(close) / 100
    feature["vol_20"] = daily.rolling(20).std() * np.sqrt(252)
    feature["vol_60"] = daily.rolling(60).std() * np.sqrt(252)
    feature["drawdown_252"] = close / rolling_peak - 1
    feature["volume_z_20"] = (volume - volume.rolling(20).mean()) / volume.rolling(20).std().replace(0, np.nan)
    feature["spy_ret_20"] = aligned_spy.pct_change(20)
    feature["spy_ret_60"] = aligned_spy.pct_change(60)
    feature["beta_60"] = rolling_covariance / rolling_variance.replace(0, np.nan)
    feature["forward_return_60"] = close.shift(-HORIZON) / close - 1
    feature["forward_spy_60"] = aligned_spy.shift(-HORIZON) / aligned_spy - 1
    feature["forward_excess_60"] = feature["forward_return_60"] - feature["forward_spy_60"]
    feature["label_excess_positive"] = (feature["forward_excess_60"] > 0).astype(float)
    feature.loc[feature["forward_excess_60"].isna(), "label_excess_positive"] = np.nan
    return feature.replace([np.inf, -np.inf], np.nan)


def serializable(value: object) -> object:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return None
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def main() -> None:
    metadata = json.loads(TICKERS_FILE.read_text(encoding="utf-8"))
    symbols = [item["ticker"] for item in metadata]
    if "SPY" not in symbols:
        symbols.append("SPY")
    histories: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}
    for symbol in symbols:
        try:
            histories[symbol] = download_history(symbol)
        except Exception as exc:  # noqa: BLE001 - failures are isolated and published
            errors[symbol] = f"{type(exc).__name__}: {str(exc)[:160]}"
    if "SPY" not in histories:
        raise RuntimeError(f"SPY es obligatorio para el benchmark. Errores: {errors}")
    if len(histories) < 3:
        raise RuntimeError(f"Cobertura insuficiente. Errores: {errors}")

    spy = histories["SPY"]["Close"]
    rows: list[dict[str, object]] = []
    for symbol, frame in histories.items():
        if symbol == "SPY":
            continue
        features = market_features(frame, spy)
        for date, record in features.iterrows():
            row = {"date": date.date().isoformat(), "ticker": symbol}
            row.update({str(key): serializable(value) for key, value in record.items()})
            rows.append(row)

    price_payload = {
        "generatedAt": pd.Timestamp.utcnow().isoformat(),
        "errors": errors,
        "prices": {
            symbol: {
                "dates": [date.date().isoformat() for date in frame.index],
                "close": [round(float(value), 6) for value in frame["Close"]],
            }
            for symbol, frame in histories.items()
        },
    }
    feature_payload = {
        "generatedAt": pd.Timestamp.utcnow().isoformat(),
        "horizonSessions": HORIZON,
        "features": [
            "ret_5", "ret_20", "ret_60", "sma_50_ratio", "sma_200_ratio", "rsi_14",
            "vol_20", "vol_60", "drawdown_252", "volume_z_20", "spy_ret_20", "spy_ret_60", "beta_60",
        ],
        "target": "label_excess_positive",
        "rows": rows,
        "errors": errors,
    }
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    PRICE_FILE.write_text(json.dumps(price_payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    FEATURE_FILE.write_text(json.dumps(feature_payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(f"Feature store: {len(rows)} filas, {len(histories)} series, {len(errors)} errores.")


if __name__ == "__main__":
    main()
