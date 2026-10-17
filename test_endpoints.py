"""
test_endpoints.py - Automated tests for NBA API endpoints discovery, catalog,
persistence, CLI commands, and REST APIs.
"""

import unittest
import os
import sqlite3
import pandas as pd

from nba_stats_db.endpoints_catalog import get_all_endpoints_catalog, determine_category
from nba_stats_db.database import NBADatabase
from nba_stats_db.endpoints_downloader import NBAEndpointDownloader
from nba_stats_db.server import app


class TestEndpointsSystem(unittest.TestCase):
    def setUp(self):
        self.test_db_path = "test_endpoints_temp.db"
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        self.db = NBADatabase(db_path=self.test_db_path)
        self.db.init_database()

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def test_catalog_discovery(self):
        catalog = get_all_endpoints_catalog()
        self.assertEqual(len(catalog), 138, "Catalog must contain exactly 138 endpoints")
        self.assertIn("AllTimeLeadersGrids", catalog)
        self.assertIn("CommonPlayerInfo", catalog)
        self.assertIn("LiveScoreBoard", catalog)
        self.assertIn("LiveBoxScore", catalog)
        self.assertIn("LivePlayByPlay", catalog)

        # Verify categorization
        self.assertEqual(catalog["LiveScoreBoard"]["category"], "Live Feeds")
        self.assertEqual(catalog["AllTimeLeadersGrids"]["category"], "Historical & Franchise")

    def test_database_registration_and_persistence(self):
        catalog = get_all_endpoints_catalog()
        count = self.db.register_endpoints_catalog(catalog)
        self.assertEqual(count, 138)

        entries = self.db.get_endpoints_catalog()
        self.assertEqual(len(entries), 138)

        # Test dataset persistence
        dummy_df = pd.DataFrame([
            {"PLAYER_ID": 2544, "PLAYER_NAME": "LeBron James", "PTS": 43000},
            {"PLAYER_ID": 201142, "PLAYER_NAME": "Kevin Durant", "PTS": 32000},
        ])
        tbl_name = self.db.save_endpoint_dataset("AllTimeLeadersGrids", "Leaders", dummy_df)
        self.assertEqual(tbl_name, "ep_alltimeleadersgrids_leaders")

        # Verify table exists in SQLite
        read_df = self.db.query_df(f"SELECT * FROM {tbl_name}")
        self.assertEqual(len(read_df), 2)
        self.assertEqual(read_df.iloc[0]["PLAYER_NAME"], "LeBron James")

        # Update status
        self.db.update_endpoint_status(
            endpoint_name="AllTimeLeadersGrids",
            status="SUCCESS",
            result_sets_count=1,
            total_rows=2,
            table_names=[tbl_name],
        )
        detail = self.db.get_endpoint_detail("AllTimeLeadersGrids")
        self.assertIsNotNone(detail)
        self.assertEqual(detail["status"], "SUCCESS")
        self.assertEqual(detail["total_rows"], 2)

    def test_server_endpoints_api(self):
        client = app.test_client()
        res = client.get("/api/endpoints")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("endpoints", data)
        self.assertGreaterEqual(data["total"], 138)

        res_detail = client.get("/api/endpoints/AllTimeLeadersGrids")
        self.assertEqual(res_detail.status_code, 200)
        detail = res_detail.get_json()
        self.assertEqual(detail["endpoint_name"], "AllTimeLeadersGrids")


if __name__ == "__main__":
    unittest.main()
