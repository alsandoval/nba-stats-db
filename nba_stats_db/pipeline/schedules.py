"""
schedules.py - Dagster Schedules for NBA Stats DB daily batch processing.
"""

from dagster import ScheduleDefinition, define_asset_job

# Define job that materializes the entire daily possession ingestion pipeline
daily_possession_ingestion_job = define_asset_job(
    name="daily_nba_possession_ingestion_job",
    selection=["daily_games_slate", "possessions_parquet", "duckdb_olap_refresh"],
    description="Daily batch ingestion executing PossessionStateMachine and refreshing DuckDB Parquet OLAP views.",
)

# Daily 4:00 AM PT Schedule (following final West Coast game finalization)
daily_4am_pt_schedule = ScheduleDefinition(
    job=daily_possession_ingestion_job,
    cron_schedule="0 4 * * *",
    execution_timezone="America/Los_Angeles",
    description="Fires every morning at 4:00 AM Pacific Time to ingest the completed NBA slate.",
)
