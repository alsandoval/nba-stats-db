"""
olap.py - DuckDB Vectorized Analytical Engine for Possessions and Sub-15ms WOWY Queries.
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
import duckdb

from .bitmask import TeamSeasonBitmaskIndexer

logger = logging.getLogger(__name__)


class DuckDBPossessionEngine:
    """
    In-memory / embedded DuckDB OLAP engine for querying partitioned Parquet possession files.
    Executes vectorized bitwise With-Or-Without-You (WOWY) filtering in sub-15ms.
    """

    def __init__(
        self,
        parquet_dir: Union[str, Path] = "data/gold/possessions",
        db_path: str = ":memory:",
    ):
        self.parquet_dir = Path(parquet_dir)
        self.conn = duckdb.connect(db_path)
        self._init_views()

    def _init_views(self) -> None:
        """Registers Parquet directory as a DuckDB view if files exist."""
        parquet_glob = str(self.parquet_dir / "**" / "*.parquet").replace("\\", "/")
        try:
            self.conn.execute(
                f"""
                CREATE OR REPLACE VIEW possessions AS 
                SELECT * FROM read_parquet('{parquet_glob}')
                """
            )
            logger.info("Registered DuckDB view 'possessions' over %s", parquet_glob)
        except Exception as e:
            logger.debug("Could not register default possessions view yet: %s", e)

    def refresh_views(self) -> None:
        """Refreshes the possessions view after new Parquet files are written."""
        self._init_views()

    def query_wowy(
        self,
        season: str,
        team_id: int,
        on_player_ids: Sequence[int],
        off_player_ids: Sequence[int],
        indexer: TeamSeasonBitmaskIndexer,
    ) -> Dict[str, Any]:
        """
        Executes sub-15ms vectorized With-Or-Without-You (WOWY) query using 64-bit UINT64 bitmasks.
        
        Filter rule:
            WHERE off_team_id = ? 
              AND (off_mask & M_on = M_on) 
              AND (off_mask & M_off = 0)
        """
        m_on, m_off = indexer.create_wowy_masks(team_id, season, on_player_ids, off_player_ids)
        parquet_path = str(self.parquet_dir / f"season={season}" / "*.parquet").replace("\\", "/")

        start_time = time.perf_counter()

        sql = f"""
        SELECT 
            COUNT(*) AS total_possessions,
            COALESCE(SUM(pts), 0) AS total_points,
            COALESCE(ROUND(SUM(pts) * 100.0 / NULLIF(COUNT(*), 0), 2), 0.0) AS offensive_rating,
            COUNT(CASE WHEN possession_result LIKE '%3PT%' THEN 1 END) AS three_pt_attempts,
            COUNT(CASE WHEN possession_result = 'MADE_3PT' THEN 1 END) AS three_pt_makes,
            COUNT(CASE WHEN possession_result = 'TURNOVER' THEN 1 END) AS turnovers,
            COALESCE(ROUND(COUNT(CASE WHEN possession_result = 'TURNOVER' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 2), 0.0) AS tov_pct
        FROM read_parquet('{parquet_path}')
        WHERE off_team_id = ?
          AND (CAST(off_mask AS UBIGINT) & CAST(? AS UBIGINT) = CAST(? AS UBIGINT))
          AND (CAST(off_mask AS UBIGINT) & CAST(? AS UBIGINT) = 0)
        """

        res = self.conn.execute(sql, [team_id, m_on, m_on, m_off]).fetchone()
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return {
            "team_id": team_id,
            "season": season,
            "on_player_ids": list(on_player_ids),
            "off_player_ids": list(off_player_ids),
            "m_on": m_on,
            "m_off": m_off,
            "total_possessions": res[0] if res else 0,
            "total_points": res[1] if res else 0,
            "offensive_rating": float(res[2]) if res and res[2] is not None else 0.0,
            "three_pt_attempts": res[3] if res else 0,
            "three_pt_makes": res[4] if res else 0,
            "turnovers": res[5] if res else 0,
            "tov_pct": float(res[6]) if res and res[6] is not None else 0.0,
            "query_time_ms": round(elapsed_ms, 2),
        }

    def extract_lineup_stints(self, season: str) -> List[Dict[str, Any]]:
        """
        Compresses possession events into continuous lineup stints (~32k stints/season)
        for RAPM sparse regression modeling.
        """
        parquet_path = str(self.parquet_dir / f"season={season}" / "*.parquet").replace("\\", "/")
        sql = f"""
        SELECT 
            game_id,
            period,
            off_team_id,
            def_team_id,
            off_mask,
            def_mask,
            off_players,
            def_players,
            COUNT(*) as possessions,
            SUM(pts) as total_pts
        FROM read_parquet('{parquet_path}')
        GROUP BY 
            game_id, period, off_team_id, def_team_id, off_mask, def_mask, off_players, def_players
        ORDER BY game_id, period
        """
        records = self.conn.execute(sql).fetchall()
        stints = []
        for r in records:
            stints.append({
                "game_id": r[0],
                "period": r[1],
                "off_team_id": r[2],
                "def_team_id": r[3],
                "off_mask": r[4],
                "def_mask": r[5],
                "off_players": r[6],
                "def_players": r[7],
                "possessions": r[8],
                "total_pts": r[9],
            })
        return stints
