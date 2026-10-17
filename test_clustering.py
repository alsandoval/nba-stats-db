"""
test_clustering.py - Unit and Integration tests for Unsupervised Position Clustering & 3D t-SNE Pipeline.
"""

import os
import unittest
import pandas as pd
from nba_stats_db.database import NBADatabase
from nba_stats_db.clustering import PositionClusteringModel, CLUSTERING_FEATURES
from nba_stats_db.queries import NBAQueryHelper
from nba_stats_db.server import app


class TestPositionClustering(unittest.TestCase):
    def setUp(self):
        self.db = NBADatabase()
        self.model = PositionClusteringModel(db=self.db)
        self.helper = NBAQueryHelper(db=self.db)

    def test_feature_extraction(self):
        df = self.model.fetch_player_data(season="2023-24", min_minutes=300.0)
        self.assertFalse(df.empty)
        self.assertGreater(len(df), 200)

        for col in CLUSTERING_FEATURES:
            self.assertIn(col, df.columns)
            # Ensure no NaNs in clustering features
            self.assertEqual(df[col].isna().sum(), 0, f"NaN values found in column {col}")

    def test_optimal_k_finding(self):
        opt = self.model.find_optimal_k(k_range=(4, 7), season="2023-24", min_minutes=400.0)
        self.assertIn("optimal_k", opt)
        self.assertIn("silhouette_scores", opt)
        self.assertIn("inertias", opt)
        self.assertEqual(len(opt["silhouette_scores"]), 4)  # k=4, 5, 6, 7
        self.assertGreaterEqual(opt["optimal_k"], 4)
        self.assertLessEqual(opt["optimal_k"], 7)

    def test_kmeans_and_3d_tsne(self):
        df = self.model.fit_clusters(k=6, season="2023-24", min_minutes=300.0)
        self.assertIn("cluster_id", df.columns)
        self.assertIn("cluster_name", df.columns)
        self.assertEqual(len(df["cluster_id"].unique()), 6)

        df_3d = self.model.compute_3d_tsne()
        self.assertIn("tsne_x", df_3d.columns)
        self.assertIn("tsne_y", df_3d.columns)
        self.assertIn("tsne_z", df_3d.columns)
        self.assertEqual(len(df_3d), len(df))

    def test_cluster_profiles_and_naming(self):
        self.model.fit_clusters(k=6, season="2023-24", min_minutes=300.0)
        profiles = self.model.profile_clusters()
        self.assertEqual(len(profiles), 6)

        for cid, p in profiles.items():
            self.assertIn("name", p)
            self.assertIn("description", p)
            self.assertIn("flagship_players", p)
            self.assertIn("key_attributes", p)
            self.assertIn("centroid_stats", p)
            self.assertGreater(len(p["flagship_players"]), 0)

    def test_3d_plot_html_generation(self):
        self.model.fit_clusters(k=5, season="2023-24", min_minutes=300.0)
        self.model.compute_3d_tsne()
        test_html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_3d_plot.html")

        html_out = self.model.generate_3d_plot_html(output_file=test_html_path)
        self.assertIn("Plotly.newPlot", html_out)
        self.assertTrue(os.path.exists(test_html_path))

        # Clean up
        if os.path.exists(test_html_path):
            os.remove(test_html_path)

    def test_database_saving_and_queries(self):
        self.model.fit_clusters(k=6, season="2023-24", min_minutes=300.0)
        self.model.compute_3d_tsne()
        saved = self.model.save_to_db()
        self.assertGreater(saved, 200)

        # Test query helper
        clusters_df = self.helper.get_position_clusters(season="2023-24", limit=10)
        self.assertFalse(clusters_df.empty)
        self.assertIn("Position Archetype", clusters_df.columns)
        self.assertIn("t-SNE X", clusters_df.columns)

        summaries_df = self.helper.get_cluster_summaries(season="2023-24")
        self.assertFalse(summaries_df.empty)
        self.assertIn("Archetype Name", summaries_df.columns)
        self.assertIn("Player Count", summaries_df.columns)

    def test_rest_api_clustering_endpoints(self):
        client = app.test_client()

        # 1. Optimal-k endpoint
        res_opt = client.get("/api/clustering/optimal-k?season=2023-24&min_k=4&max_k=6")
        self.assertEqual(res_opt.status_code, 200)
        data_opt = res_opt.get_json()
        self.assertIn("optimal_k", data_opt)

        # 2. 3D players endpoint
        res_3d = client.get("/api/clustering/3d?season=2023-24&limit=10")
        self.assertEqual(res_3d.status_code, 200)
        data_3d = res_3d.get_json()
        self.assertIn("players", data_3d)

        # 3. Clusters summaries endpoint
        res_c = client.get("/api/clustering/clusters?season=2023-24")
        self.assertEqual(res_c.status_code, 200)
        data_c = res_c.get_json()
        self.assertIn("clusters", data_c)


if __name__ == "__main__":
    unittest.main()
