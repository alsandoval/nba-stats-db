"""
definitions.py - Dagster Definitions entry point for Antigravity NBA Analytics Platform.
"""

from dagster import Definitions

from .assets import daily_games_slate, possessions_parquet, duckdb_olap_refresh
from .schedules import daily_possession_ingestion_job, daily_4am_pt_schedule

defs = Definitions(
    assets=[daily_games_slate, possessions_parquet, duckdb_olap_refresh],
    jobs=[daily_possession_ingestion_job],
    schedules=[daily_4am_pt_schedule],
)
