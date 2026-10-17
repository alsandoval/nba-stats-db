"""
test_api_endpoints.py - Automated Integration Test Suite for all FastAPI Endpoints.
"""

import io
import unittest
from fastapi.testclient import TestClient
import pyarrow.ipc as ipc

from nba_stats_db.api.main import app


class TestFastAPIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_check(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["version"], "2.3.0-PROD")
        self.assertIn("active_models", data)
        self.assertEqual(len(data["active_models"]), 4)

    def test_wowy_team_roster_and_evaluation(self):
        team_id = 1610612738  # BOS
        roster_resp = self.client.get(f"/api/wowy/team/{team_id}/roster?season=2023-24")
        self.assertEqual(roster_resp.status_code, 200)
        roster_data = roster_resp.json()
        self.assertIn("roster", roster_data)

        # Warm-up / initial evaluation
        eval_resp = self.client.post(
            "/api/wowy/evaluate",
            json={
                "team_id": team_id,
                "season": "2023-24",
                "on_player_ids": [],
                "off_player_ids": [],
            },
        )
        self.assertEqual(eval_resp.status_code, 200)
        eval_data = eval_resp.json()
        self.assertIn("offensive_rating", eval_data)
        self.assertIn("query_time_ms", eval_data)

        # Subsequent query to verify sub-15ms performance
        eval_resp2 = self.client.post(
            "/api/wowy/evaluate",
            json={
                "team_id": team_id,
                "season": "2023-24",
                "on_player_ids": [],
                "off_player_ids": [],
            },
        )
        self.assertLess(eval_resp2.json()["query_time_ms"], 15.0)

    def test_rapm_leaderboard(self):
        resp = self.client.get("/api/rapm/leaderboard?season=2023-24&limit=10")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("players", data)
        self.assertGreater(len(data["players"]), 0)
        top_player = data["players"][0]
        self.assertIn("orapm", top_player)
        self.assertIn("drapm", top_player)
        self.assertIn("rapm", top_player)
        self.assertIn("rapm_percentile", top_player)

    def test_shots_evaluation_and_chart(self):
        eval_resp = self.client.post(
            "/api/shots/evaluate",
            json={
                "shot_x": 0.0,
                "shot_y": 24.0,
                "shot_dist": 24.0,
                "period": 1,
                "clock_seconds": 360.0,
                "is_3pt": 1,
            },
        )
        self.assertEqual(eval_resp.status_code, 200)
        eval_data = eval_resp.json()
        self.assertIn("make_probability", eval_data)
        self.assertIn("x_efg_pct", eval_data)

        # Player shot chart
        chart_resp = self.client.get("/api/shots/chart/2544?season=2023-24")  # LeBron
        self.assertEqual(chart_resp.status_code, 200)
        chart_data = chart_resp.json()
        self.assertIn("summary", chart_data)
        self.assertIn("smoe", chart_data["summary"])
        self.assertIn("shots", chart_data)

    def test_win_probability_and_timeline(self):
        # Specific game state
        wp_resp = self.client.post(
            "/api/games/win-probability",
            json={
                "score_margin": 6,
                "seconds_remaining": 120.0,
                "period": 4,
                "possession_home": 1,
            },
        )
        self.assertEqual(wp_resp.status_code, 200)
        wp_data = wp_resp.json()
        self.assertGreater(wp_data["home_win_prob"], 0.70)

        # Game timeline
        timeline_resp = self.client.get("/api/games/0022300061/win-probability-timeline")
        self.assertEqual(timeline_resp.status_code, 200)
        t_data = timeline_resp.json()
        self.assertIn("timeline", t_data)
        self.assertGreater(len(t_data["timeline"]), 0)

    def test_players_list_and_profile(self):
        # List
        list_resp = self.client.get("/api/players?limit=10")
        self.assertEqual(list_resp.status_code, 200)
        l_data = list_resp.json()
        self.assertIn("items", l_data)
        self.assertEqual(len(l_data["items"]), 10)

        # Single profile (LeBron James: 2544)
        profile_resp = self.client.get("/api/players/2544")
        self.assertEqual(profile_resp.status_code, 200)
        p_data = profile_resp.json()
        self.assertEqual(p_data["player_id"], 2544)
        self.assertIn("percentiles", p_data)
        self.assertIn("traditional_stats", p_data)

    def test_teams_list_and_cba_apron(self):
        teams_resp = self.client.get("/api/teams?season=2023-24")
        self.assertEqual(teams_resp.status_code, 200)
        t_data = teams_resp.json()
        self.assertEqual(t_data["total"], 30)

        # CBA Apron
        cba_resp = self.client.get("/api/cba/teams/1610612738/apron?season=2023-24")
        self.assertEqual(cba_resp.status_code, 200)
        cba_data = cba_resp.json()
        self.assertIn("second_apron", cba_data)
        self.assertIn("estimated_luxury_tax", cba_data)

    def test_arrow_streaming_ipc(self):
        resp = self.client.get("/api/arrow/possessions?season=2023-24&limit=50")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"], "application/vnd.apache.arrow.stream")
        # Parse binary Arrow stream with PyArrow
        reader = ipc.open_stream(io.BytesIO(resp.content))
        table = reader.read_all()
        self.assertGreater(len(table), 0)
        self.assertIn("off_mask", table.column_names)

    def test_live_scoreboard_and_feed(self):
        # Scoreboard
        sb_resp = self.client.get("/api/games/live/scoreboard")
        self.assertEqual(sb_resp.status_code, 200)
        sb_data = sb_resp.json()
        self.assertIn("games", sb_data)
        self.assertGreaterEqual(len(sb_data["games"]), 1)

        # Game live feed
        feed_resp = self.client.get("/api/games/0022300001/live-feed")
        self.assertEqual(feed_resp.status_code, 200)
        feed_data = feed_resp.json()
        self.assertIn("candlesticks", feed_data)
        self.assertEqual(len(feed_data["candlesticks"]), 48)
        self.assertIn("playByPlay", feed_data)
        self.assertIn("homeTeam", feed_data)
        self.assertIn("awayTeam", feed_data)


if __name__ == "__main__":
    unittest.main()

