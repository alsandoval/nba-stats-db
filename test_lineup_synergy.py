"""
test_lineup_synergy.py - Test suite for Team Composition and Lineup Synergy Model.
"""

import unittest
import pandas as pd
from nba_stats_db.database import NBADatabase
from nba_stats_db.lineup_synergy import LineupSynergyModel, ARCHETYPES
from nba_stats_db.queries import NBAQueryHelper


class TestLineupSynergy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = NBADatabase()
        cls.model = LineupSynergyModel(db=cls.db)
        cls.helper = NBAQueryHelper(db=cls.db)

    def test_evaluate_balanced_lineup(self):
        """Tests that a balanced lineup with 1 Hub, 2 Spacers, and Bigs gets positive synergy and valid ratings."""
        lineup = ["Nikola Jokic", "Jamal Murray", "Michael Porter Jr.", "Aaron Gordon", "Christian Braun"]
        res = self.model.evaluate_lineup(lineup, season="2024-25")

        self.assertNotIn("error", res)
        self.assertEqual(len(res["players"]), 5)
        self.assertIn(res["balance_grade"], ["A+", "A", "B", "C"])
        self.assertGreater(res["predicted_net_rating"], 0.0)
        self.assertGreater(res["num_shooters"], 0)

    def test_usage_collision_diminishing_returns(self):
        """Tests that multiple high-usage engines sharing the floor incur a heavy usage cannibalization penalty."""
        # 5 Heliocentric creators together (Luka, Jokic, Giannis, SGA, Trae)
        clashing_lineup = ["Luka Doncic", "Nikola Jokic", "Giannis Antetokounmpo", "Shai Gilgeous-Alexander", "Trae Young"]
        res = self.model.evaluate_lineup(clashing_lineup, season="2024-25")

        self.assertNotIn("error", res)
        self.assertGreater(res["usage_penalty"], 1.5)
        self.assertGreater(res["total_usage_pct"], 130.0)
        # Should have lower balance score due to extreme skill overlap
        self.assertLess(res["balance_score"], 80.0)

    def test_zero_rim_protection_penalty(self):
        """Tests that a lineup with 0 frontcourt anchors suffers a defensive penalty."""
        # 5 pure perimeter players
        small_ball = ["Stephen Curry", "Damian Lillard", "Tyler Herro", "CJ McCollum", "Jordan Poole"]
        res = self.model.evaluate_lineup(small_ball, season="2024-25")

        self.assertNotIn("error", res)
        # Defensive synergy should reflect vulnerability
        self.assertLess(res["defensive_synergy"], 0.5)

    def test_optimize_team_lineup(self):
        """Tests combinatorial optimization across a team roster."""
        lineups = self.model.optimize_team_lineup(team="BOS", season="2024-25", top_k=3, min_minutes=100.0)
        self.assertIsInstance(lineups, list)
        if lineups:
            self.assertLessEqual(len(lineups), 3)
            # Ensure rankings are sorted descending
            self.assertGreaterEqual(lineups[0]["predicted_net_rating"], lineups[-1]["predicted_net_rating"])

    def test_trade_fit_evaluation(self):
        """Tests Maymin trade theorem calculation comparing before and after lineups."""
        current_lineup = ["Nikola Jokic", "Jamal Murray", "Michael Porter Jr.", "Aaron Gordon", "Christian Braun"]
        trade_res = self.model.evaluate_trade_fit(
            target_player="Alex Caruso",
            current_lineup=current_lineup,
            replaced_player="Christian Braun",
            season="2024-25"
        )
        self.assertNotIn("error", trade_res)
        self.assertIn("delta_predicted_net_rating", trade_res)
        self.assertIn("delta_total_synergy", trade_res)
        self.assertIn("synergy_verdict", trade_res)

    def test_archetype_synergy_matrix(self):
        """Tests the 8x8 pairwise archetype synergy matrix structure."""
        matrix_res = self.model.compute_archetype_synergy_matrix(season="2024-25")
        self.assertEqual(len(matrix_res["archetypes"]), 8)
        self.assertEqual(len(matrix_res["matrix"]), 8)
        for row in matrix_res["matrix"]:
            self.assertEqual(len(row["synergies"]), 8)

    def test_database_persistence_and_query(self):
        """Tests saving an evaluated lineup to SQLite and retrieving it through query helper."""
        lineup = ["Anthony Davis", "LeBron James", "Austin Reaves", "D'Angelo Russell", "Rui Hachimura"]
        eval_res = self.model.evaluate_lineup(lineup, season="2024-25")
        self.assertNotIn("error", eval_res)

        saved = self.model.save_lineup_evaluation(eval_res)
        self.assertTrue(saved)

        df = self.helper.get_lineup_evaluations(season="2024-25", limit=10)
        self.assertFalse(df.empty)
        self.assertIn("Lineup", df.columns)
        self.assertIn("Pred NetRtg", df.columns)


if __name__ == "__main__":
    unittest.main()
