"""
test_nba_db.py - Automated test suite for NBA Stats Database.
"""

import os
import unittest
from nba_stats_db.database import NBADatabase
from nba_stats_db.ingestion import NBADataIngestor
from nba_stats_db.queries import NBAQueryHelper

TEST_DB_FILE = "test_nba_stats.db"


class TestNBAStatsDB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except OSError:
                pass
        cls.db = NBADatabase(db_path=TEST_DB_FILE)
        cls.db.init_database()
        cls.ingestor = NBADataIngestor(db=cls.db)
        cls.helper = NBAQueryHelper(db=cls.db)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except OSError:
                pass

    def test_01_init_tables(self):
        """Verify all tables exist."""
        counts = self.db.get_table_counts()
        expected_tables = [
            "teams",
            "players",
            "player_profiles",
            "games",
            "player_game_logs",
            "team_game_logs",
            "player_season_stats",
            "team_season_stats",
            "player_advanced_stats",
            "team_advanced_stats",
        ]
        for tbl in expected_tables:
            self.assertIn(tbl, counts)

    def test_02_ingest_teams(self):
        """Verify static teams ingestion."""
        count = self.ingestor.ingest_teams()
        self.assertEqual(count, 30)
        c = self.db.get_table_counts()
        self.assertEqual(c["teams"], 30)

    def test_03_ingest_players(self):
        """Verify static players ingestion."""
        count = self.ingestor.ingest_players()
        self.assertGreater(count, 4500)
        c = self.db.get_table_counts()
        self.assertGreater(c["players"], 4500)

    def test_04_ingest_standings(self):
        """Verify season standings ingestion from NBA API."""
        count = self.ingestor.ingest_standings(season="2023-24")
        self.assertEqual(count, 30)
        c = self.db.get_table_counts()
        self.assertEqual(c["team_season_stats"], 30)

    def test_05_ingest_player_stats(self):
        """Verify player season stats ingestion."""
        count = self.ingestor.ingest_player_season_stats(season="2023-24")
        self.assertGreater(count, 400)

    def test_06_queries(self):
        """Verify query helper methods."""
        top_scorers = self.helper.get_top_scorers(season="2023-24", limit=5)
        self.assertFalse(top_scorers.empty)
        self.assertEqual(len(top_scorers), 5)

        standings = self.helper.get_standings(season="2023-24", conference="East")
        self.assertEqual(len(standings), 15)

        search = self.helper.search_players("Curry")
        self.assertFalse(search.empty)

    def test_07_comparisons(self):
        """Verify player and team comparison functions."""
        p_comp = self.helper.compare_players("Luka Doncic", "Stephen Curry", season="2023-24")
        self.assertIn("player1", p_comp)
        self.assertIn("player2", p_comp)
        self.assertIn("h2h", p_comp)

        t_comp = self.helper.compare_teams("BOS", "DAL", season="2023-24")
        self.assertIn("team1", t_comp)
        self.assertIn("team2", t_comp)
        self.assertIn("h2h", t_comp)


if __name__ == "__main__":
    unittest.main()
