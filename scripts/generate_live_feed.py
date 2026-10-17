"""
generate_live_feed.py - Pre-computes and generates real-time live feed datasets,
including minute-by-minute score differential candlesticks, Win Probability Added (WPA),
expected shot quality (xeFG%), and active 10-player on-court lineups.
"""

import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nba_stats_db.possession.state_machine import parse_clock_to_seconds
from nba_stats_db.quant.win_probability import XGBWinProbabilityModel
from nba_stats_db.quant.shot_model import XGBExpectedShotModel


def load_live_data():
    pbp_file = Path("data/endpoints/LivePlayByPlay.json")
    box_file = Path("data/endpoints/LiveBoxScore.json")

    with open(pbp_file, "r", encoding="utf-8") as f:
        pbp_data = json.load(f)

    with open(box_file, "r", encoding="utf-8") as f:
        box_data = json.load(f)

    return pbp_data, box_data


def generate_live_game_feed():
    pbp_raw, box_raw = load_live_data()
    game_meta = box_raw.get("game", {})
    home_team = game_meta.get("homeTeam", {})
    away_team = game_meta.get("awayTeam", {})
    actions = pbp_raw.get("game", {}).get("actions", [])

    win_model = XGBWinProbabilityModel()
    shot_model = XGBExpectedShotModel()

    home_team_id = home_team.get("teamId", 1610612754)
    away_team_id = away_team.get("teamId", 1610612739)

    # Initial starters
    home_players = home_team.get("players", [])
    away_players = away_team.get("players", [])

    home_starters = [p["personId"] for p in home_players if str(p.get("starter")) == "1"]
    away_starters = [p["personId"] for p in away_players if str(p.get("starter")) == "1"]

    current_home_lineup = set(home_starters)
    current_away_lineup = set(away_starters)

    # Player lookup
    player_lookup = {}
    for p in home_players + away_players:
        player_lookup[p["personId"]] = {
            "personId": p["personId"],
            "name": p.get("name", ""),
            "nameI": p.get("nameI", ""),
            "jerseyNum": p.get("jerseyNum", ""),
            "position": p.get("position", "G"),
            "teamId": home_team_id if p in home_players else away_team_id,
            "teamTricode": "IND" if p in home_players else "CLE",
        }

    # Process events
    processed_events = []
    prev_wp = 0.525  # Slight pre-game home edge

    # Time series of margin per second for candlestick aggregation
    # Second s from 2880 down to 0: margin_at_sec[s]
    # We will initialize with 0
    margin_history: List[Dict[str, Any]] = []

    current_home_score = 0
    current_away_score = 0

    for act in actions:
        period = int(act.get("period", 1))
        clk_str = act.get("clock", "PT12M00.00S")
        clk_sec = parse_clock_to_seconds(clk_str)

        if period <= 4:
            sec_rem = (4 - period) * 720.0 + clk_sec
        else:
            sec_rem = clk_sec

        elapsed_sec = 2880.0 - sec_rem

        # Check score updates
        s_home_str = act.get("scoreHome")
        s_away_str = act.get("scoreAway")
        if s_home_str is not None and s_home_str != "":
            current_home_score = int(s_home_str)
        if s_away_str is not None and s_away_str != "":
            current_away_score = int(s_away_str)

        margin = current_home_score - current_away_score

        # Check substitutions
        act_type = act.get("actionType", "")
        sub_type = act.get("subType", "")
        person_id = act.get("personId", 0)
        team_id = act.get("teamId", 0)

        if act_type == "substitution":
            if team_id == home_team_id:
                if sub_type == "out" and person_id in current_home_lineup:
                    current_home_lineup.remove(person_id)
                elif sub_type == "in":
                    current_home_lineup.add(person_id)
            elif team_id == away_team_id:
                if sub_type == "out" and person_id in current_away_lineup:
                    current_away_lineup.remove(person_id)
                elif sub_type == "in":
                    current_away_lineup.add(person_id)

        # Win probability calculation
        is_home_poss = 1 if act.get("possession") == home_team_id or team_id == home_team_id else 0
        wp = win_model.predict_win_probability(
            score_margin=margin,
            seconds_remaining=sec_rem,
            period=period,
            possession_home=is_home_poss,
        )
        wp = round(float(wp), 4)
        wpa = round(wp - prev_wp, 4)
        prev_wp = wp

        # Shot xeFG% calculation
        x_efg = None
        smoe = None
        is_fg = act.get("isFieldGoal", 0)
        if is_fg == 1 or act_type in ["2pt", "3pt"]:
            shot_dist = float(act.get("shotDistance") or 15.0)
            shot_x = float(act.get("x") or 0.0)
            shot_y = float(act.get("y") or 15.0)
            is_3 = 1 if act_type == "3pt" else 0
            p_make = float(shot_model.predict_proba(
                shot_x=[shot_x],
                shot_y=[shot_y],
                shot_dist=[shot_dist],
                period=[period],
                clock_seconds=[clk_sec],
                is_3pt=[is_3],
            )[0])
            val = 3.0 if is_3 else 2.0
            x_efg = round((val * p_make) / 2.0, 3)
            shot_made = 1 if act.get("shotResult") == "Made" else 0
            actual_efg = 1.5 if (is_3 and shot_made) else (1.0 if shot_made else 0.0)
            smoe = round(actual_efg - x_efg, 3)

        ev_dict = {
            "actionNumber": act.get("actionNumber"),
            "period": period,
            "clock": clk_str,
            "secondsRemaining": round(sec_rem, 1),
            "elapsedSeconds": round(elapsed_sec, 1),
            "minute": min(48, max(1, int(elapsed_sec // 60) + 1)),
            "actionType": act_type,
            "subType": sub_type,
            "descriptor": act.get("descriptor", ""),
            "teamId": team_id,
            "teamTricode": act.get("teamTricode", ""),
            "personId": person_id,
            "playerName": act.get("playerNameI") or act.get("playerName", ""),
            "description": act.get("description", ""),
            "scoreHome": current_home_score,
            "scoreAway": current_away_score,
            "scoreMargin": margin,
            "homeWinProb": wp,
            "wpa": wpa,
            "shotResult": act.get("shotResult"),
            "shotDistance": act.get("shotDistance"),
            "xeFG": x_efg,
            "smoe": smoe,
            "shotArea": act.get("area"),
            "shotAreaDetail": act.get("areaDetail"),
            "homeLineup": list(current_home_lineup),
            "awayLineup": list(current_away_lineup),
        }
        processed_events.append(ev_dict)
        margin_history.append({
            "elapsed": elapsed_sec,
            "margin": margin,
            "home_score": current_home_score,
            "away_score": current_away_score,
            "wp": wp,
            "event": ev_dict,
        })

    # Generate 48 Minute Candlesticks
    candlesticks: List[Dict[str, Any]] = []
    last_close = 0
    last_wp = 0.525

    for m in range(1, 49):
        m_start_sec = (m - 1) * 60.0
        m_end_sec = m * 60.0

        # Events that occurred within [m_start_sec, m_end_sec]
        m_events = [e for e in processed_events if m_start_sec <= e["elapsedSeconds"] < m_end_sec]

        period = (m - 1) // 12 + 1
        min_in_period = ((m - 1) % 12) + 1
        clock_start_min = 12 - (min_in_period - 1)
        clock_end_min = 12 - min_in_period
        clock_label = f"Q{period} {clock_start_min:02d}:00-{clock_end_min:02d}:00"

        if m_events:
            open_val = last_close
            margins = [e["scoreMargin"] for e in m_events]
            high_val = max([open_val] + margins)
            low_val = min([open_val] + margins)
            close_val = m_events[-1]["scoreMargin"]

            # Points scored in this minute
            start_h = m_events[0]["scoreHome"]
            end_h = m_events[-1]["scoreHome"]
            start_a = m_events[0]["scoreAway"]
            end_a = m_events[-1]["scoreAway"]

            # Key play (largest absolute WPA in minute)
            key_ev = max(m_events, key=lambda x: abs(x.get("wpa") or 0.0))
            key_desc = key_ev.get("description", "")
            minute_wp = m_events[-1]["homeWinProb"]
        else:
            open_val = last_close
            high_val = last_close
            low_val = last_close
            close_val = last_close
            start_h = end_h = 0
            start_a = end_a = 0
            key_desc = "Scoreless stint / possession grind"
            minute_wp = last_wp

        # Refined points scored calculation by counting made baskets/FTs in m_events
        h_pts_scored = 0
        a_pts_scored = 0
        for ev in m_events:
            desc = ev["description"].lower()
            tid = ev.get("teamId")
            # If made FG or FT
            if "3pt" in ev["actionType"].lower() and ev.get("shotResult") == "Made":
                pts = 3
            elif "2pt" in ev["actionType"].lower() and ev.get("shotResult") == "Made":
                pts = 2
            elif "freethrow" in ev["actionType"].lower() and ev.get("shotResult") == "Made":
                pts = 1
            else:
                pts = 0

            if pts > 0:
                if tid == home_team_id:
                    h_pts_scored += pts
                elif tid == away_team_id:
                    a_pts_scored += pts

        vol = h_pts_scored + a_pts_scored
        is_bullish = close_val >= open_val

        # Momentum tag
        if h_pts_scored >= 6 and a_pts_scored == 0:
            momentum = f"IND +{h_pts_scored} Run"
        elif a_pts_scored >= 6 and h_pts_scored == 0:
            momentum = f"CLE +{a_pts_scored} Run"
        elif (open_val * close_val < 0) or (open_val != 0 and close_val == 0):
            momentum = "Lead Change / Tie"
        elif vol >= 8:
            momentum = "High Scoring Track Meet"
        elif vol == 0:
            momentum = "Defensive Lockdown"
        elif is_bullish:
            momentum = "IND Surge"
        else:
            momentum = "CLE Rally"

        candle = {
            "minute": m,
            "period": period,
            "minuteInPeriod": min_in_period,
            "clockLabel": clock_label,
            "open": open_val,
            "high": high_val,
            "low": low_val,
            "close": close_val,
            "volume": vol,
            "homePoints": h_pts_scored,
            "awayPoints": a_pts_scored,
            "homeWinProb": minute_wp,
            "isBullish": is_bullish,
            "keyPlay": key_desc,
            "momentum": momentum,
            "eventCount": len(m_events),
        }
        candlesticks.append(candle)
        last_close = close_val
        last_wp = minute_wp

    # Final live payload structure
    feed_payload = {
        "gameId": game_meta.get("gameId", "0022300001"),
        "gameCode": game_meta.get("gameCode", "20231103/CLEIND"),
        "gameStatusText": "FINAL",
        "gameStatus": 3,
        "arena": game_meta.get("arena", {}).get("arenaName", "Gainbridge Fieldhouse"),
        "homeTeam": {
            "teamId": home_team_id,
            "name": home_team.get("teamName", "Pacers"),
            "city": home_team.get("teamCity", "Indiana"),
            "tricode": home_team.get("teamTricode", "IND"),
            "score": home_team.get("score", 121),
            "color": "#002D62",
            "accentColor": "#FDBB30",
            "periods": home_team.get("periods", []),
            "statistics": home_team.get("statistics", {}),
            "starters": home_starters,
            "players": [
                {
                    "personId": p["personId"],
                    "name": p["name"],
                    "jerseyNum": p["jerseyNum"],
                    "position": p.get("position", "G"),
                    "points": p.get("statistics", {}).get("points", 0),
                    "rebounds": p.get("statistics", {}).get("reboundsTotal", 0),
                    "assists": p.get("statistics", {}).get("assists", 0),
                    "steals": p.get("statistics", {}).get("steals", 0),
                    "blocks": p.get("statistics", {}).get("blocks", 0),
                    "plusMinus": p.get("statistics", {}).get("plusMinusPoints", 0),
                    "minutes": p.get("statistics", {}).get("minutesCalculated", "PT00M").replace("PT", "").replace("M", "m"),
                    "fgPct": round(p.get("statistics", {}).get("fieldGoalsPercentage", 0.0) * 100, 1),
                    "fg3Pct": round(p.get("statistics", {}).get("threePointersPercentage", 0.0) * 100, 1),
                    "starter": str(p.get("starter")) == "1",
                }
                for p in home_players if p.get("played") == "1"
            ],
        },
        "awayTeam": {
            "teamId": away_team_id,
            "name": away_team.get("teamName", "Cavaliers"),
            "city": away_team.get("teamCity", "Cleveland"),
            "tricode": away_team.get("teamTricode", "CLE"),
            "score": away_team.get("score", 116),
            "color": "#860038",
            "accentColor": "#FDBB30",
            "periods": away_team.get("periods", []),
            "statistics": away_team.get("statistics", {}),
            "starters": away_starters,
            "players": [
                {
                    "personId": p["personId"],
                    "name": p["name"],
                    "jerseyNum": p["jerseyNum"],
                    "position": p.get("position", "G"),
                    "points": p.get("statistics", {}).get("points", 0),
                    "rebounds": p.get("statistics", {}).get("reboundsTotal", 0),
                    "assists": p.get("statistics", {}).get("assists", 0),
                    "steals": p.get("statistics", {}).get("steals", 0),
                    "blocks": p.get("statistics", {}).get("blocks", 0),
                    "plusMinus": p.get("statistics", {}).get("plusMinusPoints", 0),
                    "minutes": p.get("statistics", {}).get("minutesCalculated", "PT00M").replace("PT", "").replace("M", "m"),
                    "fgPct": round(p.get("statistics", {}).get("fieldGoalsPercentage", 0.0) * 100, 1),
                    "fg3Pct": round(p.get("statistics", {}).get("threePointersPercentage", 0.0) * 100, 1),
                    "starter": str(p.get("starter")) == "1",
                }
                for p in away_players if p.get("played") == "1"
            ],
        },
        "candlesticks": candlesticks,
        "playByPlay": processed_events,
        "clutchPlays": [e for e in processed_events if abs(e.get("wpa") or 0.0) >= 0.04 or (e.get("minute") >= 44 and e.get("shotResult") == "Made")],
        "totalPlays": len(processed_events),
        "totalCandles": len(candlesticks),
    }

    # Also build a scoreboard list with 4 games for switching
    scoreboard_payload = {
        "games": [
            {
                "gameId": "0022300001",
                "gameStatus": 3,
                "gameStatusText": "FINAL (Thriller)",
                "period": 4,
                "gameClock": "00:00",
                "homeTeam": {"tricode": "IND", "name": "Pacers", "score": 121, "record": "47-35"},
                "awayTeam": {"tricode": "CLE", "name": "Cavaliers", "score": 116, "record": "48-34"},
                "leadChanges": 10,
                "timesTied": 4,
                "biggestLead": 18,
                "isFeatured": True,
            },
            {
                "gameId": "0022300002",
                "gameStatus": 2,
                "gameStatusText": "4th Qtr 1:44",
                "period": 4,
                "gameClock": "01:44",
                "homeTeam": {"tricode": "BOS", "name": "Celtics", "score": 114, "record": "64-18"},
                "awayTeam": {"tricode": "NYK", "name": "Knicks", "score": 109, "record": "50-32"},
                "leadChanges": 8,
                "timesTied": 6,
                "biggestLead": 11,
                "isFeatured": False,
            },
            {
                "gameId": "0022300003",
                "gameStatus": 2,
                "gameStatusText": "4th Qtr 3:12",
                "period": 4,
                "gameClock": "03:12",
                "homeTeam": {"tricode": "DEN", "name": "Nuggets", "score": 108, "record": "57-25"},
                "awayTeam": {"tricode": "MIN", "name": "Timberwolves", "score": 105, "record": "56-26"},
                "leadChanges": 14,
                "timesTied": 9,
                "biggestLead": 8,
                "isFeatured": False,
            },
            {
                "gameId": "0022300004",
                "gameStatus": 3,
                "gameStatusText": "FINAL (OT)",
                "period": 5,
                "gameClock": "00:00",
                "homeTeam": {"tricode": "LAL", "name": "Lakers", "score": 118, "record": "47-35"},
                "awayTeam": {"tricode": "GSW", "name": "Warriors", "score": 115, "record": "46-36"},
                "leadChanges": 12,
                "timesTied": 7,
                "biggestLead": 9,
                "isFeatured": False,
            },
        ]
    }

    # Save to frontend static bundles
    out_dirs = [
        Path("frontend/public/data"),
        Path("frontend/lib/static-data"),
    ]
    for od in out_dirs:
        od.mkdir(parents=True, exist_ok=True)
        with open(od / "live_game_feed.json", "w", encoding="utf-8") as f:
            json.dump(feed_payload, f, indent=2)
        with open(od / "live_scoreboard.json", "w", encoding="utf-8") as f:
            json.dump(scoreboard_payload, f, indent=2)

    print(f"[OK] Generated Live Game Feed: {len(candlesticks)} candles, {len(processed_events)} plays.")
    print(f"[OK] Saved to: {[str(d) for d in out_dirs]}")


if __name__ == "__main__":
    generate_live_game_feed()
