from __future__ import annotations

import pandas as pd
import unittest
import copy

from run_walk_forward import append_measurement, measurement_fingerprint, temporal_years


class NoLookaheadTests(unittest.TestCase):
    def test_every_training_date_precedes_test_date(self) -> None:
        dates = pd.date_range("2017-01-02", "2024-12-31", freq="B")
        frame = pd.DataFrame({"date": dates.repeat(3), "ticker": ["A", "B", "C"] * len(dates)})
        splits = list(temporal_years(frame))
        self.assertTrue(splits)
        for _, train, test in splits:
            self.assertLess(train["date"].max(), test["date"].min())


    def test_target_is_not_part_of_published_feature_list(self) -> None:
        features = [
            "ret_5", "ret_20", "ret_60", "sma_50_ratio", "sma_200_ratio", "rsi_14",
            "vol_20", "vol_60", "drawdown_252", "volume_z_20", "spy_ret_20", "spy_ret_60", "beta_60",
        ]
        forbidden = {
            "forward_return_5", "forward_spy_5", "forward_excess_5", "label_excess_positive_5",
            "forward_return_20", "forward_spy_20", "forward_excess_20", "label_excess_positive_20",
            "forward_return_60", "forward_spy_60", "forward_excess_60", "label_excess_positive_60",
            "label_excess_positive",
        }
        self.assertTrue(forbidden.isdisjoint(features))

    def test_backtest_history_deduplicates_only_identical_measurements(self) -> None:
        payload = {
            "generatedAt": "2026-08-21T10:00:00Z",
            "period": {"start": "2020-01-01", "end": "2026-01-01"},
            "horizonSessions": 60,
            "rebalanceSessions": 60,
            "transactionCostBps": 10,
            "metrics": {"spy": {"cagr": .10}, "statistical": {"cagr": .12}},
            "equity": [{"date": "2026-01-01", "spy": 1.1, "statistical": 1.2}],
            "calibration": {"brierScore": .24},
            "universe": ["AAPL", "SPY"],
        }
        same_result_later = copy.deepcopy(payload)
        same_result_later["generatedAt"] = "2026-08-22T10:00:00Z"
        changed_result = copy.deepcopy(payload)
        changed_result["metrics"]["statistical"]["cagr"] = .13
        history = {"snapshots": []}

        first = append_measurement(history, payload)
        second = append_measurement(history, same_result_later)
        third = append_measurement(history, changed_result)

        self.assertEqual(first, second)
        self.assertNotEqual(first, third)
        self.assertEqual(len(history["snapshots"]), 2)
        self.assertEqual(first, measurement_fingerprint(payload))
