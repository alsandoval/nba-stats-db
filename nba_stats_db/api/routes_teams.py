"""
routes_teams.py - Team Standings, Advanced Net Ratings, and Roster Endpoints.
"""

import sqlite3
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query

from .cache import cache

router = APIRouter(prefix="/api/teams", tags=["Teams"])


def _db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect("nba_stats.db")
    conn.row_factory = sqlite3.Row
    return conn


@router.get("")
def list_teams(season: str = Query(default="2023-24")) -> Dict[str, Any]:
    """Returns all 30 NBA teams with standings, offensive/defensive ratings, and pace."""
    cache_key = f"teams_list:{season}"
    cached = cache.get_json(cache_key)
    if cached:
        return cached

    conn = _db_conn()
    cur = conn.cursor()

    sql = """
    SELECT 
        t.team_id,
        t.full_name,
        t.abbreviation,
        t.city,
        COALESCE(s.w, 0) as wins,
        COALESCE(s.l, 0) as losses,
        COALESCE(s.win_pct, 0.5) as win_pct,
        COALESCE(a.off_rating, 114.0) as off_rating,
        COALESCE(a.def_rating, 114.0) as def_rating,
        COALESCE(a.net_rating, 0.0) as net_rating,
        COALESCE(a.pace, 99.0) as pace,
        COALESCE(a.ts_pct, 0.57) as ts_pct
    FROM teams t
    JOIN team_season_stats s ON t.team_id = s.team_id AND s.season = ?
    LEFT JOIN team_advanced_stats a ON t.team_id = a.team_id AND a.season = ?
    ORDER BY s.win_pct DESC, a.net_rating DESC
    """
    rows = cur.execute(sql, [season, season]).fetchall()
    conn.close()

    teams = [dict(r) for r in rows]
    resp = {"season": season, "total": len(teams), "teams": teams}
    cache.set_json(cache_key, resp, ttl=86400)
    return resp


@router.get("/{team_id}")
def get_team_detail(team_id: int, season: str = Query(default="2023-24")) -> Dict[str, Any]:
    """Returns team overview, roster with minutes, and rating breakdown."""
    cache_key = f"team_detail:{team_id}:{season}"
    cached = cache.get_json(cache_key)
    if cached:
        return cached

    conn = _db_conn()
    cur = conn.cursor()

    team_row = cur.execute("SELECT * FROM teams WHERE team_id = ?", [team_id]).fetchone()
    if not team_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Team {team_id} not found.")

    stats_row = cur.execute(
        "SELECT * FROM team_season_stats WHERE team_id = ? AND season = ?", [team_id, season]
    ).fetchone()
    adv_row = cur.execute(
        "SELECT * FROM team_advanced_stats WHERE team_id = ? AND season = ?", [team_id, season]
    ).fetchone()

    roster_rows = cur.execute(
        """
        SELECT p.player_id, p.full_name, ROUND(AVG(l.min), 1) as min_per_game, ROUND(AVG(l.pts), 1) as pts_per_game
        FROM player_game_logs l
        JOIN players p ON l.player_id = p.player_id
        WHERE l.team_id = ?
        GROUP BY p.player_id, p.full_name
        ORDER BY min_per_game DESC
        LIMIT 20
        """,
        [team_id],
    ).fetchall()
    conn.close()

    resp = {
        "team": dict(team_row),
        "traditional_stats": dict(stats_row) if stats_row else {},
        "advanced_stats": dict(adv_row) if adv_row else {},
        "roster": [dict(r) for r in roster_rows],
    }
    cache.set_json(cache_key, resp, ttl=86400)
    return resp
