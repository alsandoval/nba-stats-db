"""
routes_wowy.py - Vectorized With-Or-Without-You (WOWY) Lineup Query Endpoints.
"""

import sqlite3
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query

from ..possession.bitmask import TeamSeasonBitmaskIndexer
from ..possession.olap import DuckDBPossessionEngine
from .schemas import WOWYRequest, WOWYResponse
from .cache import cache

router = APIRouter(prefix="/api/wowy", tags=["WOWY"])

_indexer = TeamSeasonBitmaskIndexer()
_engine = DuckDBPossessionEngine(parquet_dir="data/gold/possessions")
try:
    _engine.conn.execute("SELECT count(*) FROM possessions").fetchall()
except Exception:
    pass


def _get_team_roster_from_db(team_id: int, season: str) -> List[Dict[str, Any]]:
    """Fetches active roster players (top 25 by minutes) and maps them into the bitmask indexer."""
    conn = sqlite3.connect("nba_stats.db")
    cur = conn.cursor()
    sql = """
    SELECT p.player_id, p.full_name, ROUND(AVG(l.min), 1) as avg_min
    FROM player_game_logs l
    JOIN players p ON l.player_id = p.player_id
    WHERE l.team_id = ?
    GROUP BY p.player_id, p.full_name
    ORDER BY SUM(l.min) DESC
    LIMIT 25
    """
    rows = cur.execute(sql, [team_id]).fetchall()
    conn.close()

    roster = []
    for r in rows:
        pid, name, avg_min = r[0], r[1], r[2]
        bit_idx = _indexer.get_bit_index(team_id, season, pid)
        roster.append({
            "player_id": pid,
            "full_name": name,
            "avg_min": avg_min,
            "bit_index": bit_idx,
        })
    return roster


@router.get("/team/{team_id}/roster")
def get_team_wowy_roster(
    team_id: int,
    season: str = Query(default="2023-24"),
) -> Dict[str, Any]:
    """Returns roster for a team with 64-bit bitmask indices for interactive WOWY selection."""
    cache_key = f"wowy_roster:{team_id}:{season}"
    cached = cache.get_json(cache_key)
    if cached:
        return cached

    roster = _get_team_roster_from_db(team_id, season)
    res = {
        "team_id": team_id,
        "season": season,
        "roster_count": len(roster),
        "roster": roster,
    }
    cache.set_json(cache_key, res, ttl=3600)
    return res


@router.post("/evaluate", response_model=WOWYResponse)
def evaluate_wowy(req: WOWYRequest) -> WOWYResponse:
    """
    Executes sub-15ms vectorized DuckDB bitwise query over Parquet possessions.
    Filter: (off_mask & M_on == M_on) & (off_mask & M_off == 0)
    """
    # Ensure team roster is indexed
    _get_team_roster_from_db(req.team_id, req.season)

    try:
        res = _engine.query_wowy(
            season=req.season,
            team_id=req.team_id,
            on_player_ids=req.on_player_ids,
            off_player_ids=req.off_player_ids,
            indexer=_indexer,
        )
        return WOWYResponse(**res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"WOWY evaluation error: {str(e)}")
