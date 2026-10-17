"""
endpoints_catalog.py - Catalog, categorization, and parameter mapping
for all 135 nba_api stats endpoints and 3 live endpoints (138 total).
"""

import inspect
from typing import Any, Dict, List, Optional
import nba_api.stats.endpoints as stats_ep
import nba_api.live.nba.endpoints as live_ep

# Standard default parameter values for endpoint invocation
CANONICAL_DEFAULTS: Dict[str, Any] = {
    # Teams: Boston Celtics (1610612738), LA Lakers (1610612747)
    "team_id": 1610612738,
    "team_id_nullable": 1610612738,
    "opponent_team_id_nullable": 1610612747,
    "vs_team_id": 1610612747,
    
    # Players: LeBron James (2544), Kevin Durant (201142), Nikola Jokic (203999)
    "player_id": 2544,
    "player_id_nullable": 2544,
    "person1_id": 2544,
    "person2_id": 201142,
    "player_id_list": "2544",
    "vs_player_id_list": "201142",
    "vs_player_id": 201142,
    
    # Games: 2023-24 season game Denver Nuggets vs LA Lakers
    "game_id": "0022300001",
    "game_ids": "0022300001",
    "game_id_nullable": "0022300001",
    
    # Seasons & Dates
    "season": "2023-24",
    "season_nullable": "2023-24",
    "season_year": "2023-24",
    "season_type": "Regular Season",
    "season_type_playoffs": "Regular Season",
    "season_type_all_star": "Regular Season",
    "season_type_all_star_nullable": "Regular Season",
    
    # 5-man lineups (Lakers vs Celtics)
    "player_id1": 2544,
    "player_id2": 203076,
    "player_id3": 1629060,
    "player_id4": 1630559,
    "player_id5": 1629637,
    "vs_player_id1": 1628369,
    "vs_player_id2": 1627759,
    "vs_player_id3": 201142,
    "vs_player_id4": 203935,
    "vs_player_id5": 1628401,
    
    # Other specialized parameters
    "college": "Duke",
    "minutes_min": 10,
    "league_id": "00",
    "league_id_nullable": "00",
}

# Categorization mapping
CATEGORY_KEYWORDS: List[tuple] = [
    ("Live Feeds", ["ScoreBoard", "BoxScore", "PlayByPlay"], "live"),
    ("Box Scores & Play-by-Play", ["BoxScore", "PlayByPlay", "GameRotation", "InfographicFanDuelPlayer", "WinProbabilityPBP"], "stats"),
    ("Shot Charts & Lineups", ["ShotChart", "Lineup", "Lineups"], "stats"),
    ("Draft & Combine", ["Draft"], "stats"),
    ("Hustle & Tracking", ["Hustle", "PtShot", "PtDefend", "PtStats", "PtReb", "PtPass", "PlayerTrack", "DefenseHub"], "stats"),
    ("Historical & Franchise", ["AllTime", "Franchise", "Historical"], "stats"),
    ("Player Analytics", ["Player", "CumeStatsPlayer"], "stats"),
    ("Team Analytics", ["Team", "CumeStatsTeam"], "stats"),
    ("League & Standings", ["League", "Standings", "Leaders", "HomePage", "Scoreboard", "PlayoffPicture", "Matchups", "Synergy", "Fantasy", "Video"], "stats"),
]


def determine_category(name: str, is_live: bool = False) -> str:
    if is_live:
        return "Live Feeds"
    for cat_name, kw_list, module_type in CATEGORY_KEYWORDS:
        if module_type == "stats":
            for kw in kw_list:
                if kw in name:
                    return cat_name
    return "League & Standings"


def get_all_endpoints_catalog() -> Dict[str, Dict[str, Any]]:
    """
    Reflects on nba_api to extract all 135 stats endpoints and 3 live endpoints.
    Returns a dictionary of endpoint metadata indexed by endpoint identifier.
    """
    catalog: Dict[str, Dict[str, Any]] = {}

    # 1. nba_api.stats.endpoints (135 classes)
    for name, cls in inspect.getmembers(stats_ep, inspect.isclass):
        sig = inspect.signature(cls.__init__)
        required_params = []
        all_params = {}

        for p_name, param in sig.parameters.items():
            if p_name in ("self", "proxy", "headers", "timeout", "get_request"):
                continue
            is_req = param.default == inspect.Parameter.empty
            if is_req:
                required_params.append(p_name)
            all_params[p_name] = {
                "required": is_req,
                "default": str(param.default) if not is_req else None,
            }

        doc = (cls.__doc__ or "").strip().split("\n")[0]
        category = determine_category(name, is_live=False)

        # Build default test parameter dictionary for this endpoint
        test_params = {}
        for p_name, p_info in all_params.items():
            if p_info["required"]:
                test_params[p_name] = CANONICAL_DEFAULTS.get(p_name, "00")
            elif p_name in ("season", "season_nullable", "season_year") and p_info["default"] in (None, "", "2025-26", "2024-25"):
                test_params[p_name] = "2023-24"

        catalog[name] = {
            "name": name,
            "module": "nba_api.stats.endpoints",
            "category": category,
            "docstring": doc,
            "required_params": required_params,
            "all_params": all_params,
            "default_test_params": test_params,
            "is_live": False,
            "class_ref": cls,
        }

    # 2. nba_api.live.nba.endpoints (3 classes)
    live_classes = [
        ("LiveScoreBoard", live_ep.ScoreBoard, {}),
        ("LiveBoxScore", live_ep.BoxScore, {"game_id": "0022300001"}),
        ("LivePlayByPlay", live_ep.PlayByPlay, {"game_id": "0022300001"}),
    ]
    for name, cls, def_params in live_classes:
        sig = inspect.signature(cls.__init__)
        required_params = []
        all_params = {}
        for p_name, param in sig.parameters.items():
            if p_name in ("self", "proxy", "headers", "timeout"):
                continue
            is_req = param.default == inspect.Parameter.empty
            if is_req:
                required_params.append(p_name)
            all_params[p_name] = {
                "required": is_req,
                "default": str(param.default) if not is_req else None,
            }

        doc = (cls.__doc__ or "").strip().split("\n")[0]
        catalog[name] = {
            "name": name,
            "module": "nba_api.live.nba.endpoints",
            "category": "Live Feeds",
            "docstring": doc,
            "required_params": required_params,
            "all_params": all_params,
            "default_test_params": def_params,
            "is_live": True,
            "class_ref": cls,
        }

    return catalog
