"""
test_live.py - Unit tests for NBA Live Scores service, adaptive scheduler, and REST API.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from nba_stats_db.database import NBADatabase
from nba_stats_db.live_scores import NBALiveService
from nba_stats_db.live_scheduler import NBALiveScheduler
from nba_stats_db.server import app


class TestLiveScoresSystem(unittest.TestCase):
    def setUp(self):
        self.test_db_path = "test_live_temp.db"
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        self.db = NBADatabase(db_path=self.test_db_path)
        self.db.init_database()
        self.live_service = NBALiveService(db=self.db)
        self.scheduler = NBALiveScheduler(db=self.db, live_interval=15, upcoming_interval=60, idle_interval=300)

    def tearDown(self):
        self.scheduler.stop()
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def test_save_and_retrieve_scoreboard(self):
        mock_payload = {
            "scoreboard": {
                "gameDate": "2024-04-14",
                "games": [
                    {
                        "gameId": "0022301001",
                        "gameCode": "20240414/LALNOP",
                        "gameStatus": 2,
                        "gameStatusText": "Q3 08:45",
                        "period": 3,
                        "gameClock": "08:45",
                        "homeTeam": {"teamId": 1610612740, "teamName": "Pelicans", "teamTricode": "NOP", "score": 75},
                        "awayTeam": {"teamId": 1610612747, "teamName": "Lakers", "teamTricode": "LAL", "score": 82},
                        "gameLeaders": {
                            "homeLeaders": {"name": "Zion Williamson", "points": 24},
                            "awayLeaders": {"name": "LeBron James", "points": 28},
                        },
                    },
                    {
                        "gameId": "0022301002",
                        "gameCode": "20240414/GSWSAC",
                        "gameStatus": 3,
                        "gameStatusText": "Final",
                        "period": 4,
                        "gameClock": "00:00",
                        "homeTeam": {"teamId": 1610612758, "teamName": "Kings", "teamTricode": "SAC", "score": 118},
                        "awayTeam": {"teamId": 1610612744, "teamName": "Warriors", "teamTricode": "GSW", "score": 94},
                    },
                ],
            }
        }

        saved = self.live_service.save_live_scoreboard(mock_payload)
        self.assertEqual(len(saved), 2)

        # Check cached scoreboard retrieval
        cached = self.live_service.get_cached_scoreboard()
        self.assertEqual(cached["total_games"], 2)
        self.assertEqual(cached["live_games_count"], 1)

        # Status 2 should be ordered first
        first_game = cached["games"][0]
        self.assertEqual(first_game["game_id"], "0022301001")
        self.assertEqual(first_game["game_status"], 2)
        self.assertEqual(first_game["home_team"]["tricode"], "NOP")
        self.assertEqual(first_game["away_team"]["score"], 82)

        # Final game should also be archived into games table
        final_game_df = self.db.query_df("SELECT * FROM games WHERE game_id = '0022301002'")
        self.assertEqual(len(final_game_df), 1)
        self.assertEqual(final_game_df.iloc[0]["home_team_pts"], 118)

    def test_adaptive_interval_logic(self):
        # Live game present -> 15s
        live_games = [{"game_status": 2}, {"game_status": 1}]
        self.assertEqual(self.scheduler._calculate_next_interval(live_games), 15)

        # Only upcoming games -> 60s
        upcoming_games = [{"game_status": 1}, {"game_status": 1}]
        self.assertEqual(self.scheduler._calculate_next_interval(upcoming_games), 60)

        # All finished games -> 300s
        final_games = [{"game_status": 3}, {"game_status": 3}]
        self.assertEqual(self.scheduler._calculate_next_interval(final_games), 300)

        # No games -> 300s
        self.assertEqual(self.scheduler._calculate_next_interval([]), 300)

    def test_live_server_endpoints(self):
        client = app.test_client()

        # Test demo mode
        res = client.get("/api/live/scores?demo=1")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("games", data)
        self.assertGreaterEqual(data["total_games"], 1)

        # Test scheduler status endpoint
        res_sched = client.get("/api/live/scheduler")
        self.assertEqual(res_sched.status_code, 200)
        sched_data = res_sched.get_json()
        self.assertIn("is_running", sched_data)

        # Test scheduler start and stop
        res_start = client.post("/api/live/scheduler/start")
        self.assertEqual(res_start.status_code, 200)
        self.assertTrue(res_start.get_json()["scheduler"]["is_running"])

        res_stop = client.post("/api/live/scheduler/stop")
        self.assertEqual(res_stop.status_code, 200)
        self.assertFalse(res_stop.get_json()["scheduler"]["is_running"])


if __name__ == "__main__":
    unittest.main()
