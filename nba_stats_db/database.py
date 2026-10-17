"""
database.py - SQLite connection manager and database operations for NBA Stats DB.
"""

import os
import sqlite3
import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
import pandas as pd
from .schema import SCHEMA_DDL

logger = logging.getLogger(__name__)

DEFAULT_DB_FILENAME = "nba_stats.db"


class NBADatabase:
    """Database interface for interacting with the NBA stats SQLite database."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to nba_stats.db in current working directory
            self.db_path = os.path.abspath(DEFAULT_DB_FILENAME)
        else:
            self.db_path = os.path.abspath(db_path)

    def get_connection(self) -> sqlite3.Connection:
        """Returns a configured SQLite connection with foreign key support enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_database(self) -> None:
        """Creates all tables and indexes if they do not already exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_DDL)
            conn.commit()
        logger.info("Initialized NBA stats database at: %s", self.db_path)

    def execute_query(
        self, query: str, params: Union[Tuple[Any, ...], Dict[str, Any]] = ()
    ) -> List[sqlite3.Row]:
        """Executes a SELECT query and returns a list of Rows."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def query_df(
        self, query: str, params: Union[Tuple[Any, ...], Dict[str, Any]] = ()
    ) -> pd.DataFrame:
        """Executes a SELECT query and returns the results as a Pandas DataFrame."""
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)

    def execute_non_query(
        self, query: str, params: Union[Tuple[Any, ...], Dict[str, Any]] = ()
    ) -> int:
        """Executes an INSERT/UPDATE/DELETE query and returns rowcount."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount

    def upsert_rows(
        self,
        table_name: str,
        rows: List[Dict[str, Any]],
        conflict_keys: List[str],
    ) -> int:
        """
        Inserts or updates rows into a table.
        Using SQLite's ON CONFLICT DO UPDATE.
        """
        if not rows:
            return 0

        # Filter row keys to ensure all rows match first row columns
        columns = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)

        update_cols = [c for c in columns if c not in conflict_keys]
        conflict_str = ", ".join(conflict_keys)

        if update_cols:
            update_assignments = ", ".join([f"{c} = excluded.{c}" for c in update_cols])
            sql = f"""
            INSERT INTO {table_name} ({col_names})
            VALUES ({placeholders})
            ON CONFLICT({conflict_str}) DO UPDATE SET
            {update_assignments}
            """
        else:
            sql = f"""
            INSERT OR IGNORE INTO {table_name} ({col_names})
            VALUES ({placeholders})
            """

        values = [[row.get(col) for col in columns] for row in rows]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, values)
            conn.commit()
            return cursor.rowcount

    def get_table_counts(self) -> Dict[str, int]:
        """Returns row count for each table in the database."""
        tables = [
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
        counts = {}
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for t in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {t}")
                    counts[t] = cursor.fetchone()[0]
                except sqlite3.OperationalError:
                    counts[t] = 0
        return counts

    def register_endpoints_catalog(self, catalog_dict: Dict[str, Dict[str, Any]]) -> int:
        """Populates or updates the nba_api_endpoints_catalog table with available endpoints."""
        import json
        rows = []
        for name, meta in catalog_dict.items():
            rows.append({
                "endpoint_name": name,
                "module": meta.get("module", "nba_api.stats.endpoints"),
                "category": meta.get("category", "General"),
                "docstring": meta.get("docstring", ""),
                "required_params": json.dumps(meta.get("required_params", [])),
                "default_params": json.dumps(meta.get("default_test_params", {})),
            })
        return self.upsert_rows("nba_api_endpoints_catalog", rows, conflict_keys=["endpoint_name"])

    def save_endpoint_dataset(
        self,
        endpoint_name: str,
        dataset_name: str,
        df: pd.DataFrame,
    ) -> str:
        """
        Saves a DataFrame returned by an endpoint into a dedicated SQLite table
        named ep_<endpoint_name>_<dataset_name> (sanitized) and records metadata.
        """
        import re
        import json
        import datetime

        # Sanitize table name
        safe_ep = re.sub(r"[^a-zA-Z0-9_]", "_", endpoint_name).lower()
        safe_ds = re.sub(r"[^a-zA-Z0-9_]", "_", dataset_name).lower()
        table_name = f"ep_{safe_ep}_{safe_ds}"

        # Clean column names for SQLite
        df_clean = df.copy()
        clean_cols = []
        for c in df_clean.columns:
            clean_c = re.sub(r"[^a-zA-Z0-9_]", "_", str(c))
            clean_cols.append(clean_c)
        df_clean.columns = clean_cols

        # Serialize complex python objects (dicts, lists) into JSON strings for SQLite
        for c in df_clean.columns:
            df_clean[c] = df_clean[c].apply(lambda v: json.dumps(v) if isinstance(v, (dict, list)) else v)

        # Write to SQLite
        with self.get_connection() as conn:
            df_clean.to_sql(table_name, conn, if_exists="replace", index=False)

            # Record in endpoint_datasets_meta
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM endpoint_datasets_meta 
                WHERE endpoint_name = ? AND dataset_name = ?
                """,
                (endpoint_name, dataset_name),
            )
            cursor.execute(
                """
                INSERT INTO endpoint_datasets_meta 
                (endpoint_name, dataset_name, table_name, row_count, columns_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    endpoint_name,
                    dataset_name,
                    table_name,
                    len(df_clean),
                    json.dumps(list(df_clean.columns)),
                    now,
                ),
            )
            conn.commit()

        return table_name

    def update_endpoint_status(
        self,
        endpoint_name: str,
        status: str,
        result_sets_count: int = 0,
        total_rows: int = 0,
        table_names: Optional[List[str]] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Updates the status and stats of an endpoint in the catalog."""
        import json
        import datetime

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        tbl_json = json.dumps(table_names or [])

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE nba_api_endpoints_catalog
                SET status = ?,
                    result_sets_count = ?,
                    total_rows = ?,
                    table_names = ?,
                    last_downloaded_at = ?,
                    error_message = ?
                WHERE endpoint_name = ?
                """,
                (
                    status,
                    result_sets_count,
                    total_rows,
                    tbl_json,
                    now,
                    error_message,
                    endpoint_name,
                ),
            )
            conn.commit()

    def get_endpoints_catalog(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Queries the endpoint catalog with optional filters."""
        sql = "SELECT * FROM nba_api_endpoints_catalog WHERE 1=1"
        params: List[Any] = []
        if category:
            sql += " AND category = ?"
            params.append(category)
        if status:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY category, endpoint_name"

        df = self.query_df(sql, tuple(params))
        return df.to_dict(orient="records")

    def get_endpoint_detail(self, endpoint_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves details, dataset tables, and sample data for an endpoint."""
        import json
        df_ep = self.query_df(
            "SELECT * FROM nba_api_endpoints_catalog WHERE endpoint_name = ?",
            (endpoint_name,),
        )
        if df_ep.empty:
            return None

        ep_data = df_ep.iloc[0].to_dict()
        if ep_data.get("table_names"):
            try:
                ep_data["table_names"] = json.loads(ep_data["table_names"])
            except Exception:
                pass
        if ep_data.get("required_params"):
            try:
                ep_data["required_params"] = json.loads(ep_data["required_params"])
            except Exception:
                pass
        if ep_data.get("default_params"):
            try:
                ep_data["default_params"] = json.loads(ep_data["default_params"])
            except Exception:
                pass

        # Fetch metadata about its datasets
        meta_df = self.query_df(
            "SELECT * FROM endpoint_datasets_meta WHERE endpoint_name = ?",
            (endpoint_name,),
        )
        datasets = []
        for _, row in meta_df.iterrows():
            tbl = row["table_name"]
            # Fetch preview (first 5 rows)
            preview_df = self.query_df(f"SELECT * FROM {tbl} LIMIT 5")
            cols = json.loads(row["columns_json"]) if row.get("columns_json") else list(preview_df.columns)
            datasets.append({
                "dataset_name": row["dataset_name"],
                "table_name": tbl,
                "row_count": row["row_count"],
                "columns": cols,
                "preview_rows": preview_df.to_dict(orient="records"),
            })

        ep_data["datasets"] = datasets
        return ep_data
