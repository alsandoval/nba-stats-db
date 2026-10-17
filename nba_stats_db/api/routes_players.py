"""
routes_players.py - Player 360 Explorer and Percentile Badge Endpoints.
"""

import sqlite3
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
import numpy as np

from .schemas import PlayerProfileResponse, PlayerPercentiles
from .cache import cache

router = APIRouter(prefix="/api/players", tags=["Players"])


def _db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect("nba_stats.db")
    conn.row_factory = sqlite3.Row
    return conn


@router.get("")
def list_players(
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> Dict[str, Any]:
    """Returns players with basic traditional and advanced stats for virtualized data grids."""
    cache_key = f"players_list:{search}:{limit}:{offset}"
    cached = cache.get_json(cache_key)
    if cached:
        return cached

    conn = _db_conn()
    cur = conn.cursor()

    where_clause = ""
    params = []
    if search:
        where_clause = "WHERE p.full_name LIKE ? OR pr.team_abbreviation LIKE ?"
        params.extend([f"%{search}%", f"%{search}%"])

    sql = f"""
    SELECT 
        p.player_id,
        p.full_name,
        p.is_active,
        COALESCE(pr.team_abbreviation, 'NBA') as team,
        COALESCE(s.pts, 0) as pts,
        COALESCE(s.reb, 0) as reb,
        COALESCE(s.ast, 0) as ast,
        COALESCE(s.stl, 0) as stl,
        COALESCE(s.blk, 0) as blk,
        COALESCE(a.ts_pct, 0.5) as ts_pct,
        COALESCE(a.net_rating, 0.0) as net_rating,
        COALESCE(a.usg_pct, 0.2) as usg_pct,
        COALESCE(a.pie, 0.1) as pie
    FROM players p
    LEFT JOIN player_profiles pr ON p.player_id = pr.player_id
    LEFT JOIN player_season_stats s ON p.player_id = s.player_id AND s.season = '2023-24'
    LEFT JOIN player_advanced_stats a ON p.player_id = a.player_id AND a.season = '2023-24'
    {where_clause}
    ORDER BY s.pts DESC
    LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    rows = cur.execute(sql, params).fetchall()

    count_sql = f"SELECT count(*) FROM players p LEFT JOIN player_profiles pr ON p.player_id = pr.player_id {where_clause}"
    total = cur.execute(count_sql, params[:-2]).fetchone()[0]
    conn.close()

    items = [dict(r) for r in rows]
    resp = {"total": total, "items": items}
    cache.set_json(cache_key, resp, ttl=3600)
    return resp


@router.get("/{player_id}", response_model=PlayerProfileResponse)
def get_player_profile(player_id: int) -> PlayerProfileResponse:
    """Returns comprehensive Player 360 profile card with percentile badges (0-100)."""
    cache_key = f"player_profile:{player_id}"
    cached = cache.get_json(cache_key)
    if cached:
        return PlayerProfileResponse(**cached)

    conn = _db_conn()
    cur = conn.cursor()

    # Player info
    p_row = cur.execute(
        """
        SELECT p.player_id, p.full_name, p.is_active, pr.team_id, pr.team_abbreviation
        FROM players p
        LEFT JOIN player_profiles pr ON p.player_id = pr.player_id
        WHERE p.player_id = ?
        """,
        [player_id],
    ).fetchone()

    if not p_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found.")

    # Season stats
    s_row = cur.execute(
        "SELECT * FROM player_season_stats WHERE player_id = ? ORDER BY season DESC LIMIT 1",
        [player_id],
    ).fetchone()

    # Advanced stats
    a_row = cur.execute(
        "SELECT * FROM player_advanced_stats WHERE player_id = ? ORDER BY season DESC LIMIT 1",
        [player_id],
    ).fetchone()

    # Recent games
    logs = cur.execute(
        """
        SELECT game_id, game_date, matchup, wl, min, pts, reb, ast, stl, blk, plus_minus
        FROM player_game_logs
        WHERE player_id = ?
        ORDER BY game_date DESC
        LIMIT 10
        """,
        [player_id],
    ).fetchall()

    # Compute percentiles across all players
    all_stats = cur.execute(
        """
        SELECT pts, reb, ast, stl, blk
        FROM player_season_stats
        WHERE pts IS NOT NULL
        """
    ).fetchall()
    all_pts = [r[0] for r in all_stats]
    all_reb = [r[1] for r in all_stats]
    all_ast = [r[2] for r in all_stats]
    all_stl = [r[3] for r in all_stats]
    all_blk = [r[4] for r in all_stats]

    conn.close()

    def pct(val: float, arr: List[float]) -> float:
        if not arr:
            return 50.0
        return round(float(np.mean(np.array(arr) <= val) * 100.0), 1)

    pts_val = s_row["pts"] if s_row and "pts" in s_row.keys() and s_row["pts"] is not None else 0.0
    reb_val = s_row["reb"] if s_row and "reb" in s_row.keys() and s_row["reb"] is not None else 0.0
    ast_val = s_row["ast"] if s_row and "ast" in s_row.keys() and s_row["ast"] is not None else 0.0
    stl_val = s_row["stl"] if s_row and "stl" in s_row.keys() and s_row["stl"] is not None else 0.0
    blk_val = s_row["blk"] if s_row and "blk" in s_row.keys() and s_row["blk"] is not None else 0.0

    percentiles = PlayerPercentiles(
        pts=pct(pts_val, all_pts),
        reb=pct(reb_val, all_reb),
        ast=pct(ast_val, all_ast),
        stl=pct(stl_val, all_stl),
        blk=pct(blk_val, all_blk),
        ts_pct=round(float(a_row["ts_pct"] * 100.0) if a_row and "ts_pct" in a_row.keys() and a_row["ts_pct"] else 55.0, 1),
        net_rating=round(float(a_row["net_rating"]) if a_row and "net_rating" in a_row.keys() and a_row["net_rating"] else 0.0, 1),
        pie=round(float(a_row["pie"] * 100.0) if a_row and "pie" in a_row.keys() and a_row["pie"] else 10.0, 1),
    )

    trad = dict(s_row) if s_row else {}
    adv = dict(a_row) if a_row else {}

    resp = {
        "player_id": p_row["player_id"],
        "full_name": p_row["full_name"],
        "team_id": p_row["team_id"],
        "team_abbreviation": p_row["team_abbreviation"],
        "is_active": bool(p_row["is_active"]),
        "archetype": "Versatile Primary Creator" if pts_val > 20 and ast_val > 5 else "3-and-D Specialist",
        "traditional_stats": trad,
        "advanced_stats": adv,
        "percentiles": percentiles.model_dump(),
        "recent_games": [dict(r) for r in logs],
    }

    cache.set_json(cache_key, resp, ttl=86400)
    return PlayerProfileResponse(**resp)
