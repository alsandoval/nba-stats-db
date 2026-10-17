import unicodedata
from typing import Any, Dict, List, Optional, Union
import pandas as pd
from .database import NBADatabase


def _normalize_str(text: str) -> str:
    """Normalizes string by removing accents and lowercasing for fuzzy search."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    ).lower()


class NBAQueryHelper:
    """Provides high-level analytical query methods on top of NBADatabase."""

    def __init__(self, db: Optional[NBADatabase] = None):
        self.db = db or NBADatabase()

    def execute_sql(self, sql: str, params: Union[tuple, dict] = ()) -> pd.DataFrame:
        """Executes an arbitrary SQL query and returns a Pandas DataFrame."""
        return self.db.query_df(sql, params)

    def search_players(self, name_query: str) -> pd.DataFrame:
        """Finds players whose full name matches the query string (accent-insensitive)."""
        df = self.db.query_df("SELECT player_id, full_name, is_active FROM players")
        if df.empty:
            return df
        norm_query = _normalize_str(name_query)
        matches = df[df["full_name"].apply(lambda n: norm_query in _normalize_str(n))]
        return matches.sort_values(by=["is_active", "full_name"], ascending=[False, True])

    def get_top_scorers(
        self,
        season: str = "2023-24",
        season_type: str = "Regular Season",
        limit: int = 10,
        min_gp: int = 20,
    ) -> pd.DataFrame:
        """Returns the top PPG scorers in a season."""
        sql = """
        SELECT 
            p.full_name AS Player,
            s.team_abbreviation AS Team,
            s.gp AS GP,
            ROUND(s.min, 1) AS MPG,
            ROUND(s.pts, 1) AS PPG,
            ROUND(s.reb, 1) AS RPG,
            ROUND(s.ast, 1) AS APG,
            ROUND(s.stl, 1) AS SPG,
            ROUND(s.blk, 1) AS BPG,
            ROUND(s.fg_pct * 100, 1) AS `FG%`,
            ROUND(s.fg3_pct * 100, 1) AS `3P%`,
            ROUND(s.ft_pct * 100, 1) AS `FT%`
        FROM player_season_stats s
        JOIN players p ON s.player_id = p.player_id
        WHERE s.season = ? AND s.season_type = ? AND s.gp >= ?
        ORDER BY s.pts DESC
        LIMIT ?
        """
        return self.db.query_df(sql, (season, season_type, min_gp, limit))

    def get_standings(
        self,
        season: str = "2023-24",
        conference: Optional[str] = None,
        season_type: str = "Regular Season",
    ) -> pd.DataFrame:
        """Returns league standings, optionally filtered by conference ('East' or 'West')."""
        if conference:
            sql = """
            SELECT 
                t.full_name AS Team,
                s.conference AS Conf,
                s.conf_rank AS Rank,
                s.w AS W,
                s.l AS L,
                ROUND(s.win_pct, 3) AS `Win%`,
                s.home_record AS Home,
                s.road_record AS Road,
                s.l10 AS L10,
                s.strk AS Streak,
                ROUND(s.pts, 1) AS PPG,
                ROUND(s.opp_pts, 1) AS `Opp PPG`,
                ROUND(s.diff, 1) AS Diff
            FROM team_season_stats s
            JOIN teams t ON s.team_id = t.team_id
            WHERE s.season = ? AND s.season_type = ? AND s.conference = ?
            ORDER BY s.conf_rank ASC
            """
            return self.db.query_df(sql, (season, season_type, conference))
        else:
            sql = """
            SELECT 
                t.full_name AS Team,
                s.conference AS Conf,
                s.conf_rank AS Rank,
                s.w AS W,
                s.l AS L,
                ROUND(s.win_pct, 3) AS `Win%`,
                s.home_record AS Home,
                s.road_record AS Road,
                s.l10 AS L10,
                s.strk AS Streak,
                ROUND(s.pts, 1) AS PPG,
                ROUND(s.opp_pts, 1) AS `Opp PPG`,
                ROUND(s.diff, 1) AS Diff
            FROM team_season_stats s
            JOIN teams t ON s.team_id = t.team_id
            WHERE s.season = ? AND s.season_type = ?
            ORDER BY s.conference ASC, s.conf_rank ASC
            """
            return self.db.query_df(sql, (season, season_type))

    def get_player_game_logs(
        self,
        player_name: str,
        limit: int = 15,
    ) -> pd.DataFrame:
        """Returns recent game logs for a given player (accent-insensitive)."""
        matching_players = self.search_players(player_name)
        if matching_players.empty:
            return pd.DataFrame()

        target_player_id = int(matching_players.iloc[0]["player_id"])

        sql = """
        SELECT 
            p.full_name AS Player,
            l.game_date AS Date,
            l.matchup AS Matchup,
            l.wl AS WL,
            ROUND(l.min, 0) AS MIN,
            l.pts AS PTS,
            l.reb AS REB,
            l.ast AS AST,
            l.stl AS STL,
            l.blk AS BLK,
            ROUND(l.fgm, 0) || '/' || ROUND(l.fga, 0) AS FGM_A,
            ROUND(l.fg_pct * 100, 1) AS `FG%`,
            ROUND(l.fg3m, 0) || '/' || ROUND(l.fg3a, 0) AS `3PM_A`,
            l.plus_minus AS `+/-`
        FROM player_game_logs l
        JOIN players p ON l.player_id = p.player_id
        WHERE l.player_id = ?
        ORDER BY l.game_date DESC
        LIMIT ?
        """
        return self.db.query_df(sql, (target_player_id, limit))

    def get_highest_scoring_games(
        self,
        limit: int = 10,
    ) -> pd.DataFrame:
        """Returns the highest single-game scoring performances in the database."""
        sql = """
        SELECT 
            p.full_name AS Player,
            l.game_date AS Date,
            l.matchup AS Matchup,
            l.pts AS PTS,
            l.reb AS REB,
            l.ast AS AST,
            ROUND(l.fgm, 0) || '/' || ROUND(l.fga, 0) AS FG,
            ROUND(l.fg3m, 0) || '/' || ROUND(l.fg3a, 0) AS `3PT`,
            ROUND(l.ftm, 0) || '/' || ROUND(l.fta, 0) AS FT,
            l.plus_minus AS `+/-`
        FROM player_game_logs l
        JOIN players p ON l.player_id = p.player_id
        ORDER BY l.pts DESC
        LIMIT ?
        """
        return self.db.query_df(sql, (limit,))

    def get_head_to_head(
        self,
        team_abbr_1: str,
        team_abbr_2: str,
    ) -> pd.DataFrame:
        """Returns all head-to-head games between two teams."""
        sql = """
        SELECT 
            g.game_id AS GameID,
            g.game_date AS Date,
            g.matchup AS Matchup,
            ht.abbreviation AS HomeTeam,
            g.home_team_pts AS HomePTS,
            vt.abbreviation AS AwayTeam,
            g.visitor_team_pts AS AwayPTS,
            wt.abbreviation AS Winner
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.team_id
        JOIN teams vt ON g.visitor_team_id = vt.team_id
        LEFT JOIN teams wt ON g.winner_team_id = wt.team_id
        WHERE (ht.abbreviation = ? AND vt.abbreviation = ?)
           OR (ht.abbreviation = ? AND vt.abbreviation = ?)
        ORDER BY g.game_date DESC
        """
        return self.db.query_df(
            sql, (team_abbr_1, team_abbr_2, team_abbr_2, team_abbr_1)
        )

    def get_triple_doubles(self, limit: int = 15) -> pd.DataFrame:
        """Finds games where a player recorded a triple-double."""
        sql = """
        SELECT 
            p.full_name AS Player,
            l.game_date AS Date,
            l.matchup AS Matchup,
            l.pts AS PTS,
            l.reb AS REB,
            l.ast AS AST,
            l.stl AS STL,
            l.blk AS BLK,
            l.wl AS Result
        FROM player_game_logs l
        JOIN players p ON l.player_id = p.player_id
        WHERE (
            (CASE WHEN l.pts >= 10 THEN 1 ELSE 0 END) +
            (CASE WHEN l.reb >= 10 THEN 1 ELSE 0 END) +
            (CASE WHEN l.ast >= 10 THEN 1 ELSE 0 END) +
            (CASE WHEN l.stl >= 10 THEN 1 ELSE 0 END) +
            (CASE WHEN l.blk >= 10 THEN 1 ELSE 0 END)
        ) >= 3
        ORDER BY l.game_date DESC
        LIMIT ?
        """
        return self.db.query_df(sql, (limit,))

    def get_available_seasons(self) -> List[str]:
        """Returns distinct seasons present in games/stats."""
        sql = "SELECT DISTINCT season FROM player_season_stats ORDER BY season DESC"
        df = self.db.query_df(sql)
        if df.empty:
            return ["2023-24"]
        return df["season"].tolist()

    def get_recent_games(self, limit: int = 15) -> pd.DataFrame:
        """Returns the most recent games with home/visitor teams and scores."""
        sql = """
        SELECT 
            g.game_id,
            g.game_date AS Date,
            g.matchup AS Matchup,
            ht.abbreviation AS HomeTeam,
            ht.full_name AS HomeName,
            g.home_team_pts AS HomePTS,
            vt.abbreviation AS AwayTeam,
            vt.full_name AS AwayName,
            g.visitor_team_pts AS AwayPTS,
            wt.abbreviation AS Winner
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.team_id
        JOIN teams vt ON g.visitor_team_id = vt.team_id
        LEFT JOIN teams wt ON g.winner_team_id = wt.team_id
        WHERE g.home_team_pts IS NOT NULL
        ORDER BY g.game_date DESC, g.game_id DESC
        LIMIT ?
        """
        return self.db.query_df(sql, (limit,))

    def get_player_profile(self, player_name: str) -> Dict[str, Any]:
        """Returns comprehensive player profile, career trajectory, and season averages."""
        matching = self.search_players(player_name)
        if matching.empty:
            return {}

        player_row = matching.iloc[0]
        pid = int(player_row["player_id"])
        name = str(player_row["full_name"])

        # Profile info
        prof_df = self.db.query_df(
            "SELECT * FROM player_profiles WHERE player_id = ?", (pid,)
        )
        profile_dict = prof_df.to_dict(orient="records")[0] if not prof_df.empty else {
            "player_id": pid,
            "display_first_last": name,
            "team_abbreviation": "N/A",
            "from_year": None,
            "to_year": None,
            "roster_status": "Active" if player_row.get("is_active") else "Inactive",
        }

        # Season traditional stats
        stats_sql = """
        SELECT 
            season, season_type, team_abbreviation, gp, 
            ROUND(min, 1) AS mpg,
            ROUND(pts, 1) AS ppg,
            ROUND(reb, 1) AS rpg,
            ROUND(ast, 1) AS apg,
            ROUND(stl, 1) AS spg,
            ROUND(blk, 1) AS bpg,
            ROUND(fg_pct * 100, 1) AS `fg_pct`,
            ROUND(fg3_pct * 100, 1) AS `fg3_pct`,
            ROUND(ft_pct * 100, 1) AS `ft_pct`,
            ROUND(plus_minus, 1) AS `plus_minus`
        FROM player_season_stats
        WHERE player_id = ?
        ORDER BY season DESC, season_type ASC
        """
        stats_df = self.db.query_df(stats_sql, (pid,))

        # Advanced stats
        adv_sql = """
        SELECT 
            season, season_type,
            ROUND(off_rating, 1) AS off_rating,
            ROUND(def_rating, 1) AS def_rating,
            ROUND(net_rating, 1) AS net_rating,
            ROUND(ts_pct * 100, 1) AS ts_pct,
            ROUND(usg_pct * 100, 1) AS usg_pct,
            ROUND(pie * 100, 1) AS pie,
            ROUND(pace, 1) AS pace
        FROM player_advanced_stats
        WHERE player_id = ?
        ORDER BY season DESC
        """
        adv_df = self.db.query_df(adv_sql, (pid,))

        # Recent games
        recent_logs = self.get_player_game_logs(name, limit=10)

        return {
            "player_id": pid,
            "name": name,
            "profile": profile_dict,
            "seasons": stats_df.to_dict(orient="records"),
            "advanced": adv_df.to_dict(orient="records"),
            "recent_games": recent_logs.to_dict(orient="records"),
        }

    def compare_players(
        self,
        player1_name: str,
        player2_name: str,
        season: str = "2023-24",
    ) -> Dict[str, Any]:
        """
        Side-by-side comparison between two players:
        - Traditional stats comparison
        - Advanced stats comparison
        - Head-to-head games when they faced each other
        """
        p1_search = self.search_players(player1_name)
        p2_search = self.search_players(player2_name)

        if p1_search.empty or p2_search.empty:
            return {"error": "One or both players could not be found."}

        p1_id = int(p1_search.iloc[0]["player_id"])
        p2_id = int(p2_search.iloc[0]["player_id"])
        p1_name = str(p1_search.iloc[0]["full_name"])
        p2_name = str(p2_search.iloc[0]["full_name"])

        # Fetch stats for both players
        def get_stats(pid):
            sql = """
            SELECT 
                p.full_name AS name,
                s.team_abbreviation AS team,
                s.gp,
                ROUND(s.min, 1) AS mpg,
                ROUND(s.pts, 1) AS ppg,
                ROUND(s.reb, 1) AS rpg,
                ROUND(s.ast, 1) AS apg,
                ROUND(s.stl, 1) AS spg,
                ROUND(s.blk, 1) AS bpg,
                ROUND(s.fg_pct * 100, 1) AS fg_pct,
                ROUND(s.fg3_pct * 100, 1) AS fg3_pct,
                ROUND(s.ft_pct * 100, 1) AS ft_pct,
                ROUND(s.plus_minus, 1) AS plus_minus,
                ROUND(a.off_rating, 1) AS off_rating,
                ROUND(a.def_rating, 1) AS def_rating,
                ROUND(a.net_rating, 1) AS net_rating,
                ROUND(a.ts_pct * 100, 1) AS ts_pct,
                ROUND(a.usg_pct * 100, 1) AS usg_pct,
                ROUND(a.pie * 100, 1) AS pie
            FROM player_season_stats s
            JOIN players p ON s.player_id = p.player_id
            LEFT JOIN player_advanced_stats a 
                ON s.player_id = a.player_id 
               AND s.season = a.season 
               AND s.season_type = a.season_type
            WHERE s.player_id = ? AND s.season = ? AND s.season_type = 'Regular Season'
            """
            df = self.db.query_df(sql, (pid, season))
            if df.empty:
                # Fallback if specific season not found
                return {"name": pid, "team": "N/A", "gp": 0, "ppg": 0.0, "rpg": 0.0, "apg": 0.0}
            return df.to_dict(orient="records")[0]

        p1_stats = get_stats(p1_id)
        p2_stats = get_stats(p2_id)
        p1_stats["name"] = p1_name
        p2_stats["name"] = p2_name

        # Direct Head-to-Head games where BOTH played in the same game
        h2h_sql = """
        SELECT 
            g.game_date AS date,
            l1.matchup AS matchup,
            l1.wl AS p1_wl,
            l1.pts AS p1_pts,
            l1.reb AS p1_reb,
            l1.ast AS p1_ast,
            l2.pts AS p2_pts,
            l2.reb AS p2_reb,
            l2.ast AS p2_ast
        FROM player_game_logs l1
        JOIN player_game_logs l2 ON l1.game_id = l2.game_id AND l2.player_id = ?
        JOIN games g ON l1.game_id = g.game_id
        WHERE l1.player_id = ?
        ORDER BY g.game_date DESC
        """
        h2h_df = self.db.query_df(h2h_sql, (p2_id, p1_id))
        h2h_records = h2h_df.to_dict(orient="records")

        # Head-to-head summary record
        p1_wins = sum(1 for g in h2h_records if g.get("p1_wl") == "W")
        p2_wins = sum(1 for g in h2h_records if g.get("p1_wl") == "L")

        return {
            "season": season,
            "player1": p1_stats,
            "player2": p2_stats,
            "h2h": {
                "total_games": len(h2h_records),
                "player1_wins": p1_wins,
                "player2_wins": p2_wins,
                "games": h2h_records,
            },
        }

    def compare_teams(
        self,
        team1_abbr: str,
        team2_abbr: str,
        season: str = "2023-24",
    ) -> Dict[str, Any]:
        """
        Side-by-side comparison between two teams:
        - Standings, record, PPG, Opp PPG, differential
        - Advanced metrics (Off Rating, Def Rating, Net Rating, Pace, TS%)
        - Head-to-head games list and record
        """
        def get_team_stats(abbr):
            sql = """
            SELECT 
                t.team_id,
                t.full_name AS name,
                t.abbreviation AS abbr,
                s.conference AS conf,
                s.conf_rank,
                s.w,
                s.l,
                ROUND(s.win_pct, 3) AS win_pct,
                s.home_record,
                s.road_record,
                ROUND(s.pts, 1) AS ppg,
                ROUND(s.opp_pts, 1) AS opp_ppg,
                ROUND(s.diff, 1) AS diff,
                ROUND(a.off_rating, 1) AS off_rating,
                ROUND(a.def_rating, 1) AS def_rating,
                ROUND(a.net_rating, 1) AS net_rating,
                ROUND(a.pace, 1) AS pace,
                ROUND(a.ts_pct * 100, 1) AS ts_pct
            FROM teams t
            LEFT JOIN team_season_stats s 
                ON t.team_id = s.team_id 
               AND s.season = ? 
               AND s.season_type = 'Regular Season'
            LEFT JOIN team_advanced_stats a
                ON t.team_id = a.team_id
               AND a.season = ?
               AND a.season_type = 'Regular Season'
            WHERE t.abbreviation = ?
            """
            df = self.db.query_df(sql, (season, season, abbr.upper()))
            if df.empty:
                return {"name": abbr, "abbr": abbr, "w": 0, "l": 0}
            return df.to_dict(orient="records")[0]

        t1 = get_team_stats(team1_abbr)
        t2 = get_team_stats(team2_abbr)

        h2h_df = self.get_head_to_head(team1_abbr, team2_abbr)
        h2h_records = h2h_df.to_dict(orient="records")

        t1_wins = sum(1 for g in h2h_records if g.get("Winner") == team1_abbr.upper())
        t2_wins = sum(1 for g in h2h_records if g.get("Winner") == team2_abbr.upper())

        return {
            "season": season,
            "team1": t1,
            "team2": t2,
            "h2h": {
                "total_games": len(h2h_records),
                "team1_wins": t1_wins,
                "team2_wins": t2_wins,
                "games": h2h_records,
            },
        }

    def get_leaders_by_category(
        self,
        category: str = "pts",
        season: str = "2023-24",
        season_type: str = "Regular Season",
        limit: int = 15,
    ) -> pd.DataFrame:
        """Returns leaderboards for any given stat category."""
        valid_cols = {
            "pts": ("s.pts", "PPG"),
            "reb": ("s.reb", "RPG"),
            "ast": ("s.ast", "APG"),
            "stl": ("s.stl", "SPG"),
            "blk": ("s.blk", "BPG"),
            "fg3m": ("s.fg3m", "3PM/G"),
            "fg_pct": ("s.fg_pct * 100", "FG%"),
            "fg3_pct": ("s.fg3_pct * 100", "3P%"),
            "ft_pct": ("s.ft_pct * 100", "FT%"),
            "off_rating": ("a.off_rating", "Off Rating"),
            "def_rating": ("a.def_rating", "Def Rating"),
            "net_rating": ("a.net_rating", "Net Rating"),
            "ts_pct": ("a.ts_pct * 100", "TS%"),
            "usg_pct": ("a.usg_pct * 100", "USG%"),
            "pie": ("a.pie * 100", "PIE%"),
        }

        col_expr, label = valid_cols.get(category.lower(), ("s.pts", "PPG"))
        order = "ASC" if category.lower() == "def_rating" else "DESC"

        sql = f"""
        SELECT 
            p.full_name AS Player,
            s.team_abbreviation AS Team,
            s.gp AS GP,
            ROUND(s.min, 1) AS MPG,
            ROUND({col_expr}, 1) AS `{label}`,
            ROUND(s.pts, 1) AS PPG,
            ROUND(s.reb, 1) AS RPG,
            ROUND(s.ast, 1) AS APG,
            ROUND(s.fg_pct * 100, 1) AS `FG%`,
            ROUND(s.fg3_pct * 100, 1) AS `3P%`
        FROM player_season_stats s
        JOIN players p ON s.player_id = p.player_id
        LEFT JOIN player_advanced_stats a 
            ON s.player_id = a.player_id 
           AND s.season = a.season 
           AND s.season_type = a.season_type
        WHERE s.season = ? AND s.season_type = ? AND s.gp >= 15
        ORDER BY {col_expr} {order}
        LIMIT ?
        """
        return self.db.query_df(sql, (season, season_type, limit))

    def get_box_lebron_leaderboard(
        self,
        season: str = "2023-24",
        season_type: str = "Regular Season",
        min_minutes: float = 500.0,
        limit: int = 25,
        sort_by: str = "box_lebron",
    ) -> pd.DataFrame:
        """
        Returns Box LEBRON leaderboard for a season.
        sort_by options: 'box_lebron', 'o_lebron', 'd_lebron', 'wins_added'.
        """
        valid_sorts = {
            "box_lebron": "box_lebron",
            "o_lebron": "o_lebron",
            "d_lebron": "d_lebron",
            "wins_added": "wins_added",
        }
        order_col = valid_sorts.get(sort_by.lower(), "box_lebron")

        sql = f"""
        SELECT 
            player_name AS Player,
            team_abbreviation AS Team,
            gp AS GP,
            ROUND(min, 1) AS MIN,
            offensive_archetype AS `Off Archetype`,
            defensive_archetype AS `Def Archetype`,
            o_lebron AS `O-LEBRON`,
            d_lebron AS `D-LEBRON`,
            box_lebron AS `Box LEBRON`,
            wins_added AS `WAR / Wins Added`,
            box_lebron_percentile AS `Percentile`
        FROM box_lebron_ratings
        WHERE season = ? AND season_type = ? AND min >= ?
        ORDER BY {order_col} DESC
        LIMIT ?
        """
        return self.db.query_df(sql, (season, season_type, min_minutes, limit))

    def get_player_box_lebron_history(
        self,
        player_id: int,
        season_type: str = "Regular Season",
    ) -> pd.DataFrame:
        """Returns full career Box LEBRON progression for a given player."""
        sql = """
        SELECT 
            season AS Season,
            team_abbreviation AS Team,
            age AS Age,
            gp AS GP,
            ROUND(min, 1) AS MIN,
            offensive_archetype AS `Off Archetype`,
            defensive_archetype AS `Def Archetype`,
            o_lebron AS `O-LEBRON`,
            d_lebron AS `D-LEBRON`,
            box_lebron AS `Box LEBRON`,
            wins_added AS `WAR`,
            box_lebron_percentile AS `Percentile`
        FROM box_lebron_ratings
        WHERE player_id = ? AND season_type = ?
        ORDER BY season ASC
        """
        return self.db.query_df(sql, (player_id, season_type))

    def get_box_lebron_archetype_distribution(
        self,
        season: str = "2023-24",
        season_type: str = "Regular Season",
    ) -> pd.DataFrame:
        """Returns distribution count and average Box LEBRON by offensive archetype."""
        sql = """
        SELECT 
            offensive_archetype AS `Offensive Archetype`,
            COUNT(*) AS `Player Count`,
            ROUND(AVG(o_lebron), 2) AS `Avg O-LEBRON`,
            ROUND(AVG(d_lebron), 2) AS `Avg D-LEBRON`,
            ROUND(AVG(box_lebron), 2) AS `Avg Box LEBRON`,
            ROUND(AVG(wins_added), 2) AS `Avg WAR`
        FROM box_lebron_ratings
        WHERE season = ? AND season_type = ? AND min >= 300
        GROUP BY offensive_archetype
        ORDER BY `Avg Box LEBRON` DESC
        """
        return self.db.query_df(sql, (season, season_type))

    def get_position_clusters(
        self,
        season: str = "2023-24",
        season_type: str = "Regular Season",
        cluster_id: Optional[int] = None,
        min_minutes: float = 300.0,
        limit: int = 50,
    ) -> pd.DataFrame:
        """Returns player cluster assignments and 3D t-SNE coordinates for a season."""
        params: List[Any] = [season, season_type, min_minutes]
        cluster_clause = ""
        if cluster_id is not None:
            cluster_clause = "AND cluster_id = ?"
            params.append(cluster_id)
        params.append(limit)

        sql = f"""
        SELECT 
            player_name AS Player,
            team_abbreviation AS Team,
            gp AS GP,
            ROUND(min, 1) AS MIN,
            cluster_id AS `Cluster ID`,
            cluster_name AS `Position Archetype`,
            ROUND(tsne_x, 2) AS `t-SNE X`,
            ROUND(tsne_y, 2) AS `t-SNE Y`,
            ROUND(tsne_z, 2) AS `t-SNE Z`,
            ROUND(usg_pct * 100, 1) AS `USG%`,
            ROUND(ts_pct * 100, 1) AS `TS%`,
            ROUND(ast_pct * 100, 1) AS `AST%`,
            ROUND(reb_pct * 100, 1) AS `REB%`,
            ROUND(fg3a_rate * 100, 1) AS `3PA%`,
            box_lebron AS `Box LEBRON`
        FROM player_position_clusters
        WHERE season = ? AND season_type = ? AND min >= ? {cluster_clause}
        ORDER BY box_lebron DESC
        LIMIT ?
        """
        return self.db.query_df(sql, tuple(params))

    def get_cluster_summaries(
        self,
        season: str = "2023-24",
        season_type: str = "Regular Season",
    ) -> pd.DataFrame:
        """Returns aggregate cluster summaries and centroid statistics."""
        sql = """
        SELECT 
            cluster_id AS `ID`,
            cluster_name AS `Archetype Name`,
            COUNT(*) AS `Player Count`,
            ROUND(AVG(usg_pct) * 100, 1) AS `Avg USG%`,
            ROUND(AVG(ts_pct) * 100, 1) AS `Avg TS%`,
            ROUND(AVG(ast_pct) * 100, 1) AS `Avg AST%`,
            ROUND(AVG(reb_pct) * 100, 1) AS `Avg REB%`,
            ROUND(AVG(fg3a_rate) * 100, 1) AS `Avg 3PA%`,
            ROUND(AVG(stl_per_36), 2) AS `Avg STL/36`,
            ROUND(AVG(blk_per_36), 2) AS `Avg BLK/36`,
            ROUND(AVG(box_lebron), 2) AS `Avg Box LEBRON`
        FROM player_position_clusters
        WHERE season = ? AND season_type = ?
        GROUP BY cluster_id, cluster_name
        ORDER BY cluster_id ASC
        """
        return self.db.query_df(sql, (season, season_type))

    def get_lineup_evaluations(
        self,
        season: str = "2024-25",
        team: Optional[str] = None,
        min_net_rating: Optional[float] = None,
        limit: int = 25,
    ) -> pd.DataFrame:
        """Returns saved lineup evaluations and synergy scores."""
        params: List[Any] = [season]
        clauses = []
        if team is not None:
            clauses.append("team_abbreviation = ?")
            params.append(team.upper())
        if min_net_rating is not None:
            clauses.append("predicted_net_rating >= ?")
            params.append(min_net_rating)

        where_str = f"AND {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)

        sql = f"""
        SELECT 
            team_abbreviation AS Team,
            player_names AS Lineup,
            balance_grade AS Grade,
            ROUND(predicted_net_rating, 2) AS `Pred NetRtg`,
            ROUND(raw_lebron_sum, 2) AS `Raw LEBRON`,
            ROUND(offensive_synergy, 2) AS `Off Synergy`,
            ROUND(defensive_synergy, 2) AS `Def Synergy`,
            ROUND(usage_penalty, 2) AS `Usage Tax`,
            ROUND(spacing_rating, 2) AS `Spacing`
        FROM team_lineup_evaluations
        WHERE season = ? {where_str}
        ORDER BY predicted_net_rating DESC
        LIMIT ?
        """
        return self.db.query_df(sql, tuple(params))

