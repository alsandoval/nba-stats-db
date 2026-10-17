"""
validate_data.py - Standalone data validator runner for NBA Stats DB.
Executes relational, statistical, and endpoint integrity checks and renders a detailed report.
"""

import sys
import time
from tabulate import tabulate

# Ensure UTF-8 console output for Windows
if sys.stdout.encoding != "utf-8" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from nba_stats_db.database import NBADatabase
from nba_stats_db.validator import NBADataValidator


def main():
    print("=" * 80)
    print(" 🏀 NBA Stats Database - Comprehensive Data Integrity Validator")
    print("=" * 80)

    db = NBADatabase()
    validator = NBADataValidator(db=db)

    print("Running 5 comprehensive validation suites...")
    start_time = time.time()
    results = validator.run_all_validations()
    elapsed = round(time.time() - start_time, 2)

    passed = sum(1 for r in results if r.status == "PASS")
    warnings = sum(1 for r in results if r.status == "WARN")
    failed = sum(1 for r in results if r.status == "FAIL")
    total = len(results)

    # Group and display results
    current_cat = None
    table_rows = []

    for r in results:
        status_str = "✓ PASS" if r.status == "PASS" else "⚠ WARN" if r.status == "WARN" else "✗ FAIL"
        table_rows.append([
            r.category.split(". ")[-1] if ". " in r.category else r.category,
            r.name,
            status_str,
            r.message,
        ])

    headers = ["Category", "Validation Check", "Status", "Details"]
    print(tabulate(table_rows, headers=headers, tablefmt="fancy_grid"))

    print("\n" + "=" * 80)
    print(f" Validation Completed in {elapsed}s | Total Checks: {total}")
    print(f" ✓ Passed: {passed:2d} | ⚠ Warnings: {warnings:2d} | ✗ Failed: {failed:2d}")
    print("=" * 80)

    # Database Summary Table
    counts = db.get_table_counts()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name LIKE 'ep_%'")
    ep_tables = cur.fetchone()[0]

    summary_rows = [
        ["Total Franchises / Teams", f"{counts.get('teams', 0):,}"],
        ["Total Players Registered", f"{counts.get('players', 0):,}"],
        ["Total Career Profiles", f"{counts.get('player_profiles', 0):,}"],
        ["Total Games Recorded", f"{counts.get('games', 0):,}"],
        ["Player Boxscore Lines", f"{counts.get('player_game_logs', 0):,}"],
        ["Team Game Logs", f"{counts.get('team_game_logs', 0):,}"],
        ["Player Season Stats", f"{counts.get('player_season_stats', 0):,}"],
        ["Team Season Stats", f"{counts.get('team_season_stats', 0):,}"],
        ["Player Advanced Stats", f"{counts.get('player_advanced_stats', 0):,}"],
        ["Team Advanced Stats", f"{counts.get('team_advanced_stats', 0):,}"],
        ["Dynamic Endpoint Tables (ep_*)", f"{ep_tables:,}"],
    ]
    print("\n📊 Database Inventory Summary:")
    print(tabulate(summary_rows, headers=["Entity / Dataset", "Record Count"], tablefmt="psql"))
    print()

    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
