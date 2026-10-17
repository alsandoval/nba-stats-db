"""
track_progress.py - Terminal visual progress bar and tracker for NBA Stats DB download.
"""

import sys
import time
import urllib.request
import json

# Ensure UTF-8 console output
if sys.stdout.encoding != "utf-8" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def render_progress_bar(percent, width=35):
    filled = int(width * (percent / 100))
    bar = "█" * filled + "░" * (width - filled)
    return bar


def main():
    print("\033[2J\033[H", end="")  # Clear terminal
    print("=" * 65)
    print(" 🏀 NBA Stats DB - Live Historical Ingestion Tracker")
    print("=" * 65)

    while True:
        try:
            req = urllib.request.Request("http://127.0.0.1:5000/api/sync-progress")
            with urllib.request.urlopen(req, timeout=3) as res:
                data = json.loads(res.read().decode("utf-8"))

            percent = data.get("percent", 0.0)
            completed = data.get("completed_count", 0)
            total = data.get("total_seasons", 79)
            current = data.get("current_season", "-")
            boxscores = data.get("total_boxscores", 0)
            games = data.get("total_games", 0)
            dbsize = data.get("db_size_mb", 0.0)
            is_done = data.get("is_complete", False)

            bar = render_progress_bar(percent)

            status_line = (
                f"\r[{bar}] {percent:5.1f}% | "
                f"{completed}/{total} Seasons | "
                f"Now: {current:7s} | "
                f"Games: {games:,} | "
                f"Boxscores: {boxscores:,} | "
                f"DB: {dbsize} MB"
            )
            sys.stdout.write(status_line)
            sys.stdout.flush()

            if is_done:
                print("\n\n" + "=" * 65)
                print(" 🎉 Complete! All 79 historical seasons downloaded (1946-2025).")
                print("=" * 65)
                break

        except Exception:
            pass

        time.sleep(2)


if __name__ == "__main__":
    main()
