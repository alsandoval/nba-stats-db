"""
live_scheduler.py - Schedule-aware adaptive real-time live score polling daemon.
Adjusts polling intervals dynamically based on whether games are Live, Upcoming, or Final.
"""

import time
import threading
import logging
from typing import Any, Callable, Dict, Optional

from .live_scores import NBALiveService
from .database import NBADatabase

logger = logging.getLogger(__name__)


class NBALiveScheduler:
    """
    Intelligent background scheduler that polls the NBA live mediaops feed
    with cadence adapted to current game status:
    - Live Games (status 2): every 15-30 seconds
    - Upcoming Games within 2 hours (status 1): every 2 minutes
    - Off-hours / Final games (status 3 / 0 games): every 15-30 minutes
    """

    def __init__(
        self,
        db: Optional[NBADatabase] = None,
        live_interval: int = 20,
        upcoming_interval: int = 120,
        idle_interval: int = 900,
        on_update: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.db = db or NBADatabase()
        self.live_service = NBALiveService(db=self.db)
        self.live_interval = live_interval
        self.upcoming_interval = upcoming_interval
        self.idle_interval = idle_interval
        self.on_update = on_update

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_running = False

        self.last_poll_time: Optional[float] = None
        self.last_poll_iso: Optional[str] = None
        self.current_interval: int = idle_interval
        self.total_polls: int = 0
        self.live_games_count: int = 0
        self.total_games_today: int = 0
        self.last_error: Optional[str] = None

    def start(self) -> None:
        """Starts the background polling worker thread."""
        if self._is_running:
            logger.info("Live scheduler is already running.")
            return

        self._stop_event.clear()
        self._is_running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        logger.info("Started NBALiveScheduler background daemon.")

    def stop(self) -> None:
        """Stops the background polling worker thread."""
        if not self._is_running:
            return

        self._stop_event.set()
        self._is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        logger.info("Stopped NBALiveScheduler background daemon.")

    def poll_once(self) -> Dict[str, Any]:
        """Executes a single live update poll immediately and returns summary."""
        import datetime
        try:
            raw_data = self.live_service.fetch_todays_scoreboard()
            saved = self.live_service.save_live_scoreboard(raw_data)

            self.last_poll_time = time.time()
            self.last_poll_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            self.total_polls += 1
            self.total_games_today = len(saved)
            self.live_games_count = sum(1 for g in saved if g.get("game_status") == 2)
            self.last_error = None

            # Calculate next adaptive interval
            self.current_interval = self._calculate_next_interval(saved)

            summary = {
                "poll_time": self.last_poll_iso,
                "total_games": self.total_games_today,
                "live_games": self.live_games_count,
                "next_interval_sec": self.current_interval,
                "games": saved,
            }

            if self.on_update:
                self.on_update(summary)

            return summary

        except Exception as e:
            self.last_error = str(e)
            logger.error("Live poll failed: %s", e)
            return {
                "error": str(e),
                "poll_time": self.last_poll_iso,
                "total_games": self.total_games_today,
                "live_games": self.live_games_count,
                "next_interval_sec": self.idle_interval,
            }

    def _calculate_next_interval(self, games: list) -> int:
        """Determines the optimal sleep time based on game statuses."""
        if not games:
            return self.idle_interval

        statuses = [g.get("game_status", 1) for g in games]

        # If any game is actively being played (Status 2) -> Fast live cadence
        if 2 in statuses:
            return self.live_interval

        # If games are upcoming (Status 1) -> Upcoming cadence
        if 1 in statuses:
            return self.upcoming_interval

        # If all games are completed (Status 3) -> Idle cadence
        return self.idle_interval

    def _worker_loop(self) -> None:
        """Continuous execution loop with interruptible sleep."""
        logger.info("Live scheduler worker loop initiated.")
        while not self._stop_event.is_set():
            res = self.poll_once()
            interval = res.get("next_interval_sec", self.idle_interval)

            # Interruptible sleep in small steps
            for _ in range(int(interval * 2)):
                if self._stop_event.is_set():
                    break
                time.sleep(0.5)

        logger.info("Live scheduler worker loop terminated.")

    def get_status(self) -> Dict[str, Any]:
        """Returns the current operating metrics of the scheduler."""
        return {
            "is_running": self._is_running,
            "last_poll_time": self.last_poll_iso,
            "current_interval_seconds": self.current_interval,
            "live_games_count": self.live_games_count,
            "total_games_today": self.total_games_today,
            "total_polls": self.total_polls,
            "last_error": self.last_error,
        }
