from __future__ import annotations

import numpy as np
import unittest

from research_core import fit_logistic, score_explanation


class ScoreTests(unittest.TestCase):
    def test_score_explanation_reconciles(self) -> None:
        scores = {"technical": 70, "fundamental": 60, "news": 55, "macro": 45, "risk": 65}
        weights = {"technical": .25, "fundamental": .30, "news": .15, "macro": .15, "risk": .15}
        explanation = score_explanation(scores, weights, {key: "test" for key in scores}, "2026-01-01", .8)
        reconstructed = explanation["base"] + sum(item["contribution"] for item in explanation["contributions"])
        expected = sum(scores[key] * weights[key] for key in weights)
        self.assertLess(abs(reconstructed - explanation["result"]), .01)
        self.assertLess(abs(explanation["result"] - expected), .01)
        self.assertLessEqual(explanation["interval"]["low"], explanation["result"])
        self.assertGreaterEqual(explanation["interval"]["high"], explanation["result"])


    def test_logistic_model_learns_simple_signal(self) -> None:
        rng = np.random.default_rng(7)
        values = rng.normal(size=(500, 3))
        target = (values[:, 0] - .4 * values[:, 1] > 0).astype(float)
        model = fit_logistic(values[:400], target[:400])
        predicted = model.predict_proba(values[400:]) >= .5
        self.assertGreater(np.mean(predicted == target[400:]), .85)
        self.assertTrue(np.isfinite(model.coefficients).all())
