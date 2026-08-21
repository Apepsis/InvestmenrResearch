from __future__ import annotations

import unittest

import numpy as np

from neural_core import classification_metrics, fit_ensemble, predict_ensemble, promotion_gate


class NeuralV8Tests(unittest.TestCase):
    @staticmethod
    def synthetic(seed: int = 4) -> tuple[np.ndarray, np.ndarray]:
        rng = np.random.default_rng(seed)
        values = rng.normal(size=(900, 6))
        logits = np.column_stack((
            1.2 * values[:, 0] - .8 * values[:, 1],
            .9 * values[:, 2] + .5 * values[:, 0],
            1.1 * values[:, 3] - .6 * values[:, 4] + .3 * values[:, 5],
        ))
        probability = 1 / (1 + np.exp(-logits))
        target = (rng.random(probability.shape) < probability).astype(float)
        return values, target

    def test_ensemble_round_trip_is_deterministic(self) -> None:
        values, target = self.synthetic()
        artifact = fit_ensemble(
            values[:600], target[:600], values[600:750], target[600:750],
            features=[f"x{index}" for index in range(values.shape[1])],
            horizons=[5, 20, 60], seeds=[3, 7], hidden=(8, 4), epochs=35, l2=.002,
        )
        first, disagreement, _ = predict_ensemble(artifact, values[750:])
        second, _, _ = predict_ensemble(artifact, values[750:])
        np.testing.assert_allclose(first, second, atol=1e-12)
        self.assertEqual(first.shape, (150, 3))
        self.assertTrue(np.all((first >= 0) & (first <= 1)))
        self.assertTrue(np.all(disagreement >= 0))

    def test_warm_candidate_records_memory_parent(self) -> None:
        values, target = self.synthetic()
        cold = fit_ensemble(
            values[:600], target[:600], values[600:750], target[600:750],
            features=[f"x{index}" for index in range(values.shape[1])],
            horizons=[5, 20, 60], seeds=[5], hidden=(8, 4), epochs=20,
        )
        cold["version"] = "cold-parent"
        warm = fit_ensemble(
            values[:620], target[:620], values[620:770], target[620:770],
            features=[f"x{index}" for index in range(values.shape[1])],
            horizons=[5, 20, 60], seeds=[5], hidden=(8, 4), epochs=10,
            warm_artifact=cold, memory_strength=.03,
        )
        self.assertEqual(warm["memory"]["parentVersion"], "cold-parent")
        self.assertIn("Fisher", warm["memory"]["method"])

    def test_promotion_rejects_cosmetic_improvement(self) -> None:
        reference = {
            "rows": 900,
            "brierScore": .2400,
            "logLoss": .680,
            "ece": .035,
            "perHorizon": {key: {"brierScore": .2400} for key in ("5", "20", "60")},
        }
        cosmetic = {
            "rows": 900,
            "brierScore": .2398,
            "logLoss": .679,
            "ece": .034,
            "temporalBlockWinRate": .75,
            "perHorizon": {key: {"brierScore": .2398} for key in ("5", "20", "60")},
        }
        qualified, checks, required = promotion_gate(reference, cosmetic, trial_count=50)
        self.assertFalse(qualified)
        self.assertFalse(checks["trialAdjustedBrierImprovement"])
        self.assertGreaterEqual(required, .001)

    def test_metrics_cover_every_horizon(self) -> None:
        values, target = self.synthetic()
        probability = np.clip(target * .7 + .15, .01, .99)
        metrics = classification_metrics(probability, target, [5, 20, 60])
        self.assertEqual(set(metrics["perHorizon"]), {"5", "20", "60"})
        self.assertEqual(metrics["probabilities"], target.size)


if __name__ == "__main__":
    unittest.main()
