from __future__ import annotations

import unittest
from datetime import datetime, timezone

from v5_core import evaluate_record, prediction_id, promotion_qualified, risk_budget, upsert_immutable_records


class V5PredictionTests(unittest.TestCase):
    def sample(self) -> dict:
        return {
            "id": prediction_id("2026-01-02", "ABC", 5, "v5"),
            "predictionDate": "2026-01-02",
            "ticker": "ABC",
            "horizonSessions": 5,
            "probability": .64,
            "uncertainty": {"low": .54, "high": .74},
            "initialPrice": 100.0,
            "modelVersion": "v5",
            "dataHash": "sha256:test",
            "status": "pending",
        }

    def test_ledger_rejects_rewriting_published_probability(self) -> None:
        original = self.sample()
        changed = {**original, "probability": .91}
        with self.assertRaises(ValueError):
            upsert_immutable_records([original], [changed])

    def test_ledger_duplicate_is_idempotent(self) -> None:
        original = self.sample()
        self.assertEqual(len(upsert_immutable_records([original], [original])), 1)

    def test_prediction_matures_only_after_exact_horizon(self) -> None:
        dates = ["2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09"]
        prices = {
            "ABC": {"dates": dates, "close": [100, 101, 102, 103, 104, 110]},
            "SPY": {"dates": dates, "close": [200, 201, 202, 203, 204, 210]},
        }
        evaluated = evaluate_record(self.sample(), prices)
        self.assertEqual(evaluated["status"], "evaluated")
        self.assertAlmostEqual(evaluated["assetReturn"], .10)
        self.assertAlmostEqual(evaluated["spyReturn"], .05)
        self.assertTrue(evaluated["correct"])

    def test_risk_budget_never_exceeds_one_and_defends_regime(self) -> None:
        defensive = risk_budget(.20, False)
        normal = risk_budget(.20, True)
        self.assertLessEqual(defensive["exposure"], .35)
        self.assertLessEqual(normal["exposure"], 1)
        self.assertLessEqual(defensive["dailyCvarProxy"], .020001)

    def test_promotion_requires_all_published_rules(self) -> None:
        champion = {"observations": 20, "sharpe": .40, "maxDrawdown": -.40, "cagr": .10}
        challenger = {"observations": 20, "sharpe": .50, "maxDrawdown": -.30, "cagr": .09}
        qualified, checks = promotion_qualified(champion, challenger)
        self.assertTrue(qualified)
        self.assertTrue(all(checks.values()))


if __name__ == "__main__":
    unittest.main()
