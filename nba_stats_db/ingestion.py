"""
ingestion.py - Ingestion pipelines to fetch and store NBA data using nba_api and SQLite.
"""

import logging
from typing import Any, Dict, List, Optional
import pandas as pd

from nba_api.stats.static import teams as static_teams
from nba_api.stats.static import players as static_players
from nba_api.stats.endpoints import (
    LeagueStandings,
    LeagueDashPlayerStats,
    LeagueDashTeamStats,
    LeagueGameLog,
    CommonAllPlayers,
)

from .client import configure_nba_api_client, call_with_retry
from .database import NBADatabase

logger = logging.getLogger(__name__)


class NBADataIngestor:
    """Orchestrates data fetching from nba_api and storage into NBADatabase."""

    def __init__(
        self,
        db: Optional[NBADatabase] = None,
        impersonate: str = "chrome120",
    ):
        self.db = db or NBADatabase()
        self.db.init_database()
        configure_nba_api_client(impersonate=impersonate)

    def ingest_teams(self) -> int:
        """Fetches all NBA franchises from static metadata and stores in DB."""
        logger.info("Ingesting NBA teams...")
        teams_data = static_teams.get_teams()
        rows = [
            {
                "team_id": t["id"],
                "full_name": t["full_name"],
                "abbreviation": t["abbreviation"],
                "nickname": t["nickname"],
                "city": t["city"],
                "state": t["state"],
                "year_founded": t["year_founded"],
            }
            for t in teams_data
        ]
        count = self.db.upsert_rows("teams", rows, conflict_keys=["team_id"])
        logger.info("Ingested %d teams.", len(rows))
        return len(rows)

    def ingest_players(self) -> int:
        """Fetches all NBA players from static metadata and stores in DB."""
        logger.info("Ingesting NBA players from static dataset...")
        players_data = static_players.get_players()
        rows = [
            {
                "player_id": p["id"],
                "full_name": p["full_name"],
                "first_name": p.get("first_name"),
                "last_name": p.get("last_name"),
                "is_active": 1 if p.get("is_active") else 0,
            }
            for p in players_data
        ]
        # Batch insert to stay within SQLite limits
        batch_size = 1000
        total = len(rows)
        for i in range(0, total, batch_size):
            batch = rows[i : i + batch_size]
            self.db.upsert_rows("players", batch, conflict_keys=["player_id"])

        logger.info("Ingested %d players.", total)
        return total

    def ingest_standings(
        self,
        season: str = "2023-24",
        season_type: str = "Regular Season",
    ) -> int:
        """Fetches league standings for a season and stores in DB."""
        logger.info("Ingesting standings for season %s (%s)...", season, season_type)

        def fetch():
            endpoint = LeagueStandings(
                season=season,
                season_type=season_type,
                timeout=30,
            )
            return endpoint.get_data_frames()[0]

        df = call_with_retry(fetch)
        if df.empty:
            logger.warning("No standings data returned for season %s", season)
            return 0

        rows = []
        for _, r in df.iterrows():
            rows.append(
                {
                    "team_id": int(r["TeamID"]),
                    "season": season,
                    "season_type": season_type,
                    "conference": str(r.get("Conference", "")),
                    "division": str(r.get("Division", "")),
                    "w": int(r.get("WINS", 0)),
                    "l": int(r.get("LOSSES", 0)),
                    "win_pct": float(r.get("WinPCT", 0.0)),
                    "conf_rank": int(r.get("PlayoffRank", 0)),
                    "div_rank": int(r.get("DivisionRank", 0)),
                    "home_record": str(r.get("HOME", "")),
                    "road_record": str(r.get("ROAD", "")),
                    "l10": str(r.get("L10", "")),
                    "strk": str(r.get("CurrentStreak", "")),
                    "pts": float(r.get("PointsPG", 0.0)),
                    "opp_pts": float(r.get("OppPointsPG", 0.0)),
                    "diff": float(r.get("DiffPointsPG", 0.0)),
                }
            )

        self.db.upsert_rows(
            "team_season_stats",
            rows,
            conflict_keys=["team_id", "season", "season_type"],
        )
        logger.info("Ingested %d team standings records.", len(rows))
        return len(rows)

    def ingest_player_season_stats(
        self,
        season: str = "2023-24",
        season_type: str = "Regular Season",
        per_mode: str = "PerGame",
    ) -> int:
        """Fetches league-wide player statistics for a season and stores in DB."""
        logger.info(
            "Ingesting player season stats for season %s (%s, %s)...",
            season,
            season_type,
            per_mode,
        )

        def fetch():
            endpoint = LeagueDashPlayerStats(
                season=season,
                season_type_all_star=season_type,
                per_mode_detailed=per_mode,
                timeout=30,
            )
            return endpoint.get_data_frames()[0]

        df = call_with_retry(fetch)
        if df.empty:
            logger.warning("No player stats returned for season %s", season)
            return 0

        # Ensure any players in stats exist in the players table
        missing_players = []
        for _, r in df.iterrows():
            missing_players.append(
                {
                    "player_id": int(r["PLAYER_ID"]),
                    "full_name": str(r["PLAYER_NAME"]),
                    "first_name": "",
                    "last_name": "",
                    "is_active": 1,
                }
            )
        self.db.upsert_rows("players", missing_players, conflict_keys=["player_id"])

        rows = []
        for _, r in df.iterrows():
            rows.append(
                {
                    "player_id": int(r["PLAYER_ID"]),
                    "season": season,
                    "season_type": season_type,
                    "team_id": int(r["TEAM_ID"]) if r.get("TEAM_ID") else None,
                    "team_abbreviation": str(r.get("TEAM_ABBREVIATION", "")),
                    "age": float(r.get("AGE", 0.0)) if pd.notnull(r.get("AGE")) else None,
                    "gp": int(r.get("GP", 0)),
                    "w": int(r.get("W", 0)),
                    "l": int(r.get("L", 0)),
                    "min": float(r.get("MIN", 0.0)) if pd.notnull(r.get("MIN")) else 0.0,
                    "fgm": float(r.get("FGM", 0.0)) if pd.notnull(r.get("FGM")) else 0.0,
                    "fga": float(r.get("FGA", 0.0)) if pd.notnull(r.get("FGA")) else 0.0,
                    "fg_pct": float(r.get("FG_PCT", 0.0)) if pd.notnull(r.get("FG_PCT")) else 0.0,
                    "fg3m": float(r.get("FG3M", 0.0)) if pd.notnull(r.get("FG3M")) else 0.0,
                    "fg3a": float(r.get("FG3A", 0.0)) if pd.notnull(r.get("FG3A")) else 0.0,
                    "fg3_pct": float(r.get("FG3_PCT", 0.0)) if pd.notnull(r.get("FG3_PCT")) else 0.0,
                    "ftm": float(r.get("FTM", 0.0)) if pd.notnull(r.get("FTM")) else 0.0,
                    "fta": float(r.get("FTA", 0.0)) if pd.notnull(r.get("FTA")) else 0.0,
                    "ft_pct": float(r.get("FT_PCT", 0.0)) if pd.notnull(r.get("FT_PCT")) else 0.0,
                    "oreb": float(r.get("OREB", 0.0)) if pd.notnull(r.get("OREB")) else 0.0,
                    "dreb": float(r.get("DREB", 0.0)) if pd.notnull(r.get("DREB")) else 0.0,
                    "reb": float(r.get("REB", 0.0)) if pd.notnull(r.get("REB")) else 0.0,
                    "ast": float(r.get("AST", 0.0)) if pd.notnull(r.get("AST")) else 0.0,
                    "tov": float(r.get("TOV", 0.0)) if pd.notnull(r.get("TOV")) else 0.0,
                    "stl": float(r.get("STL", 0.0)) if pd.notnull(r.get("STL")) else 0.0,
                    "blk": float(r.get("BLK", 0.0)) if pd.notnull(r.get("BLK")) else 0.0,
                    "pf": float(r.get("PF", 0.0)) if pd.notnull(r.get("PF")) else 0.0,
                    "pts": float(r.get("PTS", 0.0)) if pd.notnull(r.get("PTS")) else 0.0,
                    "plus_minus": float(r.get("PLUS_MINUS", 0.0)) if pd.notnull(r.get("PLUS_MINUS")) else 0.0,
                }
            )

        batch_size = 500
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            self.db.upsert_rows(
                "player_season_stats",
                batch,
                conflict_keys=["player_id", "season", "season_type"],
            )

        logger.info("Ingested %d player season stats records.", len(rows))
        return len(rows)

    def ingest_games_and_game_logs(
        self,
        season: str = "2023-24",
        season_type: str = "Regular Season",
    ) -> Dict[str, int]:
        """
        Fetches full season schedule, games, team game logs, and player game logs.
        """
        logger.info("Ingesting team game logs for season %s (%s)...", season, season_type)

        def fetch_team_logs():
            endpoint = LeagueGameLog(
                season=season,
                season_type_all_star=season_type,
                player_or_team_abbreviation="T",
                timeout=45,
            )
            return endpoint.get_data_frames()[0]

        team_df = call_with_retry(fetch_team_logs)
        if team_df.empty:
            logger.warning("No team game logs returned for season %s", season)
            return {"games": 0, "team_game_logs": 0, "player_game_logs": 0}

        # Auto-upsert any historical franchises in game logs into teams table
        teams_cache = []
        for _, r in team_df[["TEAM_ID", "TEAM_NAME", "TEAM_ABBREVIATION"]].drop_duplicates().iterrows():
            t_name = str(r["TEAM_NAME"])
            teams_cache.append({
                "team_id": int(r["TEAM_ID"]),
                "full_name": t_name,
                "abbreviation": str(r["TEAM_ABBREVIATION"]),
                "nickname": t_name.split()[-1] if t_name else "",
                "city": " ".join(t_name.split()[:-1]) if t_name else "",
                "state": "",
                "year_founded": None
            })
        self.db.upsert_rows("teams", teams_cache, conflict_keys=["team_id"])

        # 1. Parse and populate games table from team_df
        # Each game has 2 records: home (with 'vs.') and away (with '@')
        games_dict: Dict[str, Dict[str, Any]] = {}
        for _, r in team_df.iterrows():
            gid = str(r["GAME_ID"])
            matchup = str(r["MATCHUP"])
            tid = int(r["TEAM_ID"])
            pts = int(r["PTS"]) if pd.notnull(r.get("PTS")) else None
            wl = str(r.get("WL", ""))

            if gid not in games_dict:
                games_dict[gid] = {
                    "game_id": gid,
                    "season_id": str(r.get("SEASON_ID", "")),
                    "season_type": season_type,
                    "game_date": str(r.get("GAME_DATE", "")),
                    "matchup": matchup,
                    "home_team_id": None,
                    "visitor_team_id": None,
                    "home_team_pts": None,
                    "visitor_team_pts": None,
                    "winner_team_id": None,
                }

            if "vs." in matchup:
                games_dict[gid]["home_team_id"] = tid
                games_dict[gid]["home_team_pts"] = pts
                games_dict[gid]["matchup"] = matchup
            elif "@" in matchup:
                games_dict[gid]["visitor_team_id"] = tid
                games_dict[gid]["visitor_team_pts"] = pts

            if wl == "W":
                games_dict[gid]["winner_team_id"] = tid

        game_rows = list(games_dict.values())
        batch_size = 500
        for i in range(0, len(game_rows), batch_size):
            batch = game_rows[i : i + batch_size]
            self.db.upsert_rows("games", batch, conflict_keys=["game_id"])
        logger.info("Ingested %d unique games.", len(game_rows))

        # 2. Populate team_game_logs
        tgl_rows = []
        for _, r in team_df.iterrows():
            tgl_rows.append(
                {
                    "team_id": int(r["TEAM_ID"]),
                    "game_id": str(r["GAME_ID"]),
                    "game_date": str(r.get("GAME_DATE", "")),
                    "matchup": str(r.get("MATCHUP", "")),
                    "wl": str(r.get("WL", "")),
                    "min": float(r.get("MIN", 0.0)) if pd.notnull(r.get("MIN")) else 0.0,
                    "fgm": float(r.get("FGM", 0.0)) if pd.notnull(r.get("FGM")) else 0.0,
                    "fga": float(r.get("FGA", 0.0)) if pd.notnull(r.get("FGA")) else 0.0,
                    "fg_pct": float(r.get("FG_PCT", 0.0)) if pd.notnull(r.get("FG_PCT")) else 0.0,
                    "fg3m": float(r.get("FG3M", 0.0)) if pd.notnull(r.get("FG3M")) else 0.0,
                    "fg3a": float(r.get("FG3A", 0.0)) if pd.notnull(r.get("FG3A")) else 0.0,
                    "fg3_pct": float(r.get("FG3_PCT", 0.0)) if pd.notnull(r.get("FG3_PCT")) else 0.0,
                    "ftm": float(r.get("FTM", 0.0)) if pd.notnull(r.get("FTM")) else 0.0,
                    "fta": float(r.get("FTA", 0.0)) if pd.notnull(r.get("FTA")) else 0.0,
                    "ft_pct": float(r.get("FT_PCT", 0.0)) if pd.notnull(r.get("FT_PCT")) else 0.0,
                    "oreb": float(r.get("OREB", 0.0)) if pd.notnull(r.get("OREB")) else 0.0,
                    "dreb": float(r.get("DREB", 0.0)) if pd.notnull(r.get("DREB")) else 0.0,
                    "reb": float(r.get("REB", 0.0)) if pd.notnull(r.get("REB")) else 0.0,
                    "ast": float(r.get("AST", 0.0)) if pd.notnull(r.get("AST")) else 0.0,
                    "stl": float(r.get("STL", 0.0)) if pd.notnull(r.get("STL")) else 0.0,
                    "blk": float(r.get("BLK", 0.0)) if pd.notnull(r.get("BLK")) else 0.0,
                    "tov": float(r.get("TOV", 0.0)) if pd.notnull(r.get("TOV")) else 0.0,
                    "pf": float(r.get("PF", 0.0)) if pd.notnull(r.get("PF")) else 0.0,
                    "pts": float(r.get("PTS", 0.0)) if pd.notnull(r.get("PTS")) else 0.0,
                    "plus_minus": float(r.get("PLUS_MINUS", 0.0)) if pd.notnull(r.get("PLUS_MINUS")) else 0.0,
                    "video_available": int(r.get("VIDEO_AVAILABLE", 0)),
                }
            )

        for i in range(0, len(tgl_rows), batch_size):
            batch = tgl_rows[i : i + batch_size]
            self.db.upsert_rows("team_game_logs", batch, conflict_keys=["team_id", "game_id"])
        logger.info("Ingested %d team game logs.", len(tgl_rows))

        # 3. Populate player_game_logs
        logger.info("Ingesting player game logs for season %s (%s)...", season, season_type)

        def fetch_player_logs():
            endpoint = LeagueGameLog(
                season=season,
                season_type_all_star=season_type,
                player_or_team_abbreviation="P",
                timeout=60,
            )
            return endpoint.get_data_frames()[0]

        player_df = call_with_retry(fetch_player_logs)
        if player_df.empty:
            logger.warning("No player game logs returned for season %s", season)
            return {
                "games": len(game_rows),
                "team_game_logs": len(tgl_rows),
                "player_game_logs": 0,
            }

        # Ensure all players exist in players table
        player_cache = [
            {
                "player_id": int(r["PLAYER_ID"]),
                "full_name": str(r["PLAYER_NAME"]),
                "first_name": "",
                "last_name": "",
                "is_active": 1,
            }
            for _, r in player_df[["PLAYER_ID", "PLAYER_NAME"]].drop_duplicates().iterrows()
        ]
        self.db.upsert_rows("players", player_cache, conflict_keys=["player_id"])

        pgl_rows = []
        for _, r in player_df.iterrows():
            pgl_rows.append(
                {
                    "game_id": str(r["GAME_ID"]),
                    "player_id": int(r["PLAYER_ID"]),
                    "team_id": int(r["TEAM_ID"]),
                    "game_date": str(r.get("GAME_DATE", "")),
                    "matchup": str(r.get("MATCHUP", "")),
                    "wl": str(r.get("WL", "")),
                    "min": float(r.get("MIN", 0.0)) if pd.notnull(r.get("MIN")) else 0.0,
                    "fgm": float(r.get("FGM", 0.0)) if pd.notnull(r.get("FGM")) else 0.0,
                    "fga": float(r.get("FGA", 0.0)) if pd.notnull(r.get("FGA")) else 0.0,
                    "fg_pct": float(r.get("FG_PCT", 0.0)) if pd.notnull(r.get("FG_PCT")) else 0.0,
                    "fg3m": float(r.get("FG3M", 0.0)) if pd.notnull(r.get("FG3M")) else 0.0,
                    "fg3a": float(r.get("FG3A", 0.0)) if pd.notnull(r.get("FG3A")) else 0.0,
                    "fg3_pct": float(r.get("FG3_PCT", 0.0)) if pd.notnull(r.get("FG3_PCT")) else 0.0,
                    "ftm": float(r.get("FTM", 0.0)) if pd.notnull(r.get("FTM")) else 0.0,
                    "fta": float(r.get("FTA", 0.0)) if pd.notnull(r.get("FTA")) else 0.0,
                    "ft_pct": float(r.get("FT_PCT", 0.0)) if pd.notnull(r.get("FT_PCT")) else 0.0,
                    "oreb": float(r.get("OREB", 0.0)) if pd.notnull(r.get("OREB")) else 0.0,
                    "dreb": float(r.get("DREB", 0.0)) if pd.notnull(r.get("DREB")) else 0.0,
                    "reb": float(r.get("REB", 0.0)) if pd.notnull(r.get("REB")) else 0.0,
                    "ast": float(r.get("AST", 0.0)) if pd.notnull(r.get("AST")) else 0.0,
                    "stl": float(r.get("STL", 0.0)) if pd.notnull(r.get("STL")) else 0.0,
                    "blk": float(r.get("BLK", 0.0)) if pd.notnull(r.get("BLK")) else 0.0,
                    "tov": float(r.get("TOV", 0.0)) if pd.notnull(r.get("TOV")) else 0.0,
                    "pf": float(r.get("PF", 0.0)) if pd.notnull(r.get("PF")) else 0.0,
                    "pts": float(r.get("PTS", 0.0)) if pd.notnull(r.get("PTS")) else 0.0,
                    "plus_minus": float(r.get("PLUS_MINUS", 0.0)) if pd.notnull(r.get("PLUS_MINUS")) else 0.0,
                    "video_available": int(r.get("VIDEO_AVAILABLE", 0)),
                }
            )

        for i in range(0, len(pgl_rows), batch_size):
            batch = pgl_rows[i : i + batch_size]
            self.db.upsert_rows("player_game_logs", batch, conflict_keys=["player_id", "game_id"])
        logger.info("Ingested %d player game logs.", len(pgl_rows))

        return {
            "games": len(game_rows),
            "team_game_logs": len(tgl_rows),
            "player_game_logs": len(pgl_rows),
        }

    def ingest_player_profiles(self) -> int:
        """Fetches all player historical and roster profiles using CommonAllPlayers."""
        logger.info("Ingesting player profiles from CommonAllPlayers...")

        def fetch():
            endpoint = CommonAllPlayers(is_only_current_season=0, timeout=30)
            return endpoint.get_data_frames()[0]

        df = call_with_retry(fetch)
        if df.empty:
            logger.warning("No player profile data returned.")
            return 0

        # Also ensure players table has all these players
        players_base = []
        for _, r in df.iterrows():
            players_base.append(
                {
                    "player_id": int(r["PERSON_ID"]),
                    "full_name": str(r["DISPLAY_FIRST_LAST"]),
                    "first_name": "",
                    "last_name": "",
                    "is_active": 1 if str(r.get("ROSTERSTATUS", "")) == "1" else 0,
                }
            )
        self.db.upsert_rows("players", players_base, conflict_keys=["player_id"])

        rows = []
        for _, r in df.iterrows():
            rows.append(
                {
                    "player_id": int(r["PERSON_ID"]),
                    "display_first_last": str(r.get("DISPLAY_FIRST_LAST", "")),
                    "roster_status": str(r.get("ROSTERSTATUS", "")),
                    "from_year": int(r["FROM_YEAR"]) if pd.notnull(r.get("FROM_YEAR")) else None,
                    "to_year": int(r["TO_YEAR"]) if pd.notnull(r.get("TO_YEAR")) else None,
                    "team_id": int(r["TEAM_ID"]) if pd.notnull(r.get("TEAM_ID")) and int(r["TEAM_ID"]) > 0 else None,
                    "team_city": str(r.get("TEAM_CITY", "")),
                    "team_name": str(r.get("TEAM_NAME", "")),
                    "team_abbreviation": str(r.get("TEAM_ABBREVIATION", "")),
                }
            )

        batch_size = 1000
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            self.db.upsert_rows("player_profiles", batch, conflict_keys=["player_id"])

        logger.info("Ingested %d player profiles.", len(rows))
        return len(rows)

    def ingest_player_advanced_stats(
        self,
        season: str = "2023-24",
        season_type: str = "Regular Season",
    ) -> int:
        """Fetches advanced analytics for players (Off/Def/Net Rating, TS%, USG%, PIE, Pace)."""
        logger.info(
            "Ingesting player advanced stats for season %s (%s)...",
            season,
            season_type,
        )

        def fetch():
            endpoint = LeagueDashPlayerStats(
                season=season,
                season_type_all_star=season_type,
                measure_type_detailed_defense="Advanced",
                timeout=35,
            )
            return endpoint.get_data_frames()[0]

        df = call_with_retry(fetch)
        if df.empty:
            logger.warning("No player advanced stats returned for season %s", season)
            return 0

        rows = []
        for _, r in df.iterrows():
            rows.append(
                {
                    "player_id": int(r["PLAYER_ID"]),
                    "season": season,
                    "season_type": season_type,
                    "team_id": int(r["TEAM_ID"]) if pd.notnull(r.get("TEAM_ID")) else None,
                    "team_abbreviation": str(r.get("TEAM_ABBREVIATION", "")),
                    "age": float(r.get("AGE", 0.0)) if pd.notnull(r.get("AGE")) else None,
                    "gp": int(r.get("GP", 0)),
                    "min": float(r.get("MIN", 0.0)) if pd.notnull(r.get("MIN")) else 0.0,
                    "off_rating": float(r.get("OFF_RATING", 0.0)) if pd.notnull(r.get("OFF_RATING")) else 0.0,
                    "def_rating": float(r.get("DEF_RATING", 0.0)) if pd.notnull(r.get("DEF_RATING")) else 0.0,
                    "net_rating": float(r.get("NET_RATING", 0.0)) if pd.notnull(r.get("NET_RATING")) else 0.0,
                    "ast_pct": float(r.get("AST_PCT", 0.0)) if pd.notnull(r.get("AST_PCT")) else 0.0,
                    "ast_to": float(r.get("AST_TO", 0.0)) if pd.notnull(r.get("AST_TO")) else 0.0,
                    "ast_ratio": float(r.get("AST_RATIO", 0.0)) if pd.notnull(r.get("AST_RATIO")) else 0.0,
                    "oreb_pct": float(r.get("OREB_PCT", 0.0)) if pd.notnull(r.get("OREB_PCT")) else 0.0,
                    "dreb_pct": float(r.get("DREB_PCT", 0.0)) if pd.notnull(r.get("DREB_PCT")) else 0.0,
                    "reb_pct": float(r.get("REB_PCT", 0.0)) if pd.notnull(r.get("REB_PCT")) else 0.0,
                    "tm_tov_pct": float(r.get("TM_TOV_PCT", 0.0)) if pd.notnull(r.get("TM_TOV_PCT")) else 0.0,
                    "efg_pct": float(r.get("EFG_PCT", 0.0)) if pd.notnull(r.get("EFG_PCT")) else 0.0,
                    "ts_pct": float(r.get("TS_PCT", 0.0)) if pd.notnull(r.get("TS_PCT")) else 0.0,
                    "usg_pct": float(r.get("USG_PCT", 0.0)) if pd.notnull(r.get("USG_PCT")) else 0.0,
                    "pace": float(r.get("PACE", 0.0)) if pd.notnull(r.get("PACE")) else 0.0,
                    "pie": float(r.get("PIE", 0.0)) if pd.notnull(r.get("PIE")) else 0.0,
                    "poss": float(r.get("POSS", 0.0)) if pd.notnull(r.get("POSS")) else 0.0,
                }
            )

        batch_size = 500
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            self.db.upsert_rows(
                "player_advanced_stats",
                batch,
                conflict_keys=["player_id", "season", "season_type"],
            )

        logger.info("Ingested %d player advanced stats records.", len(rows))
        return len(rows)

    def ingest_team_advanced_stats(
        self,
        season: str = "2023-24",
        season_type: str = "Regular Season",
    ) -> int:
        """Fetches advanced analytics for teams (Off/Def/Net Rating, Pace, TS%, etc.)."""
        logger.info(
            "Ingesting team advanced stats for season %s (%s)...",
            season,
            season_type,
        )

        def fetch():
            endpoint = LeagueDashTeamStats(
                season=season,
                season_type_all_star=season_type,
                measure_type_detailed_defense="Advanced",
                timeout=30,
            )
            return endpoint.get_data_frames()[0]

        df = call_with_retry(fetch)
        if df.empty:
            logger.warning("No team advanced stats returned for season %s", season)
            return 0

        rows = []
        for _, r in df.iterrows():
            rows.append(
                {
                    "team_id": int(r["TEAM_ID"]),
                    "season": season,
                    "season_type": season_type,
                    "gp": int(r.get("GP", 0)),
                    "w": int(r.get("W", 0)),
                    "l": int(r.get("L", 0)),
                    "w_pct": float(r.get("W_PCT", 0.0)) if pd.notnull(r.get("W_PCT")) else 0.0,
                    "min": float(r.get("MIN", 0.0)) if pd.notnull(r.get("MIN")) else 0.0,
                    "off_rating": float(r.get("OFF_RATING", 0.0)) if pd.notnull(r.get("OFF_RATING")) else 0.0,
                    "def_rating": float(r.get("DEF_RATING", 0.0)) if pd.notnull(r.get("DEF_RATING")) else 0.0,
                    "net_rating": float(r.get("NET_RATING", 0.0)) if pd.notnull(r.get("NET_RATING")) else 0.0,
                    "ast_pct": float(r.get("AST_PCT", 0.0)) if pd.notnull(r.get("AST_PCT")) else 0.0,
                    "ast_to": float(r.get("AST_TO", 0.0)) if pd.notnull(r.get("AST_TO")) else 0.0,
                    "ast_ratio": float(r.get("AST_RATIO", 0.0)) if pd.notnull(r.get("AST_RATIO")) else 0.0,
                    "oreb_pct": float(r.get("OREB_PCT", 0.0)) if pd.notnull(r.get("OREB_PCT")) else 0.0,
                    "dreb_pct": float(r.get("DREB_PCT", 0.0)) if pd.notnull(r.get("DREB_PCT")) else 0.0,
                    "reb_pct": float(r.get("REB_PCT", 0.0)) if pd.notnull(r.get("REB_PCT")) else 0.0,
                    "tm_tov_pct": float(r.get("TM_TOV_PCT", 0.0)) if pd.notnull(r.get("TM_TOV_PCT")) else 0.0,
                    "efg_pct": float(r.get("EFG_PCT", 0.0)) if pd.notnull(r.get("EFG_PCT")) else 0.0,
                    "ts_pct": float(r.get("TS_PCT", 0.0)) if pd.notnull(r.get("TS_PCT")) else 0.0,
                    "pace": float(r.get("PACE", 0.0)) if pd.notnull(r.get("PACE")) else 0.0,
                    "pie": float(r.get("PIE", 0.0)) if pd.notnull(r.get("PIE")) else 0.0,
                }
            )

        self.db.upsert_rows(
            "team_advanced_stats",
            rows,
            conflict_keys=["team_id", "season", "season_type"],
        )
        logger.info("Ingested %d team advanced stats records.", len(rows))
        return len(rows)

    def is_season_ingested(self, season: str) -> bool:
        """Checks if a season's player stats or game logs already exist in the database."""
        df = self.db.query_df("SELECT COUNT(*) AS cnt FROM player_season_stats WHERE season = ?", (season,))
        if not df.empty and df.iloc[0]["cnt"] > 0:
            return True
        return False

    def ingest_season(
        self,
        season: str,
        include_playoffs: bool = True,
    ) -> Dict[str, Any]:
        """Comprehensive resilient ingestion for any season from 1946 to present."""
        logger.info(">>> Ingesting Season %s (Playoffs=%s) <<<", season, include_playoffs)
        summary: Dict[str, Any] = {"season": season}

        # 1. Regular Season Standings
        try:
            summary["standings"] = self.ingest_standings(season, "Regular Season")
        except Exception as e:
            logger.warning("Standings for %s not available: %s", season, e)
            summary["standings"] = 0

        # 2. Player Traditional Stats
        try:
            summary["player_stats"] = self.ingest_player_season_stats(season, "Regular Season")
        except Exception as e:
            logger.warning("Player season stats for %s not available: %s", season, e)
            summary["player_stats"] = 0

        # 3. Advanced Stats (tracking data available post-1996)
        try:
            summary["player_advanced_stats"] = self.ingest_player_advanced_stats(season, "Regular Season")
            summary["team_advanced_stats"] = self.ingest_team_advanced_stats(season, "Regular Season")
        except Exception as e:
            logger.debug("Advanced stats not available for %s: %s", season, e)

        # 4. Games & Game Logs
        try:
            rs_games = self.ingest_games_and_game_logs(season, "Regular Season")
            summary["rs_games"] = rs_games["games"]
            summary["rs_player_logs"] = rs_games["player_game_logs"]
        except Exception as e:
            logger.warning("Game logs for %s failed: %s", season, e)
            summary["rs_games"] = 0
            summary["rs_player_logs"] = 0

        # 5. Playoffs
        if include_playoffs:
            try:
                self.ingest_player_season_stats(season, "Playoffs")
                self.ingest_player_advanced_stats(season, "Playoffs")
                self.ingest_team_advanced_stats(season, "Playoffs")
            except Exception:
                pass
            try:
                po_games = self.ingest_games_and_game_logs(season, "Playoffs")
                summary["po_games"] = po_games.get("games", 0)
                summary["po_player_logs"] = po_games.get("player_game_logs", 0)
            except Exception as e:
                logger.debug("Playoffs for %s not available: %s", season, e)

        return summary

    def ingest_all_history(
        self,
        start_year: int = 2024,
        end_year: int = 1946,
        skip_existing: bool = True,
        on_progress: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Downloads all historical NBA data in reverse chronological order
        from start_year (e.g. 2024-25) down to end_year (1946-47).
        """
        seasons = [f"{y}-{str(y+1)[-2:]}" for y in range(start_year, end_year - 1, -1)]
        total = len(seasons)
        logger.info("Starting historical ingestion across %d seasons (from %s down to %s)...", total, seasons[0], seasons[-1])

        # Ensure base teams, players, and profiles exist
        self.ingest_teams()
        self.ingest_players()
        self.ingest_player_profiles()

        results = {}
        for idx, season in enumerate(seasons, 1):
            if skip_existing and self.is_season_ingested(season):
                logger.info("[%d/%d] Season %s already ingested, skipping.", idx, total, season)
                results[season] = "already_ingested"
                if on_progress:
                    on_progress(idx, total, season, "skipped")
                continue

            logger.info("[%d/%d] Ingesting season %s...", idx, total, season)
            try:
                res = self.ingest_season(season, include_playoffs=True)
                results[season] = res
                if on_progress:
                    on_progress(idx, total, season, "success")
            except Exception as exc:
                logger.error("[%d/%d] Failed season %s: %s", idx, total, season, exc)
                results[season] = f"failed: {exc}"
                if on_progress:
                    on_progress(idx, total, season, f"error: {exc}")

        return results

    def ingest_all(
        self,
        season: str = "2023-24",
        season_type: str = "Regular Season",
    ) -> Dict[str, Any]:
        """Full pipeline: inits DB, loads teams, players, profiles, standings, stats, and game logs."""
        logger.info("=== Starting Full NBA Stats Database Ingestion ===")
        results = {
            "teams": self.ingest_teams(),
            "players": self.ingest_players(),
            "player_profiles": self.ingest_player_profiles(),
            "standings": self.ingest_standings(season, season_type),
            "player_season_stats": self.ingest_player_season_stats(season, season_type),
            "player_advanced_stats": self.ingest_player_advanced_stats(season, season_type),
            "team_advanced_stats": self.ingest_team_advanced_stats(season, season_type),
        }
        game_results = self.ingest_games_and_game_logs(season, season_type)
        results.update(game_results)
        logger.info("=== Ingestion Completed Successfully ===")
        return results
