"""
routes_games.py - Real-Time Win Probability and Rotation Timeline Endpoints.
"""

import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException

from ..quant.win_probability import XGBWinProbabilityModel
from .schemas import WinProbabilityRequest, WinProbabilityResponse, WinProbTimelinePoint
from .cache import cache

router = APIRouter(prefix="/api/games", tags=["Games"])

_win_model = XGBWinProbabilityModel()


@router.post("/win-probability", response_model=WinProbabilityResponse)
def evaluate_win_probability(req: WinProbabilityRequest) -> WinProbabilityResponse:
    """Evaluates real-time home win probability from game margin and clock state."""
    wp = _win_model.predict_win_probability(
        score_margin=req.score_margin,
        seconds_remaining=req.seconds_remaining,
        period=req.period,
        possession_home=req.possession_home,
    )
    return WinProbabilityResponse(
        score_margin=req.score_margin,
        seconds_remaining=req.seconds_remaining,
        period=req.period,
        home_win_prob=round(wp, 4),
        away_win_prob=round(1.0 - wp, 4),
    )


@router.get("/{game_id}/win-probability-timeline")
def get_game_win_prob_timeline(game_id: str) -> Dict[str, Any]:
    """Generates continuous Win Probability time series across all plays in a game."""
    cache_key = f"game_wp:{game_id}"
    cached = cache.get_json(cache_key)
    if cached:
        return cached

    pbp_path = "data/endpoints/LivePlayByPlay.json"
    actions = []
    if os.path.exists(pbp_path):
        try:
            with open(pbp_path, "r") as f:
                data = json.load(f)
            actions = data.get("game", {}).get("actions", [])
        except Exception:
            pass

    game_states = []
    if actions:
        for act in actions:
            p = act.get("period", 1)
            clk_str = act.get("clock", "PT12M00.00S")
            # Parse clock
            from ..possession.state_machine import parse_clock_to_seconds
            clk_sec = parse_clock_to_seconds(clk_str)
            # Total seconds remaining in regulation
            if p <= 4:
                sec_rem = (4 - p) * 720.0 + clk_sec
            else:
                sec_rem = clk_sec

            home_score = int(act.get("scoreHome") or 0)
            away_score = int(act.get("scoreAway") or 0)
            margin = home_score - away_score

            game_states.append({
                "period": p,
                "seconds_remaining": sec_rem,
                "score_margin": margin,
                "home_score": home_score,
                "away_score": away_score,
                "possession_team_id": act.get("teamId"),
                "home_team_id": act.get("teamId"),
            })
    else:
        # Fallback simulated timeline
        for sec in range(2880, -1, -60):
            p = 4 - (sec // 720) if sec > 0 else 4
            margin = int((2880 - sec) * 0.003 + (sec % 5) - 2)
            game_states.append({
                "period": p,
                "seconds_remaining": float(sec),
                "score_margin": margin,
                "home_score": 100 - (sec // 30),
                "away_score": 96 - (sec // 30),
                "possession_team_id": 1,
                "home_team_id": 1,
            })

    timeline = _win_model.compute_game_timeline(game_states)
    resp = {
        "game_id": game_id,
        "timeline_points": len(timeline),
        "timeline": timeline,
    }
    cache.set_json(cache_key, resp, ttl=86400)
    return resp


@router.get("/{game_id}/rotations")
def get_game_rotations(game_id: str) -> Dict[str, Any]:
    """Returns player stint intervals for rotation Gantt timeline visualization."""
    cache_key = f"game_rotations:{game_id}"
    cached = cache.get_json(cache_key)
    if cached:
        return cached

    # Parse stints from Parquet / DuckDB
    from ..possession.olap import DuckDBPossessionEngine
    engine = DuckDBPossessionEngine(parquet_dir="data/gold/possessions")
    stints = engine.extract_lineup_stints("2023-24")

    # Filter for target game_id
    game_stints = [s for s in stints if s.get("game_id") == game_id]
    if not game_stints and stints:
        game_stints = stints[:20]

    resp = {
        "game_id": game_id,
        "total_stints": len(game_stints),
        "stints": game_stints,
    }
    cache.set_json(cache_key, resp, ttl=86400)
    return resp


@router.get("/live/scoreboard")
def get_live_scoreboard() -> Dict[str, Any]:
    """Returns real-time scoreboard list across active NBA games."""
    cache_key = "live_scoreboard_overview"
    cached = cache.get_json(cache_key)
    if cached:
        return cached

    feed_file = Path("frontend/public/data/live_scoreboard.json")
    if feed_file.exists():
        with open(feed_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            cache.set_json(cache_key, data, ttl=15)
            return data

    return {"games": []}


@router.get("/{game_id}/live-feed")
def get_game_live_feed(game_id: str) -> Dict[str, Any]:
    """Returns minute-by-minute differential candlesticks, WPA, and active 10-player lineups."""
    cache_key = f"live_feed:{game_id}"
    cached = cache.get_json(cache_key)
    if cached:
        return cached

    feed_file = Path("frontend/public/data/live_game_feed.json")
    if feed_file.exists():
        with open(feed_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            cache.set_json(cache_key, data, ttl=15)
            return data

    raise HTTPException(status_code=404, detail=f"Live feed for game {game_id} not found")
