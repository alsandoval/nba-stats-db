"""
live_scores.py - Real-time NBA live scores, box scores, and play-by-play service.
Fetches official live mediaops CDN streams with TLS browser impersonation.
"""

import json
import logging
import datetime
from typing import Any, Dict, List, Optional
from curl_cffi import requests as cr

from .database import NBADatabase
from .client import get_impersonated_session

logger = logging.getLogger(__name__)

CDN_BASE_URL = "https://cdn.nba.com/static/json/liveData"
LIVE_HEADERS = {
    "Origin": "https://www.nba.com",
    "Referer": "https://www.nba.com/",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


class NBALiveService:
    """Handles real-time live score fetching, parsing, and database persistence."""

    def __init__(self, db: Optional[NBADatabase] = None):
        self.db = db or NBADatabase()
        self.db.init_database()
        self.session = get_impersonated_session()

    def fetch_todays_scoreboard(self) -> Dict[str, Any]:
        """
        Fetches today's live scoreboard directly from the official NBA CDN.
        Returns the parsed dictionary.
        """
        url = f"{CDN_BASE_URL}/scoreboard/todaysScoreboard_00.json"
        try:
            res = self.session.get(url, headers=LIVE_HEADERS, timeout=15)
            if res.status_code == 200 and res.text.strip():
                return res.json()
            else:
                logger.warning("Scoreboard returned status %d", res.status_code)
                return {"scoreboard": {"gameDate": "", "games": []}}
        except Exception as e:
            logger.error("Failed to fetch live scoreboard: %s", e)
            return {"scoreboard": {"gameDate": "", "games": []}}

    def fetch_game_boxscore(self, game_id: str) -> Dict[str, Any]:
        """Fetches live detailed box score for a specific game."""
        url = f"{CDN_BASE_URL}/boxscore/boxscore_{game_id}.json"
        try:
            res = self.session.get(url, headers=LIVE_HEADERS, timeout=15)
            if res.status_code == 200:
                return res.json()
            return {"error": f"Game {game_id} returned HTTP {res.status_code}"}
        except Exception as e:
            logger.error("Failed to fetch live boxscore for %s: %s", game_id, e)
            return {"error": str(e)}

    def fetch_game_playbyplay(self, game_id: str) -> Dict[str, Any]:
        """Fetches live play-by-play actions for a specific game."""
        url = f"{CDN_BASE_URL}/playbyplay/playbyplay_{game_id}.json"
        try:
            res = self.session.get(url, headers=LIVE_HEADERS, timeout=15)
            if res.status_code == 200:
                return res.json()
            return {"error": f"Game {game_id} returned HTTP {res.status_code}"}
        except Exception as e:
            logger.error("Failed to fetch live play-by-play for %s: %s", game_id, e)
            return {"error": str(e)}

    def save_live_scoreboard(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parses live games from the scoreboard response and saves/updates
        records in the `live_scoreboard` SQLite table.
        """
        sb = data.get("scoreboard", {})
        games = sb.get("games", [])
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        saved_rows: List[Dict[str, Any]] = []

        for g in games:
            gid = str(g.get("gameId"))
            home = g.get("homeTeam", {})
            away = g.get("awayTeam", {})
            status = int(g.get("gameStatus", 1))

            row = {
                "game_id": gid,
                "game_code": str(g.get("gameCode", "")),
                "game_status": status,
                "game_status_text": str(g.get("gameStatusText", "")),
                "period": int(g.get("period", 0)),
                "game_clock": str(g.get("gameClock", "")),
                "home_team_id": int(home.get("teamId", 0)),
                "home_team_name": str(home.get("teamName", "")),
                "home_team_tricode": str(home.get("teamTricode", "")),
                "home_team_score": int(home.get("score", 0)),
                "away_team_id": int(away.get("teamId", 0)),
                "away_team_name": str(away.get("teamName", "")),
                "away_team_tricode": str(away.get("teamTricode", "")),
                "away_team_score": int(away.get("score", 0)),
                "game_leaders_json": json.dumps(g.get("gameLeaders", {})),
                "raw_game_json": json.dumps(g),
                "updated_at": now,
            }
            saved_rows.append(row)

            # If game is Final (status == 3), ensure the permanent games table is updated
            if status == 3:
                self._archive_final_game(g, now)

        if saved_rows:
            self.db.upsert_rows("live_scoreboard", saved_rows, conflict_keys=["game_id"])
            logger.info("Updated %d live games in database.", len(saved_rows))

        return saved_rows

    def _archive_final_game(self, game: Dict[str, Any], timestamp: str) -> None:
        """Helper to archive a finished live game into games table."""
        try:
            gid = str(game.get("gameId"))
            home = game.get("homeTeam", {})
            away = game.get("awayTeam", {})
            h_score = int(home.get("score", 0))
            a_score = int(away.get("score", 0))
            h_id = int(home.get("teamId", 0))
            a_id = int(away.get("teamId", 0))
            winner = h_id if h_score > a_score else a_id

            # Ensure teams exist in teams table to prevent foreign key violation
            for t_info in (home, away):
                t_id = int(t_info.get("teamId", 0))
                if t_id > 0:
                    team_name = t_info.get("teamName") or t_info.get("teamCity") or f"Team {t_id}"
                    tricode = t_info.get("teamTricode") or str(t_id)
                    self.db.upsert_rows(
                        "teams",
                        [{
                            "team_id": t_id,
                            "full_name": team_name,
                            "abbreviation": tricode,
                            "nickname": t_info.get("teamName", ""),
                            "city": t_info.get("teamCity", ""),
                        }],
                        conflict_keys=["team_id"],
                    )

            game_row = {
                "game_id": gid,
                "season_id": "2023-24",
                "season_type": "Regular Season",
                "game_date": str(game.get("gameEt", timestamp[:10])),
                "matchup": f"{away.get('teamTricode')} @ {home.get('teamTricode')}",
                "home_team_id": h_id,
                "visitor_team_id": a_id,
                "home_team_pts": h_score,
                "visitor_team_pts": a_score,
                "winner_team_id": winner,
            }
            self.db.upsert_rows("games", [game_row], conflict_keys=["game_id"])
        except Exception as e:
            logger.debug("Failed archiving final game: %s", e)

    def get_cached_scoreboard(self) -> Dict[str, Any]:
        """Returns live scores from SQLite database."""
        df = self.db.query_df("""
            SELECT * FROM live_scoreboard 
            ORDER BY 
              CASE 
                WHEN game_status = 2 THEN 1 -- Live first
                WHEN game_status = 1 THEN 2 -- Upcoming second
                ELSE 3                     -- Final last
              END,
              game_id;
        """)

        games = []
        for _, r in df.iterrows():
            g_dict = {
                "game_id": r["game_id"],
                "game_code": r["game_code"],
                "game_status": r["game_status"],
                "game_status_text": r["game_status_text"],
                "period": r["period"],
                "game_clock": r["game_clock"],
                "home_team": {
                    "team_id": r["home_team_id"],
                    "team_name": r["home_team_name"],
                    "tricode": r["home_team_tricode"],
                    "score": r["home_team_score"],
                },
                "away_team": {
                    "team_id": r["away_team_id"],
                    "team_name": r["away_team_name"],
                    "tricode": r["away_team_tricode"],
                    "score": r["away_team_score"],
                },
                "updated_at": r["updated_at"],
            }
            if r.get("game_leaders_json"):
                try:
                    g_dict["game_leaders"] = json.loads(r["game_leaders_json"])
                except Exception:
                    g_dict["game_leaders"] = {}
            if r.get("raw_game_json"):
                try:
                    g_dict["raw"] = json.loads(r["raw_game_json"])
                except Exception:
                    g_dict["raw"] = {}
            games.append(g_dict)

        live_count = sum(1 for g in games if g["game_status"] == 2)
        return {
            "total_games": len(games),
            "live_games_count": live_count,
            "games": games,
        }
