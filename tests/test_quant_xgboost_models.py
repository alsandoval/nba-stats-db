"""
test_quant_xgboost_models.py - Tests for XGBExpectedShotModel and XGBWinProbabilityModel.
"""

import math
import os
import tempfile
import unittest
import numpy as np

from nba_stats_db.quant.shot_model import XGBExpectedShotModel
from nba_stats_db.quant.win_probability import (
    XGBWinProbabilityModel,
    analytical_win_prob_prior,
)


class TestXGBExpectedShotModel(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        # Generate 400 synthetic shots across court
        self.n = 400
        self.dist = np.random.uniform(2.0, 28.0, self.n)
        self.x = np.random.uniform(-22.0, 22.0, self.n)
        self.y = np.random.uniform(0.0, 25.0, self.n)
        self.period = np.random.randint(1, 5, self.n)
        self.clock = np.random.uniform(0.0, 720.0, self.n)
        self.is_3pt = (self.dist >= 23.75).astype(int)
        # Closer shots have higher make probability
        true_prob = np.clip(0.68 - 0.012 * self.dist, 0.25, 0.70)
        self.made = (np.random.rand(self.n) < true_prob).astype(int)

        self.model = XGBExpectedShotModel()

    def test_fit_and_smoe_evaluation(self):
        metrics = self.model.fit(
            shot_x=self.x,
            shot_y=self.y,
            shot_dist=self.dist,
            period=self.period,
            clock_seconds=self.clock,
            is_3pt=self.is_3pt,
            made=self.made,
        )

        self.assertEqual(metrics["train_samples"], self.n)
        self.assertGreater(metrics["logloss"], 0.0)

        eval_result = self.model.evaluate_shots(
            shot_x=self.x,
            shot_y=self.y,
            shot_dist=self.dist,
            period=self.period,
            clock_seconds=self.clock,
            is_3pt=self.is_3pt,
            made=self.made,
        )

        self.assertEqual(eval_result["shots_analyzed"], self.n)
        self.assertIn("x_efg_pct", eval_result)
        self.assertIn("actual_efg_pct", eval_result)
        self.assertIn("smoe", eval_result)
        # Verify SMOE formula: SMOE = actual_efg - x_efg
        self.assertAlmostEqual(
            eval_result["smoe"],
            eval_result["actual_efg_pct"] - eval_result["x_efg_pct"],
            places=3
        )

    def test_model_persistence(self):
        self.model.fit(
            shot_x=self.x,
            shot_y=self.y,
            shot_dist=self.dist,
            period=self.period,
            clock_seconds=self.clock,
            is_3pt=self.is_3pt,
            made=self.made,
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            self.model.save(tmp_path)
            loaded_model = XGBExpectedShotModel(model_path=tmp_path)
            probs1 = self.model.predict_proba(self.x[:5], self.y[:5], self.dist[:5], self.period[:5], self.clock[:5], self.is_3pt[:5])
            probs2 = loaded_model.predict_proba(self.x[:5], self.y[:5], self.dist[:5], self.period[:5], self.clock[:5], self.is_3pt[:5])
            np.testing.assert_allclose(probs1, probs2, rtol=1e-4)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestXGBWinProbabilityModel(unittest.TestCase):
    def setUp(self):
        self.model = XGBWinProbabilityModel()

    def test_analytical_prior_boundaries(self):
        # Up by 12 with 30 seconds remaining -> probability should be >= 0.98
        p_lead = analytical_win_prob_prior(score_margin=12, seconds_remaining=30.0, possession_home=1)
        self.assertGreaterEqual(p_lead, 0.98)

        # Down by 12 with 30 seconds remaining -> probability should be <= 0.02
        p_trail = analytical_win_prob_prior(score_margin=-12, seconds_remaining=30.0, possession_home=0)
        self.assertLessEqual(p_trail, 0.02)

        # Tied at start of game (2880s) with slight home court advantage -> ~0.55 - 0.60
        p_start = analytical_win_prob_prior(score_margin=0, seconds_remaining=2880.0, possession_home=1)
        self.assertGreater(p_start, 0.50)
        self.assertLess(p_start, 0.65)

    def test_fit_and_predict(self):
        # Generate 300 game states
        n = 300
        sec_rem = np.random.uniform(10.0, 2880.0, n)
        margins = np.random.normal(0, 8, n).astype(int)
        period = np.random.randint(1, 5, n)
        poss_home = np.random.randint(0, 2, n)
        # Winners correlated with lead
        home_won = (margins + np.random.normal(0, 5, n) > 0).astype(int)

        metrics = self.model.fit(
            score_margin=margins,
            seconds_remaining=sec_rem,
            period=period,
            possession_home=poss_home,
            home_won=home_won,
        )

        self.assertEqual(metrics["train_samples"], n)
        self.assertGreater(metrics["logloss"], 0.0)

        # High lead test
        wp_high = self.model.predict_win_probability(score_margin=15, seconds_remaining=60, period=4, possession_home=1)
        wp_low = self.model.predict_win_probability(score_margin=-15, seconds_remaining=60, period=4, possession_home=0)
        self.assertGreater(wp_high, wp_low)

    def test_game_timeline_generation(self):
        mock_game_states = [
            {"period": 1, "seconds_remaining": 2880, "score_margin": 0, "home_score": 0, "away_score": 0, "home_team_id": 1, "possession_team_id": 1},
            {"period": 2, "seconds_remaining": 1440, "score_margin": 6, "home_score": 56, "away_score": 50, "home_team_id": 1, "possession_team_id": 1},
            {"period": 4, "seconds_remaining": 60, "score_margin": 10, "home_score": 110, "away_score": 100, "home_team_id": 1, "possession_team_id": 1},
            {"period": 4, "seconds_remaining": 0, "score_margin": 10, "home_score": 112, "away_score": 102, "home_team_id": 1, "possession_team_id": 1},
        ]

        timeline = self.model.compute_game_timeline(mock_game_states)
        self.assertEqual(len(timeline), 4)
        # Last state with home lead must be 1.0
        self.assertEqual(timeline[-1]["home_win_prob"], 1.0)
        self.assertEqual(timeline[-1]["away_win_prob"], 0.0)


if __name__ == "__main__":
    unittest.main()
