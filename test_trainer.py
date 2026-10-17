"""
test_trainer.py - Unit and Integration tests for Box LEBRON Machine Learning Training Engine.
"""

import os
import unittest
import json
import pandas as pd
from nba_stats_db.database import NBADatabase
from nba_stats_db.trainer import BoxLEBRONTrainer, OFFENSIVE_FEATURES, DEFENSIVE_FEATURES
from nba_stats_db.box_lebron import BoxLEBRONModel
from nba_stats_db.server import app


class TestBoxLEBRONTrainer(unittest.TestCase):
    def setUp(self):
        self.db = NBADatabase()
        self.trainer = BoxLEBRONTrainer(db=self.db)

    def test_feature_matrix_construction(self):
        X_off, X_def, y_off, y_def = self.trainer.build_training_dataset(
            min_minutes=400.0, start_season="2015-16"
        )
        self.assertFalse(X_off.empty)
        self.assertFalse(X_def.empty)
        self.assertEqual(len(X_off), len(y_off))
        self.assertEqual(len(X_def), len(y_def))

        for feat in OFFENSIVE_FEATURES:
            self.assertIn(feat, X_off.columns)
        for feat in DEFENSIVE_FEATURES:
            self.assertIn(feat, X_def.columns)

    def test_training_convergence_and_metrics(self):
        meta = self.trainer.train(estimator="ridge", cv=3, min_minutes=400.0, start_season="2018-19")
        self.assertIn("offensive_metrics", meta)
        self.assertIn("defensive_metrics", meta)
        self.assertIn("r2", meta["offensive_metrics"])
        self.assertGreater(meta["sample_size"], 500)

        # Check that weights dictionary contains all features
        for feat in OFFENSIVE_FEATURES:
            self.assertIn(feat, meta["offensive_weights"])
        for feat in DEFENSIVE_FEATURES:
            self.assertIn(feat, meta["defensive_weights"])

    def test_save_and_load_model(self):
        meta = self.trainer.train(estimator="ridge", cv=3, min_minutes=400.0, start_season="2020-21")
        test_path = os.path.join(os.path.dirname(self.trainer.weights_path), "test_weights.json")
        saved_path = self.trainer.save_model(filepath=test_path)
        self.assertTrue(os.path.exists(saved_path))

        loaded = self.trainer.load_model(filepath=test_path)
        self.assertEqual(loaded["sample_size"], meta["sample_size"])

        # Test BoxLEBRONModel loading
        model = BoxLEBRONModel(db=self.db, weights_file=test_path)
        self.assertIsNotNone(model.trained_weights)

        # Clean up test file
        if os.path.exists(test_path):
            os.remove(test_path)

    def test_training_api_endpoint(self):
        client = app.test_client()

        # 1. Test get model-weights
        res = client.get("/api/lebron/model-weights")
        self.assertEqual(res.status_code, 200)

        # 2. Test trigger training endpoint
        train_res = client.post("/api/lebron/train", json={
            "estimator": "ridge",
            "cv": 3,
            "min_minutes": 500.0,
            "recalculate": False
        })
        self.assertEqual(train_res.status_code, 200)
        data = train_res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("offensive_metrics", data)


if __name__ == "__main__":
    unittest.main()
