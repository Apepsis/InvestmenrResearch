from __future__ import annotations

import unittest
from datetime import datetime, timezone

from send_alerts import build_candidates, pending_after_cooldown


class AlertTests(unittest.TestCase):
    def test_opportunity_requires_two_horizons_and_uncertainty_floor(self) -> None:
        predictions = {
            "predictions": [
                {"ticker": "ABC", "horizonSessions": 20, "probability": .70, "uncertainty": {"low": .55}},
                {"ticker": "ABC", "horizonSessions": 60, "probability": .65, "uncertainty": {"low": .51}},
            ]
        }
        candidates = build_candidates(predictions, {"issues": []}, {"champion": {"key": "statistical"}})
        self.assertEqual(candidates[0]["code"], "research_opportunity")

    def test_cooldown_suppresses_duplicate_email(self) -> None:
        now = datetime(2026, 8, 20, tzinfo=timezone.utc)
        candidate = {"fingerprint": "same", "cooldownHours": 72}
        history = [{"fingerprint": "same", "sentAt": "2026-08-19T00:00:00+00:00"}]
        self.assertEqual(pending_after_cooldown([candidate], history, now), [])


if __name__ == "__main__":
    unittest.main()
