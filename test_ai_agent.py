"""
test_ai_agent.py - Unit and integration tests for NBA AI Chart Agent and REST endpoints.
"""

import unittest
import json
from nba_stats_db.ai_agent import NBAAIAgent, PRESET_QUERIES
from nba_stats_db.database import NBADatabase
from nba_stats_db.server import app


class TestNBAAIAgent(unittest.TestCase):

    def setUp(self):
        self.db = NBADatabase()
        self.agent = NBAAIAgent(db=self.db)
        self.client = app.test_client()

    def test_sql_validation_safe(self):
        """Valid SELECT queries must pass validation."""
        valid_queries = [
            "SELECT * FROM players LIMIT 10;",
            "SELECT player_id, pts, season FROM player_season_stats WHERE season = '2023-24';",
            "WITH ranked AS (SELECT * FROM player_season_stats) SELECT * FROM ranked LIMIT 5;"
        ]
        for q in valid_queries:
            is_safe, sanitized = self.agent.validate_sql(q)
            self.assertTrue(is_safe, f"Expected query to be safe: {q}")

    def test_sql_validation_blocks_dangerous(self):
        """Mutating or dangerous SQL keywords and multi-statements must be blocked."""
        dangerous = [
            "DROP TABLE players;",
            "DELETE FROM player_season_stats WHERE pts < 10;",
            "UPDATE player_season_stats SET pts = 100;",
            "INSERT INTO players (player_id) VALUES (99999);",
            "SELECT * FROM players; DROP TABLE teams;",
            "PRAGMA table_info(players);",
            "ALTER TABLE players ADD COLUMN test TEXT;"
        ]
        for q in dangerous:
            is_safe, err = self.agent.validate_sql(q)
            self.assertFalse(is_safe, f"Expected query to be blocked: {q}, but got: {err}")

    def test_presets_execute_cleanly(self):
        """All built-in demo presets must execute against the database without errors."""
        presets = self.agent.get_presets()
        self.assertGreaterEqual(len(presets), 3)

        for p in presets:
            spec = p["chartSpec"]
            self.assertIn("chartType", spec)
            self.assertIn("sqlQuery", spec)
            self.assertIn(spec["chartType"], ["bar", "horizontalBar", "line", "scatter", "radar"])

            rows, err = self.agent.execute_query(spec["sqlQuery"])
            self.assertIsNone(err, f"Preset '{p['id']}' failed with SQL error: {err}")
            self.assertIsNotNone(rows, f"Preset '{p['id']}' returned None rows")

    def test_demo_mode_processing(self):
        """Without an API key, process_query should return demo mode results safely."""
        res = self.agent.process_query(
            prompt="Compare the top 10 PGs this season by Points Per Game and True Shooting %",
            api_key=None
        )
        self.assertTrue(res["success"])
        self.assertTrue(res.get("isDemo", False))
        self.assertIn("chartSpec", res)
        self.assertGreater(len(res["data"]), 0)
        self.assertIn("narrative", res)

    def test_semantic_queries_dynamic_generation(self):
        """Verify that various natural language prompts dynamically construct charts without an API key."""
        prompts = [
            "Let's compare the top 10 PG's this season",
            "Top 5 Centers by rebounds",
            "Show 3PT leaders in 2023-24",
            "Compare Nikola Jokic and Joel Embiid",
            "Pace vs Net Rating for teams",
            "Top 10 scorers"
        ]
        for p in prompts:
            res = self.agent.process_query(prompt=p, api_key=None)
            self.assertTrue(res["success"], f"Query failed for prompt '{p}': {res.get('error')}")
            self.assertIn("chartSpec", res)
            self.assertGreater(len(res["data"]), 0, f"No data rows returned for prompt '{p}'")
            self.assertIn("sqlQuery", res["chartSpec"])
            self.assertIn("chartType", res["chartSpec"])

    def test_api_presets_endpoint(self):
        """GET /api/chart-agent/presets returns valid JSON list."""
        resp = self.client.get("/api/chart-agent/presets")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_api_chart_agent_post(self):
        """POST /api/chart-agent processes query."""
        resp = self.client.post(
            "/api/chart-agent",
            data=json.dumps({"prompt": "top-pgs"}),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertIn("chartSpec", data)

    def test_api_validate_key_endpoint_empty(self):
        """POST /api/chart-agent/validate-key returns False for empty key."""
        resp = self.client.post(
            "/api/chart-agent/validate-key",
            data=json.dumps({"api_key": ""}),
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data["valid"])


if __name__ == "__main__":
    unittest.main()
