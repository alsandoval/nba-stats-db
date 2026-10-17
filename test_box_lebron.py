"""
test_box_lebron.py - Unit and Integration tests for Box LEBRON calculations,
archetype classifications, database queries, and REST endpoints.
"""

import os
import unittest
import pandas as pd
from nba_stats_db.database import NBADatabase
from nba_stats_db.box_lebron import BoxLEBRONModel, _to_decimal
from nba_stats_db.queries import NBAQueryHelper
from nba_stats_db.server import app


class TestBoxLEBRONModel(unittest.TestCase):
    def setUp(self):
        self.db = NBADatabase()
        self.model = BoxLEBRONModel(db=self.db)
        self.helper = NBAQueryHelper(db=self.db)

    def test_decimal_normalization(self):
        self.assertEqual(_to_decimal(15.0), 0.15)
        self.assertEqual(_to_decimal(0.15), 0.15)
        self.assertEqual(_to_decimal(None, default=0.10), 0.10)
        self.assertEqual(_to_decimal("8.5"), 0.085)

    def test_archetype_classification(self):
        # Primary Ball Handler
        pg_row = pd.Series({
            "usg_pct": 0.32,
            "ast_pct": 0.35,
            "fg3a": 8.0,
            "fga": 20.0,
            "oreb_pct": 0.02,
            "reb_pct": 0.06,
            "fg_pct": 0.48,
        })
        self.assertEqual(self.model.classify_offensive_archetype(pg_row), "Primary Ball Handler")

        # Roll & Cut Big
        center_row = pd.Series({
            "usg_pct": 0.15,
            "ast_pct": 0.05,
            "fg3a": 0.1,
            "fga": 8.0,
            "oreb_pct": 0.12,
            "reb_pct": 0.18,
            "fg_pct": 0.68,
        })
        self.assertEqual(self.model.classify_offensive_archetype(center_row), "Roll & Cut Big")

        # Movement Shooter
        shooter_row = pd.Series({
            "usg_pct": 0.18,
            "ast_pct": 0.08,
            "fg3a": 8.5,
            "fga": 11.0,
            "oreb_pct": 0.01,
            "reb_pct": 0.04,
            "fg_pct": 0.44,
        })
        self.assertEqual(self.model.classify_offensive_archetype(shooter_row), "Movement Shooter")

        # Rim Protector
        rim_def_row = pd.Series({
            "dreb_pct": 0.24,
            "blk": 2.5,
            "stl": 0.6,
            "min": 32.0,
            "gp": 70,
            "ast_pct": 0.05,
        })
        self.assertEqual(self.model.classify_defensive_archetype(rim_def_row), "Rim Protector")

    def test_formula_sanity_and_bounds(self):
        superstar_row = pd.Series({
            "usg_pct": 0.33,
            "ts_pct": 0.65,
            "ast_pct": 0.35,
            "tm_tov_pct": 9.5,
            "oreb_pct": 0.06,
            "dreb_pct": 0.22,
            "fg3a": 6.0,
            "fg3_pct": 0.40,
            "stl": 1.5,
            "blk": 1.0,
            "pf": 2.2,
            "min": 35.0,
            "gp": 75,
        })
        o_leb = self.model.compute_o_lebron(superstar_row, lg_ts_pct=0.57)
        d_leb = self.model.compute_d_lebron(superstar_row)
        tot_leb = o_leb + d_leb

        self.assertGreater(o_leb, 0.4)
        self.assertGreater(d_leb, -0.5)
        self.assertGreater(tot_leb, 0.5)

    def test_database_leaderboard_query(self):
        df = self.helper.get_box_lebron_leaderboard(season="2023-24", min_minutes=500.0, limit=10)
        self.assertFalse(df.empty)
        self.assertIn("Player", df.columns)
        self.assertIn("Box LEBRON", df.columns)
        self.assertIn("WAR / Wins Added", df.columns)

    def test_player_history_query(self):
        # Test LeBron James player history (player_id: 2544)
        df = self.helper.get_player_box_lebron_history(player_id=2544)
        self.assertFalse(df.empty)
        self.assertGreaterEqual(len(df), 20)  # At least 20 seasons for LeBron

    def test_archetype_distribution_query(self):
        df = self.helper.get_box_lebron_archetype_distribution(season="2023-24")
        self.assertFalse(df.empty)
        self.assertIn("Offensive Archetype", df.columns)
        self.assertIn("Player Count", df.columns)

    def test_rest_api_endpoints(self):
        client = app.test_client()

        # 1. Leaderboard endpoint
        res = client.get("/api/lebron/leaderboard?season=2023-24&limit=5")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("leaders", data)
        self.assertEqual(len(data["leaders"]), 5)

        # 2. Player history endpoint (LeBron James: 2544)
        res_player = client.get("/api/lebron/player/2544")
        self.assertEqual(res_player.status_code, 200)
        player_data = res_player.get_json()
        self.assertIn("history", player_data)
        self.assertGreater(len(player_data["history"]), 10)

        # 3. Archetypes endpoint
        res_arch = client.get("/api/lebron/archetypes?season=2023-24")
        self.assertEqual(res_arch.status_code, 200)
        arch_data = res_arch.get_json()
        self.assertIn("archetypes", arch_data)


if __name__ == "__main__":
    unittest.main()
