"""
parquet_store.py - Apache Parquet Partitioned Storage for NBA Possessions.

Uses Polars and PyArrow for high-performance zero-copy serialization into
partitioned Parquet files organized by season:
    data/gold/possessions/season={YYYY-YY}/*.parquet
"""

import os
from pathlib import Path
from typing import List, Optional, Union
import polars as pl

from .state_machine import PossessionEvent

POSSESSION_SCHEMA = {
    "game_id": pl.Utf8,
    "season": pl.Utf8,
    "period": pl.Int32,
    "possession_id": pl.Int32,
    "clock_seconds": pl.Float64,
    "off_team_id": pl.Int64,
    "def_team_id": pl.Int64,
    "off_players": pl.List(pl.Int64),
    "def_players": pl.List(pl.Int64),
    "off_mask": pl.UInt64,
    "def_mask": pl.UInt64,
    "pts": pl.Int32,
    "possession_result": pl.Utf8,
    "shot_x": pl.Float64,
    "shot_y": pl.Float64,
    "shot_dist": pl.Float64,
    "shot_made": pl.Boolean,
}


class ParquetPossessionStore:
    """Manages reading and writing partitioned Parquet possession tables."""

    def __init__(self, base_dir: Union[str, Path] = "data/gold/possessions"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _season_dir(self, season: str) -> Path:
        s_dir = self.base_dir / f"season={season}"
        s_dir.mkdir(parents=True, exist_ok=True)
        return s_dir

    def possessions_to_df(self, possessions: List[PossessionEvent]) -> pl.DataFrame:
        """Converts a list of PossessionEvent dataclasses to a typed Polars DataFrame."""
        if not possessions:
            return pl.DataFrame(schema=POSSESSION_SCHEMA)

        data = {
            "game_id": [p.game_id for p in possessions],
            "season": [p.season for p in possessions],
            "period": [p.period for p in possessions],
            "possession_id": [p.possession_id for p in possessions],
            "clock_seconds": [p.clock_seconds for p in possessions],
            "off_team_id": [p.off_team_id for p in possessions],
            "def_team_id": [p.def_team_id for p in possessions],
            "off_players": [p.off_players for p in possessions],
            "def_players": [p.def_players for p in possessions],
            "off_mask": [p.off_mask for p in possessions],
            "def_mask": [p.def_mask for p in possessions],
            "pts": [p.pts for p in possessions],
            "possession_result": [p.possession_result for p in possessions],
            "shot_x": [p.shot_x for p in possessions],
            "shot_y": [p.shot_y for p in possessions],
            "shot_dist": [p.shot_dist for p in possessions],
            "shot_made": [p.shot_made for p in possessions],
        }
        return pl.DataFrame(data, schema=POSSESSION_SCHEMA)

    def write_game_possessions(
        self, season: str, game_id: str, possessions: List[PossessionEvent]
    ) -> Path:
        """Writes game possessions to a Parquet file partitioned by season."""
        df = self.possessions_to_df(possessions)
        target_path = self._season_dir(season) / f"possessions_{game_id}.parquet"
        df.write_parquet(target_path, compression="zstd")
        return target_path

    def load_season(self, season: str) -> pl.DataFrame:
        """Loads all possession Parquet files for a given season."""
        s_dir = self._season_dir(season)
        parquet_files = list(s_dir.glob("*.parquet"))
        if not parquet_files:
            return pl.DataFrame(schema=POSSESSION_SCHEMA)
        return pl.read_parquet(s_dir / "*.parquet")

    def count_possessions(self, season: str) -> int:
        """Returns total possession count for a season."""
        df = self.load_season(season)
        return len(df)
