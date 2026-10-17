"""
download_all_history.py - Downloads the entire 78-year NBA dataset from 2024-25 down to 1946-47.
Runs in reverse chronological order with live progress tracking and idempotent database upserts.
"""

import sys
import time
import logging

# Ensure UTF-8 console output for player names
if sys.stdout.encoding != "utf-8" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from nba_stats_db.database import NBADatabase
from nba_stats_db.ingestion import NBADataIngestor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("historical_downloader")


def progress_callback(idx, total, season, status):
    print(f"[{idx}/{total}] Season {season}: {status.upper()}", flush=True)


def main():
    db = NBADatabase()
    ingestor = NBADataIngestor(db=db)

    print("=" * 60)
    print("NBA Stats DB - Full Historical Dataset Downloader")
    print("Ingesting all 79 seasons in reverse chronological order (2024-25 -> 1946-47)...")
    print("=" * 60)

    start_time = time.time()
    results = ingestor.ingest_all_history(
        start_year=2024,
        end_year=1946,
        skip_existing=True,
        on_progress=progress_callback,
    )

    elapsed_min = round((time.time() - start_time) / 60, 2)
    counts = db.get_table_counts()

    print("\n" + "=" * 60)
    print(f"Historical Download Finished in {elapsed_min} minutes!")
    print("=" * 60)
    print("Final Database Table Summary:")
    for tbl, cnt in counts.items():
        print(f"  {tbl:22s}: {cnt:,} rows")
    print("=" * 60)


if __name__ == "__main__":
    main()
