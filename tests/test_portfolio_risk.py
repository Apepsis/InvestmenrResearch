from __future__ import annotations

import numpy as np
import unittest

from research_core import historical_var_cvar, maximum_drawdown, performance_metrics, portfolio_returns


class PortfolioRiskTests(unittest.TestCase):
    def test_portfolio_returns_respect_weights(self) -> None:
        result = portfolio_returns({"A": [0.10, 0.00], "B": [0.00, -0.10]}, {"A": .6, "B": .4})
        self.assertTrue(np.allclose(result, [0.06, -0.04]))


    def test_var_cvar_tail_order(self) -> None:
        var, cvar = historical_var_cvar([-0.10, -0.04, -0.02, 0.01, 0.03], confidence=.8)
        self.assertLessEqual(cvar, var)
        self.assertLessEqual(var, 0)


    def test_performance_metrics_are_finite(self) -> None:
        returns = [0.08, -0.03, 0.05, 0.02, -0.01, 0.04]
        benchmark = [0.04, -0.02, 0.03, 0.01, 0.00, 0.02]
        metrics = performance_metrics(returns, benchmark, periods_per_year=4)
        self.assertEqual(metrics["observations"], len(returns))
        self.assertEqual(metrics["maxDrawdown"], maximum_drawdown(returns))
        self.assertTrue(all(np.isfinite(value) for value in metrics.values()))
