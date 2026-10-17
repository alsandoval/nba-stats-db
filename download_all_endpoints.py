"""
download_all_endpoints.py - Standalone runner to download ALL 138 nba_api endpoints.
Includes live console progress tracking and comprehensive SQLite/JSON storage.
"""

import sys
import time
import argparse
import logging

# Ensure UTF-8 console output
if sys.stdout.encoding != "utf-8" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from nba_stats_db.database import NBADatabase
from nba_stats_db.endpoints_catalog import get_all_endpoints_catalog
from nba_stats_db.endpoints_downloader import NBAEndpointDownloader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("download_all_endpoints")


def render_bar(percent: float, width: int = 30) -> str:
    filled = int(width * (percent / 100))
    return "█" * filled + "░" * (width - filled)


def main():
    parser = argparse.ArgumentParser(description="Download all 138 NBA API endpoints into SQLite and JSON archive.")
    parser.add_argument("--category", type=str, help="Filter by endpoint category (e.g. 'League & Standings', 'Draft & Combine', 'Live Feeds')")
    parser.add_argument("--endpoint", type=str, help="Download a specific endpoint by name (e.g. 'CommonPlayerInfo')")
    parser.add_argument("--force", action="store_true", help="Force re-download even if already downloaded")
    parser.add_argument("--delay", type=float, default=0.75, help="Polite delay in seconds between requests (default: 0.75s)")
    parser.add_argument("--list", action="store_true", help="List all 138 endpoints and their current database status")

    args = parser.parse_args()
    db = NBADatabase()
    downloader = NBAEndpointDownloader(db=db)

    if args.list:
        catalog = db.get_endpoints_catalog(category=args.category)
        print("=" * 85)
        print(f"{'Endpoint Name':34s} {'Category':24s} {'Status':12s} {'Rows':8s}")
        print("=" * 85)
        for ep in catalog:
            st = ep.get("status", "PENDING")
            rows = ep.get("total_rows", 0)
            print(f"{ep['endpoint_name']:34s} {ep['category']:24s} {st:12s} {rows:<8d}")
        print("=" * 85)
        print(f"Total: {len(catalog)} endpoints listed.")
        return

    if args.endpoint:
        print(f"Downloading single endpoint: {args.endpoint} (force={args.force})...")
        res = downloader.download_endpoint(args.endpoint, force=args.force)
        print("\nResult:")
        print(f"  Status: {res['status']}")
        print(f"  Total Rows: {res['total_rows']}")
        print(f"  Result Sets / Tables: {res['result_sets_count']}")
        if res.get("table_names"):
            print("  Tables Created:")
            for t in res["table_names"]:
                print(f"    - {t}")
        if res.get("error_message"):
            print(f"  Message/Error: {res['error_message']}")
        return

    # Batch download
    cats = [args.category] if args.category else None
    catalog = downloader.catalog
    if cats:
        targets = [name for name, m in catalog.items() if m["category"] in cats]
    else:
        targets = list(catalog.keys())

    total = len(targets)
    print("=" * 75)
    print(" 🏀 NBA Stats DB - All Endpoints Ingestion Pipeline")
    print(f" Target Endpoints : {total}")
    if args.category:
        print(f" Category Filter  : {args.category}")
    print(f" Polite Delay     : {args.delay}s per request")
    print(f" Force Overwrite  : {args.force}")
    print("=" * 75)

    start_time = time.time()
    succeeded = 0
    empty = 0
    deprecated = 0
    errors = 0
    skipped = 0
    total_new_rows = 0

    def on_progress(idx, tot, name, res):
        nonlocal succeeded, empty, deprecated, errors, skipped, total_new_rows
        st = res.get("status", "UNKNOWN")
        rows = res.get("total_rows", 0)
        total_new_rows += rows
        pct = (idx / tot) * 100
        bar = render_bar(pct)

        status_tag = st
        if st == "SUCCESS":
            succeeded += 1
            status_tag = f"✓ SUCCESS (+{rows} rows)"
        elif st == "EMPTY":
            empty += 1
            status_tag = "○ EMPTY"
        elif st == "SKIPPED":
            skipped += 1
            status_tag = "↷ SKIPPED"
        elif st == "DEPRECATED":
            deprecated += 1
            status_tag = "✗ DEPRECATED/404"
        else:
            errors += 1
            status_tag = "⚠ ERROR"

        print(f"[{bar}] {pct:5.1f}% | [{idx:3d}/{tot:3d}] {name:32s} | {status_tag}", flush=True)

    summary = downloader.download_all_endpoints(
        categories=cats,
        force=args.force,
        delay=args.delay,
        on_progress=on_progress,
    )

    elapsed_min = round((time.time() - start_time) / 60, 2)
    print("\n" + "=" * 75)
    print(f" 🎉 Ingestion Completed in {elapsed_min} minutes!")
    print("=" * 75)
    print(f"  Total Processed : {total}")
    print(f"  ✓ Succeeded     : {summary['succeeded']}")
    print(f"  ○ Empty Dataset : {summary['empty']}")
    print(f"  ↷ Skipped       : {summary['skipped']}")
    print(f"  ✗ Deprecated    : {summary['deprecated']}")
    print(f"  ⚠ Errors        : {summary['error']}")
    print(f"  📈 Rows Ingested: {total_new_rows:,}")
    print("=" * 75)


if __name__ == "__main__":
    main()
