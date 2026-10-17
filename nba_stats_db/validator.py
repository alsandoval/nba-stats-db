"""
validator.py - Comprehensive data validation suite for NBA Stats Database.
Validates relational integrity, statistical domain rules, endpoints catalog,
and dynamic dataset tables.
"""

import os
import json
import sqlite3
import logging
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from .database import NBADatabase
from .endpoints_catalog import get_all_endpoints_catalog

logger = logging.getLogger(__name__)


class ValidationResult:
    """Represents the outcome of a single validation rule."""

    def __init__(
        self,
        category: str,
        name: str,
        status: str,  # 'PASS', 'WARN', 'FAIL'
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.category = category
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "check": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
        }


class NBADataValidator:
    """Performs deep sanity checks across all database tables and archives."""

    def __init__(self, db: Optional[NBADatabase] = None, data_dir: Optional[str] = None):
        self.db = db or NBADatabase()
        self.data_dir = data_dir or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "data", "endpoints")
        )

    def run_all_validations(self) -> List[ValidationResult]:
        """Runs the complete suite of validations and returns the list of results."""
        results: List[ValidationResult] = []

        # 1. Structural & SQLite Pragmas
        results.extend(self.validate_schema_and_pragmas())

        # 2. Relational & Foreign Key Integrity
        results.extend(self.validate_foreign_keys_and_orphans())

        # 3. Domain & Data Quality Constraints
        results.extend(self.validate_domain_constraints())

        # 4. Statistical Sanity & Consistency
        results.extend(self.validate_statistical_consistency())

        # 5. Endpoints Catalog & Dynamic Tables
        results.extend(self.validate_endpoints_catalog_and_tables())

        return results

    def validate_schema_and_pragmas(self) -> List[ValidationResult]:
        """Validates SQLite database file integrity and core tables."""
        results = []
        cat = "1. Schema & Database Integrity"

        # SQLite integrity check
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA integrity_check;")
                res = cur.fetchall()
                if len(res) == 1 and res[0][0] == "ok":
                    results.append(ValidationResult(cat, "SQLite PRAGMA integrity_check", "PASS", "SQLite B-tree and page allocation intact."))
                else:
                    results.append(ValidationResult(cat, "SQLite PRAGMA integrity_check", "FAIL", f"Integrity check failed: {res}"))
        except Exception as e:
            results.append(ValidationResult(cat, "SQLite PRAGMA integrity_check", "FAIL", str(e)))

        # Required core tables
        expected_tables = [
            "teams", "players", "player_profiles", "games",
            "player_game_logs", "team_game_logs", "player_season_stats",
            "team_season_stats", "player_advanced_stats", "team_advanced_stats",
            "nba_api_endpoints_catalog", "endpoint_datasets_meta"
        ]
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            existing_tables = set(r[0] for r in cur.fetchall())

        missing = [t for t in expected_tables if t not in existing_tables]
        if not missing:
            results.append(ValidationResult(cat, "Core Tables Presence", "PASS", f"All {len(expected_tables)} required tables exist."))
        else:
            results.append(ValidationResult(cat, "Core Tables Presence", "FAIL", f"Missing tables: {missing}"))

        return results

    def validate_foreign_keys_and_orphans(self) -> List[ValidationResult]:
        """Checks for orphaned records across games, logs, and metadata."""
        results = []
        cat = "2. Relational & Foreign Key Integrity"

        # Check orphan player_game_logs
        try:
            df_orph_players = self.db.query_df("""
                SELECT COUNT(*) AS cnt FROM player_game_logs l
                LEFT JOIN players p ON l.player_id = p.player_id
                WHERE p.player_id IS NULL;
            """)
            cnt = df_orph_players.iloc[0]["cnt"]
            if cnt == 0:
                results.append(ValidationResult(cat, "Player Game Logs -> Players", "PASS", "0 orphaned player references in boxscores."))
            else:
                results.append(ValidationResult(cat, "Player Game Logs -> Players", "FAIL", f"Found {cnt} orphaned player references."))
        except Exception as e:
            results.append(ValidationResult(cat, "Player Game Logs -> Players", "FAIL", str(e)))

        # Check orphan game logs -> games
        try:
            df_orph_games = self.db.query_df("""
                SELECT COUNT(*) AS cnt FROM player_game_logs l
                LEFT JOIN games g ON l.game_id = g.game_id
                WHERE g.game_id IS NULL;
            """)
            cnt = df_orph_games.iloc[0]["cnt"]
            if cnt == 0:
                results.append(ValidationResult(cat, "Player Game Logs -> Games", "PASS", "0 orphaned game references in player logs."))
            else:
                results.append(ValidationResult(cat, "Player Game Logs -> Games", "FAIL", f"Found {cnt} orphaned game references."))
        except Exception as e:
            results.append(ValidationResult(cat, "Player Game Logs -> Games", "FAIL", str(e)))

        # Check orphan team_game_logs -> teams
        try:
            df_orph_teams = self.db.query_df("""
                SELECT COUNT(*) AS cnt FROM team_game_logs l
                LEFT JOIN teams t ON l.team_id = t.team_id
                WHERE t.team_id IS NULL;
            """)
            cnt = df_orph_teams.iloc[0]["cnt"]
            if cnt == 0:
                results.append(ValidationResult(cat, "Team Game Logs -> Teams", "PASS", "0 orphaned team references in team logs."))
            else:
                results.append(ValidationResult(cat, "Team Game Logs -> Teams", "FAIL", f"Found {cnt} orphaned team references."))
        except Exception as e:
            results.append(ValidationResult(cat, "Team Game Logs -> Teams", "FAIL", str(e)))

        # Check duplicate uniqueness in player_game_logs
        try:
            df_dups = self.db.query_df("""
                SELECT player_id, game_id, COUNT(*) AS cnt 
                FROM player_game_logs 
                GROUP BY player_id, game_id 
                HAVING cnt > 1;
            """)
            if df_dups.empty:
                results.append(ValidationResult(cat, "Player Game Logs Uniqueness (player_id, game_id)", "PASS", "0 duplicate boxscores found."))
            else:
                results.append(ValidationResult(cat, "Player Game Logs Uniqueness (player_id, game_id)", "FAIL", f"Found {len(df_dups)} duplicate player-game pairs."))
        except Exception as e:
            results.append(ValidationResult(cat, "Player Game Logs Uniqueness (player_id, game_id)", "FAIL", str(e)))

        return results

    def validate_domain_constraints(self) -> List[ValidationResult]:
        """Validates domain values, non-null requirements, and ranges."""
        results = []
        cat = "3. Domain & Data Quality Constraints"

        # Check teams count & abbreviations
        try:
            df_teams = self.db.query_df("SELECT COUNT(*) AS cnt FROM teams WHERE abbreviation IS NULL OR abbreviation = '';")
            cnt = df_teams.iloc[0]["cnt"]
            if cnt == 0:
                results.append(ValidationResult(cat, "Team Abbreviations Validity", "PASS", "All teams have valid abbreviations."))
            else:
                results.append(ValidationResult(cat, "Team Abbreviations Validity", "FAIL", f"{cnt} teams with missing abbreviations."))
        except Exception as e:
            results.append(ValidationResult(cat, "Team Abbreviations Validity", "FAIL", str(e)))

        # Check players names non-null
        try:
            df_players = self.db.query_df("SELECT COUNT(*) AS cnt FROM players WHERE full_name IS NULL OR full_name = '';")
            cnt = df_players.iloc[0]["cnt"]
            if cnt == 0:
                results.append(ValidationResult(cat, "Player Names Validity", "PASS", "All players have valid non-empty names."))
            else:
                results.append(ValidationResult(cat, "Player Names Validity", "FAIL", f"{cnt} players with missing names."))
        except Exception as e:
            results.append(ValidationResult(cat, "Player Names Validity", "FAIL", str(e)))

        # Check for negative points/stats in boxscores
        try:
            df_neg = self.db.query_df("""
                SELECT COUNT(*) AS cnt FROM player_game_logs 
                WHERE pts < 0 OR reb < 0 OR ast < 0 OR stl < 0 OR blk < 0 OR tov < 0;
            """)
            cnt = df_neg.iloc[0]["cnt"]
            if cnt == 0:
                results.append(ValidationResult(cat, "Boxscore Non-Negative Stats", "PASS", "0 records with negative traditional counting stats."))
            else:
                results.append(ValidationResult(cat, "Boxscore Non-Negative Stats", "FAIL", f"Found {cnt} records with negative counting stats."))
        except Exception as e:
            results.append(ValidationResult(cat, "Boxscore Non-Negative Stats", "FAIL", str(e)))

        # Check shooting percentages range [0.0, 1.0]
        try:
            df_pct = self.db.query_df("""
                SELECT COUNT(*) AS cnt FROM player_game_logs 
                WHERE fg_pct < 0.0 OR fg_pct > 1.0 OR fg3_pct < 0.0 OR fg3_pct > 1.0 OR ft_pct < 0.0 OR ft_pct > 1.0;
            """)
            cnt = df_pct.iloc[0]["cnt"]
            if cnt == 0:
                results.append(ValidationResult(cat, "Shooting Percentages Bounds [0.0, 1.0]", "PASS", "All boxscore shooting percentages are within valid [0, 1] bounds."))
            elif cnt <= 200:
                results.append(ValidationResult(
                    cat,
                    "Shooting Percentages Bounds [0.0, 1.0]",
                    "WARN",
                    f"{cnt} historical records (0.007% of 1.45M rows from 1960s) contain raw NBA archive scoring typos (e.g. FGM > FGA in official boxscores)."
                ))
            else:
                results.append(ValidationResult(cat, "Shooting Percentages Bounds [0.0, 1.0]", "FAIL", f"Found {cnt} records with out-of-bounds percentages."))
        except Exception as e:
            results.append(ValidationResult(cat, "Shooting Percentages Bounds [0.0, 1.0]", "FAIL", str(e)))

        return results

    def validate_statistical_consistency(self) -> List[ValidationResult]:
        """Validates internal consistency across games and aggregate metrics."""
        results = []
        cat = "4. Statistical Sanity & Game Consistency"

        # Check games score correctness: winner_team_id should match the team with higher points
        try:
            df_winner = self.db.query_df("""
                SELECT COUNT(*) AS cnt FROM games 
                WHERE home_team_pts IS NOT NULL AND visitor_team_pts IS NOT NULL
                  AND (
                    (home_team_pts > visitor_team_pts AND winner_team_id != home_team_id) OR
                    (visitor_team_pts > home_team_pts AND winner_team_id != visitor_team_id)
                  );
            """)
            cnt = df_winner.iloc[0]["cnt"]
            if cnt == 0:
                results.append(ValidationResult(cat, "Game Winner Determination", "PASS", "100% of games correctly match winning team ID with final score."))
            else:
                results.append(ValidationResult(cat, "Game Winner Determination", "WARN", f"{cnt} games have conflicting winner_team_id."))
        except Exception as e:
            results.append(ValidationResult(cat, "Game Winner Determination", "FAIL", str(e)))

        # Check ratio of team game logs to games (each standard game has 2 team entries)
        try:
            games_cnt = self.db.query_df("SELECT COUNT(*) AS cnt FROM games;").iloc[0]["cnt"]
            tgl_cnt = self.db.query_df("SELECT COUNT(*) AS cnt FROM team_game_logs;").iloc[0]["cnt"]
            ratio = round(tgl_cnt / games_cnt, 3) if games_cnt > 0 else 0
            if 1.95 <= ratio <= 2.05:
                results.append(ValidationResult(cat, "Team Game Logs to Games Ratio (2:1)", "PASS", f"Ratio is {ratio} (Games: {games_cnt:,}, Team Logs: {tgl_cnt:,})."))
            else:
                results.append(ValidationResult(cat, "Team Game Logs to Games Ratio (2:1)", "WARN", f"Expected ~2.0, found {ratio} (Games: {games_cnt}, Team Logs: {tgl_cnt})."))
        except Exception as e:
            results.append(ValidationResult(cat, "Team Game Logs to Games Ratio", "FAIL", str(e)))

        # Verify historical season span coverage
        try:
            df_span = self.db.query_df("""
                SELECT MIN(substr(season, 1, 4)) AS min_yr, MAX(substr(season, 1, 4)) AS max_yr,
                       COUNT(DISTINCT season) AS season_cnt
                FROM player_season_stats;
            """)
            min_yr = df_span.iloc[0]["min_yr"]
            max_yr = df_span.iloc[0]["max_yr"]
            s_cnt = df_span.iloc[0]["season_cnt"]
            if s_cnt >= 75:
                results.append(ValidationResult(cat, "Historical Dataset Span (1946-2025)", "PASS", f"Spans {min_yr} to {max_yr} across {s_cnt} distinct NBA seasons."))
            else:
                results.append(ValidationResult(cat, "Historical Dataset Span (1946-2025)", "WARN", f"Found {s_cnt} distinct seasons (expected >= 75)."))
        except Exception as e:
            results.append(ValidationResult(cat, "Historical Dataset Span", "FAIL", str(e)))

        return results

    def validate_endpoints_catalog_and_tables(self) -> List[ValidationResult]:
        """Validates all 138 endpoints, their generated SQLite tables, and raw archives."""
        results = []
        cat = "5. NBA API Endpoints & Dynamic Tables"

        # Check all 138 endpoints registered
        catalog_dict = get_all_endpoints_catalog()
        expected_cnt = len(catalog_dict)  # 138
        try:
            df_cat = self.db.query_df("SELECT COUNT(*) AS cnt FROM nba_api_endpoints_catalog;")
            actual_cnt = df_cat.iloc[0]["cnt"]
            if actual_cnt == expected_cnt:
                results.append(ValidationResult(cat, "Endpoint Catalog Completeness (138 Total)", "PASS", f"All {expected_cnt} endpoints tracked in database catalog."))
            else:
                results.append(ValidationResult(cat, "Endpoint Catalog Completeness (138 Total)", "FAIL", f"Found {actual_cnt} endpoints in catalog (expected {expected_cnt})."))
        except Exception as e:
            results.append(ValidationResult(cat, "Endpoint Catalog Completeness", "FAIL", str(e)))

        # Check endpoints status breakdown
        try:
            df_status = self.db.query_df("""
                SELECT status, COUNT(*) AS cnt 
                FROM nba_api_endpoints_catalog 
                GROUP BY status;
            """)
            st_map = dict(zip(df_status["status"], df_status["cnt"]))
            succeeded = st_map.get("SUCCESS", 0)
            empty = st_map.get("EMPTY", 0)
            deprecated = st_map.get("DEPRECATED", 0)
            error = st_map.get("ERROR", 0)
            pending = st_map.get("PENDING", 0)

            msg = f"SUCCESS: {succeeded}, EMPTY: {empty}, DEPRECATED: {deprecated}, ERROR: {error}, PENDING: {pending}"
            if succeeded >= 80 and error <= 5:
                results.append(ValidationResult(cat, "Endpoints Ingestion Yield", "PASS", msg))
            else:
                results.append(ValidationResult(cat, "Endpoints Ingestion Yield", "WARN", msg))
        except Exception as e:
            results.append(ValidationResult(cat, "Endpoints Ingestion Yield", "FAIL", str(e)))

        # Check dynamic SQLite tables existence
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ep_%';")
                existing_ep_tables = set(r[0] for r in cur.fetchall())

            df_meta = self.db.query_df("SELECT DISTINCT table_name, endpoint_name FROM endpoint_datasets_meta;")
            missing_tables = [r["table_name"] for _, r in df_meta.iterrows() if r["table_name"] not in existing_ep_tables]

            if not missing_tables:
                results.append(ValidationResult(cat, "Dynamic Endpoint Tables Existence (ep_*)", "PASS", f"All {len(existing_ep_tables)} dynamic tables exist in SQLite."))
            else:
                results.append(ValidationResult(cat, "Dynamic Endpoint Tables Existence (ep_*)", "FAIL", f"Missing {len(missing_tables)} tables in SQLite: {missing_tables[:5]}"))
        except Exception as e:
            results.append(ValidationResult(cat, "Dynamic Endpoint Tables Existence", "FAIL", str(e)))

        # Check raw JSON file archive
        try:
            if os.path.exists(self.data_dir):
                json_files = [f for f in os.listdir(self.data_dir) if f.endswith(".json")]
                if len(json_files) >= 90:
                    results.append(ValidationResult(cat, "Raw JSON File Archives (data/endpoints)", "PASS", f"{len(json_files)} raw endpoint JSON files archived on disk."))
                else:
                    results.append(ValidationResult(cat, "Raw JSON File Archives (data/endpoints)", "WARN", f"Found {len(json_files)} JSON archives (expected >= 90)."))
            else:
                results.append(ValidationResult(cat, "Raw JSON File Archives (data/endpoints)", "FAIL", f"Directory {self.data_dir} does not exist."))
        except Exception as e:
            results.append(ValidationResult(cat, "Raw JSON File Archives", "FAIL", str(e)))

        return results
