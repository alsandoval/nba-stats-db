"""
box_lebron.py - Replicated Box LEBRON statistical model, archetype classifier,
and Wins Added pipeline for the NBA Stats Database.

Based on BBall Index's LEBRON framework (Krishna Narsu & Tim/Cranjis McBasketball),
incorporating box score rates, player tracking (rim protection, passing, drives),
and hustle metrics (deflections, screen assists) normalized per 100 possessions.
"""

import os
import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from .database import NBADatabase

logger = logging.getLogger(__name__)

# Constants for LEBRON & WAR Calculations
REPLACEMENT_LEVEL = -2.0  # Net rating per 100 possessions for replacement player
POINTS_PER_WIN = 3.15     # Marginal points per 100 possessions to win conversion

# Offensive Archetypes
OFFENSIVE_ARCHETYPES = [
    "Primary Ball Handler",
    "Secondary Ball Handler",
    "Shot Creator",
    "Slasher",
    "Movement Shooter",
    "Stationary Shooter",
    "Roll & Cut Big",
    "Post Up Big",
    "Stretch Big",
    "Low Usage Connector",
]

# Defensive Archetypes
DEFENSIVE_ARCHETYPES = [
    "Rim Protector",
    "Mobile Anchor",
    "Point of Attack Defender",
    "Wing Stopper",
    "Chaser",
    "Off-Ball Helper",
    "Low Activity",
]


def _to_decimal(val: Optional[float], default: float = 0.0) -> float:
    """Converts a percentage to decimal (e.g. 15.0 -> 0.15, 0.15 -> 0.15)."""
    if val is None or pd.isna(val):
        return default
    try:
        f = float(val)
        return f / 100.0 if f > 1.0 else f
    except (ValueError, TypeError):
        return default


class BoxLEBRONModel:
    """
    Calculates Box LEBRON (O-LEBRON, D-LEBRON, Total Box LEBRON, Wins Added)
    and classifies players into tactical offensive and defensive archetypes.
    Supports dynamic inference with trained machine learning regression weights.
    """

    def __init__(self, db: Optional[NBADatabase] = None, weights_file: Optional[str] = None):
        self.db = db or NBADatabase()
        default_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
        self.weights_file = weights_file or os.path.join(default_dir, "box_lebron_weights.json")
        self.trained_weights: Optional[Dict[str, Any]] = None
        self.load_trained_weights()

    def load_trained_weights(self) -> bool:
        """Loads trained ML weights if JSON file exists."""
        import json
        if os.path.exists(self.weights_file):
            try:
                with open(self.weights_file, "r", encoding="utf-8") as f:
                    self.trained_weights = json.load(f)
                logger.info("Loaded trained Box LEBRON weights from: %s", self.weights_file)
                return True
            except Exception as e:
                logger.warning("Failed to load weights from %s: %s", self.weights_file, e)
                self.trained_weights = None
        return False

    def classify_offensive_archetype(self, row: pd.Series) -> str:
        """Classifies a player into an offensive archetype based on usage, passing, shooting, and rebounding."""
        usg = _to_decimal(row.get("usg_pct"), 0.18)
        ast_pct = _to_decimal(row.get("ast_pct"), 0.12)
        fg3a = row.get("fg3a", 0.0) or 0.0
        fga = max(row.get("fga", 0.0) or 1.0, 0.1)
        fg3a_rate = fg3a / fga
        oreb_pct = _to_decimal(row.get("oreb_pct"), 0.04)
        reb_pct = _to_decimal(row.get("reb_pct"), 0.08)
        fg_pct = _to_decimal(row.get("fg_pct"), 0.45)

        # Bigs criteria
        if reb_pct >= 0.13 or oreb_pct >= 0.08:
            if fg3a_rate >= 0.30:
                return "Stretch Big"
            if ast_pct >= 0.16 or usg >= 0.24:
                return "Post Up Big"
            if fg_pct >= 0.56:
                return "Roll & Cut Big"

        # Perimeter / Guards / Wings
        if usg >= 0.25 and ast_pct >= 0.25:
            return "Primary Ball Handler"
        if usg >= 0.20 and ast_pct >= 0.18:
            return "Secondary Ball Handler"
        if usg >= 0.24 and fg3a_rate < 0.40:
            return "Shot Creator"
        if usg >= 0.20 and fg3a_rate < 0.30:
            return "Slasher"
        if fg3a_rate >= 0.50:
            return "Movement Shooter"
        if fg3a_rate >= 0.35:
            return "Stationary Shooter"
        if usg >= 0.18:
            return "Secondary Ball Handler"

        return "Low Usage Connector"

    def classify_defensive_archetype(self, row: pd.Series) -> str:
        """Classifies a player into a defensive archetype based on rim protection, steals, blocks, deflections, and rebounds."""
        dreb_pct = _to_decimal(row.get("dreb_pct"), 0.14)
        blk = row.get("blk", 0.0) or 0.0
        stl = row.get("stl", 0.0) or 0.0
        mpg = max(row.get("min", 0.0) or 0.0, 1.0)

        stl_per36 = (stl / mpg) * 36.0
        blk_per36 = (blk / mpg) * 36.0
        ast_pct = _to_decimal(row.get("ast_pct"), 0.12)

        # Interior Anchors
        if blk_per36 >= 1.8 and dreb_pct >= 0.18:
            return "Rim Protector"
        if dreb_pct >= 0.20 and blk_per36 >= 1.0:
            return "Mobile Anchor"

        # Perimeter & Wing defenders
        if stl_per36 >= 1.6 and ast_pct >= 0.20:
            return "Point of Attack Defender"
        if stl_per36 >= 1.4:
            return "Wing Stopper"
        if stl_per36 >= 1.1 and mpg >= 20.0:
            return "Chaser"
        if dreb_pct >= 0.14 or blk_per36 >= 0.8:
            return "Off-Ball Helper"

        return "Low Activity"

    def compute_o_lebron(self, row: pd.Series, lg_ts_pct: float = 0.57) -> float:
        """
        Computes Offensive LEBRON (O-LEBRON) in points per 100 possessions above league average.
        Uses trained ML weights if available, otherwise falls back to calibrated equations.
        """
        usg = _to_decimal(row.get("usg_pct"), 0.20)
        ts = _to_decimal(row.get("ts_pct"), lg_ts_pct)
        ast_pct = _to_decimal(row.get("ast_pct"), 0.15)
        tov_pct = _to_decimal(row.get("tm_tov_pct"), 0.10)
        oreb_pct = _to_decimal(row.get("oreb_pct"), 0.045)
        fg3a = row.get("fg3a", 0.0) or 0.0
        fga = max(row.get("fga", 0.0) or 1.0, 0.1)
        fg3a_rate = fg3a / fga
        fg3_pct = _to_decimal(row.get("fg3_pct"), 0.35)
        mpg = max(row.get("min", 0.0) or 0.0, 1.0)
        pts_per36 = ((row.get("pts", 0.0) or 0.0) / mpg) * 36.0

        ts_diff = ts - lg_ts_pct

        # 1. Trained ML Weights Inference
        if self.trained_weights and "offensive_weights" in self.trained_weights:
            w = self.trained_weights["offensive_weights"]
            intercept = self.trained_weights.get("offensive_intercept", 0.0)
            feat_vals = {
                "usg_pct": usg,
                "ts_pct_diff": ts_diff,
                "usg_ts_interaction": usg * ts_diff,
                "ast_pct": ast_pct,
                "tm_tov_pct": tov_pct,
                "ast_tov_diff": ast_pct - tov_pct,
                "oreb_pct": oreb_pct,
                "fg3a_rate": fg3a_rate,
                "fg3_pct_diff": fg3_pct - 0.35,
                "pts_per_36": pts_per36,
            }
            pred = intercept + sum(w.get(k, 0.0) * v for k, v in feat_vals.items())
            clamped = float(np.clip(pred, -6.0, 8.5))
            return float(np.round(clamped, 2))

        # 2. Calibrated Baseline Fallback
        scoring_val = 22.0 * (usg ** 1.1) * ts_diff + 7.5 * (usg - 0.20)
        creation_val = 10.0 * (ast_pct - 0.15) - 12.0 * (tov_pct - 0.10)
        oreb_val = 8.0 * (oreb_pct - 0.045)
        spacing_val = 0.25 * (fg3a / max(row.get("gp", 1.0) or 1.0, 1.0)) * (fg3_pct - 0.33)

        tracking_boost = 0.0
        pot_ast = row.get("pot_ast_per_100")
        if pot_ast is not None and not pd.isna(pot_ast):
            tracking_boost += 0.06 * (float(pot_ast) - 8.0)

        raw_o = scoring_val + creation_val + oreb_val + spacing_val + tracking_boost
        clamped_o = float(np.clip(raw_o, -6.0, 8.5))
        return float(np.round(clamped_o, 2))

    def compute_d_lebron(self, row: pd.Series) -> float:
        """
        Computes Defensive LEBRON (D-LEBRON) in points per 100 possessions above league average.
        Uses trained ML weights if available, otherwise falls back to calibrated equations.
        """
        dreb_pct = _to_decimal(row.get("dreb_pct"), 0.14)
        reb_pct = _to_decimal(row.get("reb_pct"), 0.09)
        stl = row.get("stl", 0.0) or 0.0
        blk = row.get("blk", 0.0) or 0.0
        pf = row.get("pf", 0.0) or 0.0
        mpg = max(row.get("min", 0.0) or 0.0, 1.0)

        stl_per36 = (stl / mpg) * 36.0
        blk_per36 = (blk / mpg) * 36.0
        pf_per36 = (pf / mpg) * 36.0

        rim_diff = _to_decimal(row.get("rim_defense_diff"), 0.0)
        defl = float(row.get("deflections_per_100") or 0.0)

        # 1. Trained ML Weights Inference
        if self.trained_weights and "defensive_weights" in self.trained_weights:
            w = self.trained_weights["defensive_weights"]
            intercept = self.trained_weights.get("defensive_intercept", 0.0)
            feat_vals = {
                "dreb_pct": dreb_pct,
                "stl_per_36": stl_per36,
                "blk_per_36": blk_per36,
                "pf_per_36": pf_per36,
                "reb_pct": reb_pct,
                "rim_defense_diff": rim_diff,
                "deflections_per_100": defl,
            }
            pred = intercept + sum(w.get(k, 0.0) * v for k, v in feat_vals.items())
            clamped = float(np.clip(pred, -4.0, 5.5))
            return float(np.round(clamped, 2))

        # 2. Calibrated Baseline Fallback
        event_val = 1.25 * (stl_per36 - 1.2) + 0.90 * (blk_per36 - 0.6)
        dreb_val = 5.5 * (dreb_pct - 0.14)
        tracking_def = -10.0 * rim_diff + (0.25 * (defl - 2.5) if defl > 0 else 0.0)

        raw_d = event_val + dreb_val + tracking_def
        clamped_d = float(np.clip(raw_d * 0.70, -4.0, 5.5))
        return float(np.round(clamped_d, 2))

    def fetch_season_raw_data(self, season: str, season_type: str = "Regular Season") -> pd.DataFrame:
        """Pulls combined box score, advanced stats, and available tracking stats for a season."""
        query = """
        SELECT 
            pss.player_id,
            p.full_name as player_name,
            pss.season,
            pss.season_type,
            pss.team_abbreviation,
            pss.age,
            pss.gp,
            pss.min,
            pss.fgm,
            pss.fga,
            pss.fg_pct,
            pss.fg3m,
            pss.fg3a,
            pss.fg3_pct,
            pss.ftm,
            pss.fta,
            pss.ft_pct,
            pss.oreb,
            pss.dreb,
            pss.reb,
            pss.ast,
            pss.stl,
            pss.blk,
            pss.tov,
            pss.pf,
            pss.pts,
            pss.plus_minus,
            pas.off_rating,
            pas.def_rating,
            pas.net_rating,
            pas.ast_pct,
            pas.ast_to,
            pas.ast_ratio,
            pas.oreb_pct,
            pas.dreb_pct,
            pas.reb_pct,
            pas.tm_tov_pct,
            pas.efg_pct,
            pas.ts_pct,
            pas.usg_pct,
            pas.pace,
            pas.poss
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.player_id
        LEFT JOIN player_advanced_stats pas 
            ON pss.player_id = pas.player_id 
            AND pss.season = pas.season 
            AND pss.season_type = pas.season_type
        WHERE pss.season = ? AND pss.season_type = ?
        """
        df = self.db.query_df(query, (season, season_type))
        if df.empty:
            logger.warning("No player season data found for %s %s", season, season_type)
            return df

        # Try to join tracking rim defense if table exists
        try:
            pt_def_query = """
            SELECT player_id, (d_fg_pct - fg_pct) as rim_defense_diff
            FROM ep_leaguedashptdefend_leaguedashptdefend
            """
            pt_def_df = self.db.query_df(pt_def_query)
            if not pt_def_df.empty and "player_id" in pt_def_df.columns:
                df = df.merge(pt_def_df, on="player_id", how="left")
            else:
                df["rim_defense_diff"] = None
        except Exception:
            df["rim_defense_diff"] = None

        # Try to join hustle deflections if table exists
        try:
            hustle_query = """
            SELECT player_id, deflections as deflections_per_100
            FROM ep_leaguehustlestatsplayer_hustlestatsplayer
            """
            hustle_df = self.db.query_df(hustle_query)
            if not hustle_df.empty and "player_id" in hustle_df.columns:
                df = df.merge(hustle_df, on="player_id", how="left")
            else:
                df["deflections_per_100"] = None
        except Exception:
            df["deflections_per_100"] = None

        return df

    def compute_season_box_lebron(self, season: str, season_type: str = "Regular Season") -> pd.DataFrame:
        """
        Computes Box LEBRON, Archetypes, Wins Added, and Percentiles for an entire season.
        """
        df = self.fetch_season_raw_data(season, season_type)
        if df.empty:
            return pd.DataFrame()

        # Calculate Total Minutes (since min in player_season_stats is MPG)
        df["total_minutes"] = np.round(df["min"].fillna(0.0) * df["gp"].fillna(1), 1)

        # Estimate possessions if missing
        def estimate_poss(row):
            if row.get("poss") and not pd.isna(row["poss"]) and row["poss"] > 0:
                return float(row["poss"])
            tot_min = row.get("total_minutes", 0.0) or 0.0
            pace = row.get("pace", 99.0) or 99.0
            # Team possessions played by player = (minutes / 48) * pace
            return (tot_min / 48.0) * pace

        df["possessions"] = np.round(df.apply(estimate_poss, axis=1), 0)

        # League mean TS%
        qualified = df[df["total_minutes"] >= 300]
        lg_ts = qualified["ts_pct"].apply(lambda v: _to_decimal(v, 0.57)).mean() if not qualified.empty else 0.57

        # 1. Compute Archetypes
        df["offensive_archetype"] = df.apply(self.classify_offensive_archetype, axis=1)
        df["defensive_archetype"] = df.apply(self.classify_defensive_archetype, axis=1)

        # 2. Compute O-LEBRON & D-LEBRON
        df["o_lebron"] = df.apply(lambda r: self.compute_o_lebron(r, lg_ts), axis=1)
        df["d_lebron"] = df.apply(self.compute_d_lebron, axis=1)
        df["box_lebron"] = np.round(df["o_lebron"] + df["d_lebron"], 2)

        # 3. Compute Wins Added (LEBRON WAR)
        df["wins_added"] = np.round(
            ((df["box_lebron"] - REPLACEMENT_LEVEL) * df["possessions"]) / (100.0 * POINTS_PER_WIN),
            2
        )

        # 4. Compute Percentiles for qualified players (total_minutes >= 300 minutes)
        qual_mask = df["total_minutes"] >= 300
        df["o_lebron_percentile"] = 50.0
        df["d_lebron_percentile"] = 50.0
        df["box_lebron_percentile"] = 50.0

        if qual_mask.sum() > 0:
            df.loc[qual_mask, "o_lebron_percentile"] = np.round(
                df.loc[qual_mask, "o_lebron"].rank(pct=True) * 100.0, 1
            )
            df.loc[qual_mask, "d_lebron_percentile"] = np.round(
                df.loc[qual_mask, "d_lebron"].rank(pct=True) * 100.0, 1
            )
            df.loc[qual_mask, "box_lebron_percentile"] = np.round(
                df.loc[qual_mask, "box_lebron"].rank(pct=True) * 100.0, 1
            )

        df["updated_at"] = datetime.datetime.utcnow().isoformat()
        return df

    def save_season_box_lebron(self, season: str, season_type: str = "Regular Season") -> int:
        """Computes and upserts Box LEBRON ratings into the database."""
        df = self.compute_season_box_lebron(season, season_type)
        if df.empty:
            return 0

        # Replace 'min' with total_minutes for storing total minutes played
        df["min"] = df["total_minutes"]

        columns_to_save = [
            "player_id", "season", "season_type", "player_name", "team_abbreviation",
            "age", "gp", "min", "possessions", "offensive_archetype", "defensive_archetype",
            "o_lebron", "d_lebron", "box_lebron", "wins_added",
            "o_lebron_percentile", "d_lebron_percentile", "box_lebron_percentile",
            "usg_pct", "ts_pct", "ast_pct", "reb_pct",
            "rim_defense_diff", "deflections_per_100", "updated_at"
        ]

        for col in columns_to_save:
            if col not in df.columns:
                df[col] = None

        df_to_save = df[columns_to_save].rename(columns={
            "usg_pct": "usage_pct",
        })

        records = df_to_save.to_dict(orient="records")
        clean_records = []
        for r in records:
            clean_row = {}
            for k, v in r.items():
                if pd.isna(v):
                    clean_row[k] = None
                else:
                    clean_row[k] = v
            clean_records.append(clean_row)

        inserted = self.db.upsert_rows(
            table_name="box_lebron_ratings",
            rows=clean_records,
            conflict_keys=["player_id", "season", "season_type"]
        )
        logger.info("Saved %d Box LEBRON records for %s %s", inserted, season, season_type)
        return inserted

    def compute_all_seasons(self, season_type: str = "Regular Season") -> Dict[str, int]:
        """Computes and stores Box LEBRON ratings for all available seasons in the database."""
        seasons_df = self.db.query_df(
            "SELECT DISTINCT season FROM player_season_stats WHERE season_type = ? ORDER BY season",
            (season_type,)
        )
        results = {}
        if seasons_df.empty:
            logger.warning("No seasons found in player_season_stats.")
            return results

        for season in seasons_df["season"]:
            logger.info("Computing Box LEBRON for season %s...", season)
            count = self.save_season_box_lebron(season, season_type)
            results[season] = count

        return results
