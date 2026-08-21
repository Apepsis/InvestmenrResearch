from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from monitor_intraday_alerts import build_intraday_candidates, fresh_price


NOW = datetime(2026, 8, 21, 15, 0, tzinfo=timezone.utc)


def prediction(ticker: str, horizon: int, probability: float, low: float) -> dict:
    return {
        "ticker": ticker,
        "horizonSessions": horizon,
        "probability": probability,
        "uncertainty": {"low": low, "high": min(1.0, probability + .1)},
    }


class IntradayAlertTests(unittest.TestCase):
    def test_stale_quote_is_ignored(self) -> None:
        quote = {"price": 90, "asOf": (NOW - timedelta(minutes=30)).isoformat()}
        self.assertIsNone(fresh_price(quote, NOW))

    def test_large_drop_creates_critical_alert(self) -> None:
        market = {"stocks": {"ABC": {"price": 100}}}
        quotes = {"quotes": {"ABC": {"price": 93, "asOf": NOW.isoformat()}}}
        candidates = build_intraday_candidates(market, {"predictions": []}, quotes, NOW)
        self.assertEqual(candidates[0]["code"], "intraday_price_drop")
        self.assertEqual(candidates[0]["severity"], "critical")

    def test_opportunity_requires_price_move_and_two_strong_horizons(self) -> None:
        market = {"stocks": {"ABC": {"price": 100}}}
        live = {"predictions": [
            prediction("ABC", 20, .70, .55),
            prediction("ABC", 60, .64, .52),
        ]}
        quotes = {"quotes": {"ABC": {"price": 96, "asOf": NOW.isoformat()}}}
        candidates = build_intraday_candidates(market, live, quotes, NOW)
        self.assertEqual([item["code"] for item in candidates], ["intraday_research_opportunity"])

    def test_small_move_creates_no_alert(self) -> None:
        market = {"stocks": {"ABC": {"price": 100}}}
        quotes = {"quotes": {"ABC": {"price": 99, "asOf": NOW.isoformat()}}}
        self.assertEqual(build_intraday_candidates(market, {"predictions": []}, quotes, NOW), [])


if __name__ == "__main__":
    unittest.main()
