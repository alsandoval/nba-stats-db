"""
trainer.py - Machine Learning Training Pipeline for Box LEBRON and Custom NBA Metrics.

Fits regularized regression models (Ridge / ElasticNet with Cross-Validation) on
historical player feature matrices against on/off lineup impact targets,
extracts learned feature weights, and persists model artifacts.
"""

import json
import logging
import os
import datetime
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV, ElasticNetCV
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

from .database import NBADatabase
from .box_lebron import _to_decimal

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
DEFAULT_WEIGHTS_FILE = os.path.join(DEFAULT_WEIGHTS_DIR, "box_lebron_weights.json")

OFFENSIVE_FEATURES = [
    "usg_pct",
    "ts_pct_diff",
    "usg_ts_interaction",
    "ast_pct",
    "tm_tov_pct",
    "ast_tov_diff",
    "oreb_pct",
    "fg3a_rate",
    "fg3_pct_diff",
]

DEFENSIVE_FEATURES = [
    "dreb_pct",
    "stl_per_36",
    "blk_per_36",
    "pf_per_36",
    "rim_defense_diff",
    "deflections_per_100",
]


class BoxLEBRONTrainer:
    """
    Manages dataset construction, feature extraction, cross-validated model training,
    weights extraction, and persistence for Box LEBRON and custom predictive models.
    """

    def __init__(self, db: Optional[NBADatabase] = None, weights_path: Optional[str] = None):
        self.db = db or NBADatabase()
        self.weights_path = weights_path or DEFAULT_WEIGHTS_FILE
        self.off_model: Optional[Any] = None
        self.def_model: Optional[Any] = None
        self.off_scaler: Optional[StandardScaler] = None
        self.def_scaler: Optional[StandardScaler] = None
        self.training_metadata: Dict[str, Any] = {}

    def extract_features_df(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """Transforms raw player season + advanced rows into normalized feature vectors."""
        df = raw_df.copy()

        # Minutes and games
        df["gp"] = df["gp"].fillna(1).apply(lambda v: max(float(v), 1.0))
        df["min_pg"] = df["min"].fillna(0.0).apply(lambda v: max(float(v), 1.0))
        df["total_minutes"] = np.round(df["min_pg"] * df["gp"], 1)

        # Percentages
        df["usg_pct"] = df["usg_pct"].apply(lambda v: _to_decimal(v, 0.18))
        df["ts_pct"] = df["ts_pct"].apply(lambda v: _to_decimal(v, 0.55))
        df["ast_pct"] = df["ast_pct"].apply(lambda v: _to_decimal(v, 0.12))
        df["tm_tov_pct"] = df["tm_tov_pct"].apply(lambda v: _to_decimal(v, 0.10))
        df["oreb_pct"] = df["oreb_pct"].apply(lambda v: _to_decimal(v, 0.04))
        df["dreb_pct"] = df["dreb_pct"].apply(lambda v: _to_decimal(v, 0.14))
        df["reb_pct"] = df["reb_pct"].apply(lambda v: _to_decimal(v, 0.09))
        df["fg3_pct"] = df["fg3_pct"].apply(lambda v: _to_decimal(v, 0.35))

        # Per 36 counting stats
        df["pts_per_36"] = (df["pts"].fillna(0.0) / df["min_pg"]) * 36.0
        df["stl_per_36"] = (df["stl"].fillna(0.0) / df["min_pg"]) * 36.0
        df["blk_per_36"] = (df["blk"].fillna(0.0) / df["min_pg"]) * 36.0
        df["pf_per_36"] = (df["pf"].fillna(0.0) / df["min_pg"]) * 36.0

        # Shot selection & 3PT rate
        fga = df["fga"].fillna(1.0).apply(lambda v: max(float(v), 0.1))
        df["fg3a_rate"] = df["fg3a"].fillna(0.0) / fga
        df["fg3_pct_diff"] = df["fg3_pct"] - 0.35

        # TS% relative to league baseline
        lg_ts = df["ts_pct"].mean()
        df["ts_pct_diff"] = df["ts_pct"] - lg_ts
        df["usg_ts_interaction"] = df["usg_pct"] * df["ts_pct_diff"]
        df["ast_tov_diff"] = df["ast_pct"] - df["tm_tov_pct"]

        # Tracking defaults if missing
        if "rim_defense_diff" not in df.columns:
            df["rim_defense_diff"] = 0.0
        else:
            df["rim_defense_diff"] = df["rim_defense_diff"].fillna(0.0).apply(lambda v: _to_decimal(v, 0.0))

        if "deflections_per_100" not in df.columns:
            df["deflections_per_100"] = 0.0
        else:
            df["deflections_per_100"] = df["deflections_per_100"].fillna(0.0).apply(lambda v: float(v) if v else 0.0)

        return df

    def build_training_dataset(
        self,
        min_minutes: float = 400.0,
        start_season: str = "1996-97",
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Builds the training feature matrices (X_off, X_def) and target vectors (y_off, y_def)
        from historical seasons in the SQLite database.
        """
        query = """
        SELECT 
            pss.player_id,
            p.full_name as player_name,
            pss.season,
            pss.season_type,
            pss.team_abbreviation,
            pss.gp,
            pss.min,
            pss.fga,
            pss.fg3a,
            pss.fg3_pct,
            pss.pts,
            pss.stl,
            pss.blk,
            pss.pf,
            pas.off_rating,
            pas.def_rating,
            pas.net_rating,
            pas.ast_pct,
            pas.oreb_pct,
            pas.dreb_pct,
            pas.reb_pct,
            pas.tm_tov_pct,
            pas.ts_pct,
            pas.usg_pct,
            pas.poss,
            tas.off_rating as team_off_rating,
            tas.def_rating as team_def_rating,
            tas.net_rating as team_net_rating
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.player_id
        JOIN player_advanced_stats pas 
            ON pss.player_id = pas.player_id 
            AND pss.season = pas.season 
            AND pss.season_type = pas.season_type
        LEFT JOIN team_advanced_stats tas
            ON pss.team_id = tas.team_id
            AND pss.season = tas.season
            AND pss.season_type = tas.season_type
        WHERE pss.season_type = 'Regular Season' 
          AND pss.season >= ?
          AND pas.off_rating IS NOT NULL
          AND pas.def_rating IS NOT NULL
        """
        raw_df = self.db.query_df(query, (start_season,))
        if raw_df.empty:
            raise ValueError(f"No training data found in database for season >= {start_season}")

        features_df = self.extract_features_df(raw_df)

        # Filter by minimum minutes for training stability
        train_mask = features_df["total_minutes"] >= min_minutes
        train_df = features_df[train_mask].copy()

        # Construct Ground Truth On/Off Differentials (Points / 100 Possessions above average)
        # If team ratings are present, compute player vs team differential; otherwise calibrate to league average
        if "team_off_rating" in train_df.columns and train_df["team_off_rating"].notna().sum() > 100:
            raw_y_off = (train_df["off_rating"] - train_df["team_off_rating"].fillna(108.0))
            raw_y_def = -(train_df["def_rating"] - train_df["team_def_rating"].fillna(108.0))
        else:
            lg_off = train_df["off_rating"].mean()
            lg_def = train_df["def_rating"].mean()
            raw_y_off = train_df["off_rating"] - lg_off
            raw_y_def = -(train_df["def_rating"] - lg_def)

        # Shrink single-season noisy differential towards typical RAPM standard deviations (SD ~ 1.8 off, SD ~ 1.3 def)
        # Single-season on/off has high variance, so Bayesian regression target is regressed:
        y_off = np.clip(raw_y_off * 0.45, -6.5, 8.5)
        y_def = np.clip(raw_y_def * 0.35, -4.5, 5.5)

        X_off = train_df[OFFENSIVE_FEATURES]
        X_def = train_df[DEFENSIVE_FEATURES]

        logger.info("Constructed training dataset: %d player-seasons across %d features", len(train_df), len(OFFENSIVE_FEATURES) + len(DEFENSIVE_FEATURES))
        return X_off, X_def, y_off, y_def

    def train(
        self,
        estimator: str = "ridge",
        cv: int = 5,
        test_size: float = 0.2,
        min_minutes: float = 400.0,
        start_season: str = "1996-97",
    ) -> Dict[str, Any]:
        """
        Trains offensive and defensive regularized regression models using scikit-learn cross-validation.
        """
        X_off, X_def, y_off, y_def = self.build_training_dataset(min_minutes=min_minutes, start_season=start_season)

        # Train/Test Split
        X_o_train, X_o_test, y_o_train, y_o_test = train_test_split(X_off, y_off, test_size=test_size, random_state=42)
        X_d_train, X_d_test, y_d_train, y_d_test = train_test_split(X_def, y_def, test_size=test_size, random_state=42)

        # Standardize features
        self.off_scaler = StandardScaler()
        X_o_train_scaled = self.off_scaler.fit_transform(X_o_train)
        X_o_test_scaled = self.off_scaler.transform(X_o_test)

        self.def_scaler = StandardScaler()
        X_d_train_scaled = self.def_scaler.fit_transform(X_d_train)
        X_d_test_scaled = self.def_scaler.transform(X_d_test)

        # Select & Fit Estimator
        alphas = [0.01, 0.1, 1.0, 10.0, 50.0, 100.0, 500.0, 1000.0]
        if estimator.lower() == "elasticnet":
            self.off_model = ElasticNetCV(l1_ratio=[0.1, 0.5, 0.7, 0.9, 0.99], cv=cv, random_state=42, max_iter=3000)
            self.def_model = ElasticNetCV(l1_ratio=[0.1, 0.5, 0.7, 0.9, 0.99], cv=cv, random_state=42, max_iter=3000)
        else:
            self.off_model = RidgeCV(alphas=alphas, cv=cv)
            self.def_model = RidgeCV(alphas=alphas, cv=cv)

        self.off_model.fit(X_o_train_scaled, y_o_train)
        self.def_model.fit(X_d_train_scaled, y_d_train)

        # Out-of-sample Evaluation
        y_o_pred = self.off_model.predict(X_o_test_scaled)
        y_d_pred = self.def_model.predict(X_d_test_scaled)

        o_r2 = float(r2_score(y_o_test, y_o_pred))
        o_rmse = float(np.sqrt(mean_squared_error(y_o_test, y_o_pred)))
        o_mae = float(mean_absolute_error(y_o_test, y_o_pred))

        d_r2 = float(r2_score(y_d_test, y_d_pred))
        d_rmse = float(np.sqrt(mean_squared_error(y_d_test, y_d_pred)))
        d_mae = float(mean_absolute_error(y_d_test, y_d_pred))

        # Convert standardized coefficients back to original feature scale: beta_orig = beta_scaled / scale
        o_weights_scaled = dict(zip(OFFENSIVE_FEATURES, [float(c) for c in self.off_model.coef_]))
        d_weights_scaled = dict(zip(DEFENSIVE_FEATURES, [float(c) for c in self.def_model.coef_]))

        o_weights_raw = {
            feat: float(self.off_model.coef_[i] / self.off_scaler.scale_[i])
            for i, feat in enumerate(OFFENSIVE_FEATURES)
        }
        d_weights_raw = {
            feat: float(self.def_model.coef_[i] / self.def_scaler.scale_[i])
            for i, feat in enumerate(DEFENSIVE_FEATURES)
        }

        # Calculate unscaled intercept: c_orig = c_scaled - sum(beta_orig * mean)
        o_intercept = float(self.off_model.intercept_ - sum(o_weights_raw[feat] * self.off_scaler.mean_[i] for i, feat in enumerate(OFFENSIVE_FEATURES)))
        d_intercept = float(self.def_model.intercept_ - sum(d_weights_raw[feat] * self.def_scaler.mean_[i] for i, feat in enumerate(DEFENSIVE_FEATURES)))

        self.training_metadata = {
            "model_type": f"{estimator.upper()} Regression (CV={cv})",
            "trained_at": datetime.datetime.utcnow().isoformat(),
            "sample_size": len(X_off),
            "train_samples": len(X_o_train),
            "test_samples": len(X_o_test),
            "offensive_metrics": {
                "r2": round(o_r2, 4),
                "rmse": round(o_rmse, 4),
                "mae": round(o_mae, 4),
                "best_alpha": float(getattr(self.off_model, "alpha_", 1.0)),
            },
            "defensive_metrics": {
                "r2": round(d_r2, 4),
                "rmse": round(d_rmse, 4),
                "mae": round(d_mae, 4),
                "best_alpha": float(getattr(self.def_model, "alpha_", 1.0)),
            },
            "offensive_weights": o_weights_raw,
            "defensive_weights": d_weights_raw,
            "offensive_weights_standardized": o_weights_scaled,
            "defensive_weights_standardized": d_weights_scaled,
            "offensive_intercept": round(o_intercept, 4),
            "defensive_intercept": round(d_intercept, 4),
        }

        logger.info(
            "Model training complete. Offense R2=%.4f (RMSE=%.4f), Defense R2=%.4f (RMSE=%.4f)",
            o_r2, o_rmse, d_r2, d_rmse
        )
        return self.training_metadata

    def save_model(self, filepath: Optional[str] = None) -> str:
        """Saves trained model weights and metadata to JSON file."""
        target_path = filepath or self.weights_path
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(self.training_metadata, f, indent=2)
        logger.info("Saved trained Box LEBRON weights to: %s", target_path)
        return target_path

    def load_model(self, filepath: Optional[str] = None) -> Dict[str, Any]:
        """Loads trained weights from JSON file."""
        target_path = filepath or self.weights_path
        if not os.path.exists(target_path):
            raise FileNotFoundError(f"Model weights file not found at: {target_path}")
        with open(target_path, "r", encoding="utf-8") as f:
            self.training_metadata = json.load(f)
        return self.training_metadata
