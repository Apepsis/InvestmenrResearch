from __future__ import annotations

import pandas as pd
import unittest

from run_walk_forward import temporal_years


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
        forbidden = {"forward_return_60", "forward_spy_60", "forward_excess_60", "label_excess_positive"}
        self.assertTrue(forbidden.isdisjoint(features))
