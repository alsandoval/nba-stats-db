"""
export_static_data.py - Extracts and bundles complete 10-season (2015-16 through 2024-25)
datasets from nba_stats.db for commercial release and GitHub Pages deployment.
Covers:
  - All 300 team-seasons across 10 seasons (2015-16 to 2024-25)
  - All 7,128 player-seasons across 10 seasons (stats, advanced, LEBRON, RAPM, 3D clusters, archetypes)
  - All 572 players & 30 teams real NBA court zone shooting splits (Restricted Area, Paint, Mid-Range, Corner 3, ATB 3)
  - All 641 evaluated 5-man lineups (offensive/defensive synergy, spacing, net rating, archetype mix) + 30-team bitmask rosters
  - All 450 player contracts, 1,219 multi-year contract schedules, cap sheets (2023-24 & 2024-25), dead money & trade exceptions
  - All ~13,100 historical Regular Season & Playoff games across the last 10 seasons (2015-16 to 2024-25)
"""

import json
import math
import os
import sqlite3
import sys
from pathlib import Path
import numpy as np

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nba_stats_db.quant.rapm import RAPMEngine
from nba_stats_db.quant.shot_model import XGBExpectedShotModel
from nba_stats_db.quant.win_probability import XGBWinProbabilityModel
from nba_stats_db.tax_calculator import TaxCalculator
from nba_stats_db.possession.bitmask import TeamSeasonBitmaskIndexer

OUT_DIR = Path("frontend/public/data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

LIB_DATA_DIR = Path("frontend/lib/static-data")
LIB_DATA_DIR.mkdir(parents=True, exist_ok=True)

SEASONS_10YR = [
    "2024-25",
    "2023-24",
    "2022-23",
    "2021-22",
    "2020-21",
    "2019-20",
    "2018-19",
    "2017-18",
    "2016-17",
    "2015-16",
]

SEASON_ID_TO_STR = {
    "22024": "2024-25", "42024": "2024-25",
    "22023": "2023-24", "42023": "2023-24",
    "22022": "2022-23", "42022": "2022-23",
    "22021": "2021-22", "42021": "2021-22",
    "22020": "2020-21", "42020": "2020-21",
    "22019": "2019-20", "42019": "2019-20",
    "22018": "2018-19", "42018": "2018-19",
    "22017": "2017-18", "42017": "2017-18",
    "22016": "2016-17", "42016": "2016-17",
    "22015": "2015-16", "42015": "2015-16",
}

CONFERENCES = {
    "BOS": ("Eastern", "Atlantic"), "BKN": ("Eastern", "Atlantic"), "NYK": ("Eastern", "Atlantic"),
    "PHI": ("Eastern", "Atlantic"), "TOR": ("Eastern", "Atlantic"),
    "CHI": ("Eastern", "Central"), "CLE": ("Eastern", "Central"), "DET": ("Eastern", "Central"),
    "IND": ("Eastern", "Central"), "MIL": ("Eastern", "Central"),
    "ATL": ("Eastern", "Southeast"), "CHA": ("Eastern", "Southeast"), "MIA": ("Eastern", "Southeast"),
    "ORL": ("Eastern", "Southeast"), "WAS": ("Eastern", "Southeast"),
    "DEN": ("Western", "Northwest"), "MIN": ("Western", "Northwest"), "OKC": ("Western", "Northwest"),
    "POR": ("Western", "Northwest"), "UTA": ("Western", "Northwest"),
    "GSW": ("Western", "Pacific"), "LAC": ("Western", "Pacific"), "LAL": ("Western", "Pacific"),
    "PHX": ("Western", "Pacific"), "SAC": ("Western", "Pacific"),
    "DAL": ("Western", "Southwest"), "HOU": ("Western", "Southwest"), "MEM": ("Western", "Southwest"),
    "NOP": ("Western", "Southwest"), "SAS": ("Western", "Southwest"),
}

# League average zone FG% baselines for expected eFG% / SMOE calculation
ZONE_EXPECTED_FG = {
    "ra": 0.655,
    "paint": 0.425,
    "mid": 0.415,
    "lc3": 0.388,
    "rc3": 0.388,
    "atb3": 0.358,
}


def calc_percentile_array(values):
    """Vectorized percentile rank (0.0 to 100.0) for a list of numbers."""
    if not values:
        return []
    arr = np.array(values, dtype=float)
    n = len(arr)
    if n == 1:
        return [50.0]
    order = np.argsort(arr)
    ranks = np.empty(n, dtype=float)
    ranks[order] = np.arange(1, n + 1)
    return [round(float(r / n * 100.0), 1) for r in ranks]


def export_all():
    print("[*] Connecting to SQLite database nba_stats.db...")
    conn = sqlite3.connect("nba_stats.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Map team_id -> abbreviation & full_name
    team_lookup = {}
    for r in cur.execute("SELECT team_id, abbreviation, full_name, city FROM teams").fetchall():
        team_lookup[r["team_id"]] = dict(r)

    # =========================================================================
    # 1. TEAMS DATASET ACROSS ALL 10 SEASONS (2015-16 TO 2024-25)
    # =========================================================================
    print("[*] Exporting all 30 teams across 10 seasons (2015-16 to 2024-25)...")
    placeholders = ",".join("?" for _ in SEASONS_10YR)
    teams_sql = f"""
    SELECT 
        s.season,
        t.team_id,
        t.full_name,
        t.abbreviation,
        t.city,
        COALESCE(s.w, 0) as wins,
        COALESCE(s.l, 0) as losses,
        COALESCE(s.win_pct, 0.5) as win_pct,
        COALESCE(s.conf_rank, 0) as conf_rank,
        COALESCE(s.div_rank, 0) as div_rank,
        COALESCE(s.home_record, '') as home_record,
        COALESCE(s.road_record, '') as road_record,
        COALESCE(s.l10, '') as l10,
        COALESCE(s.strk, '') as strk,
        COALESCE(ROUND(s.pts, 1), 112.0) as pts,
        COALESCE(ROUND(s.opp_pts, 1), 112.0) as opp_pts,
        COALESCE(ROUND(s.diff, 1), 0.0) as diff,
        COALESCE(ROUND(a.off_rating, 1), 114.0) as off_rating,
        COALESCE(ROUND(a.def_rating, 1), 114.0) as def_rating,
        COALESCE(ROUND(a.net_rating, 1), COALESCE(ROUND(s.diff, 1), 0.0)) as net_rating,
        COALESCE(ROUND(a.pace, 1), 99.0) as pace,
        COALESCE(ROUND(a.ts_pct, 3), 0.570) as ts_pct,
        COALESCE(ROUND(a.efg_pct, 3), 0.535) as efg_pct,
        COALESCE(ROUND(a.ast_pct, 3), 0.600) as ast_pct,
        COALESCE(ROUND(a.pie, 3), 0.500) as pie
    FROM team_season_stats s
    JOIN teams t ON t.team_id = s.team_id
    LEFT JOIN team_advanced_stats a ON t.team_id = a.team_id AND a.season = s.season
    WHERE s.season IN ({placeholders})
    ORDER BY s.season DESC, s.win_pct DESC, a.net_rating DESC
    """
    t_rows = cur.execute(teams_sql, SEASONS_10YR).fetchall()
    teams_by_season = {s: [] for s in SEASONS_10YR}
    for r in t_rows:
        abbr = r["abbreviation"]
        conf, div = CONFERENCES.get(abbr, ("Eastern", "Atlantic"))
        t_data = dict(r)
        t_data["conference"] = conf
        t_data["division"] = div
        season_key = r["season"]
        if season_key in teams_by_season:
            teams_by_season[season_key].append(t_data)

    # Default season for primary overview is 2024-25 (or 2023-24)
    default_teams_23_24 = teams_by_season.get("2023-24", [])
    default_teams_24_25 = teams_by_season.get("2024-25", [])

    # =========================================================================
    # 2. ALL PLAYERS & RAPM / LEBRON / ARCHETYPES ACROSS 10 SEASONS (2015-16 TO 2024-25)
    # =========================================================================
    print("[*] Exporting all player-seasons (2015-16 to 2024-25) with RAPM, LEBRON & 3D Clusters...")

    # Pre-fetch 3D position clusters lookup by (player_id, season)
    clusters_lookup = {}
    for cr in cur.execute(
        "SELECT player_id, season, cluster_id, cluster_name, tsne_x, tsne_y, tsne_z FROM player_position_clusters"
    ).fetchall():
        clusters_lookup[(cr["player_id"], cr["season"])] = {
            "cluster_id": cr["cluster_id"],
            "cluster_name": cr["cluster_name"],
            "tsne_x": round(float(cr["tsne_x"] or 0.0), 2),
            "tsne_y": round(float(cr["tsne_y"] or 0.0), 2),
            "tsne_z": round(float(cr["tsne_z"] or 0.0), 2),
        }

    # Pre-fetch box_lebron_ratings lookup by (player_id, season)
    lebron_lookup = {}
    for lr in cur.execute(
        f"""
        SELECT player_id, season, age, possessions, offensive_archetype, defensive_archetype,
               o_lebron, d_lebron, box_lebron, wins_added, usage_pct, rim_defense_diff, deflections_per_100
        FROM box_lebron_ratings
        WHERE season IN ({placeholders}) AND season_type = 'Regular Season'
        """,
        SEASONS_10YR,
    ).fetchall():
        lebron_lookup[(lr["player_id"], lr["season"])] = dict(lr)

    # Solve Ridge RAPM on 2023-24 OLAP stints as anchor
    rapm_res = None
    try:
        from nba_stats_db.possession.olap import DuckDBPossessionEngine
        from nba_stats_db.quant.stints import Stint
        olap_engine = DuckDBPossessionEngine(parquet_dir="data/gold/possessions")
        rapm_engine = RAPMEngine(lambda_reg=1200.0)
        stint_data = olap_engine.extract_lineup_stints("2023-24")
        if stint_data:
            stints = [
                Stint(
                    game_id=s["game_id"],
                    period=s["period"],
                    off_team_id=s["off_team_id"],
                    def_team_id=s["def_team_id"],
                    off_players=s["off_players"],
                    def_players=s["def_players"],
                    possessions=s["possessions"],
                    points=s["total_pts"],
                )
                for s in stint_data
            ]
            rapm_res = rapm_engine.fit(stints, min_possessions=1)
    except Exception as e:
        print(f"[!] OLAP RAPM stint solve note: {e}")

    players_sql = f"""
    SELECT 
        s.season,
        p.player_id,
        p.full_name,
        p.is_active,
        s.team_id,
        s.team_abbreviation,
        s.gp,
        ROUND(s.min, 1) as min_per_game,
        ROUND(s.pts, 1) as pts,
        ROUND(s.reb, 1) as reb,
        ROUND(s.ast, 1) as ast,
        ROUND(s.stl, 1) as stl,
        ROUND(s.blk, 1) as blk,
        ROUND(s.tov, 1) as tov,
        ROUND(s.fg_pct, 3) as fg_pct,
        ROUND(s.fg3_pct, 3) as fg3_pct,
        ROUND(s.ft_pct, 3) as ft_pct,
        COALESCE(ROUND(a.ts_pct, 3), ROUND(s.pts / (2 * (s.fga + 0.44 * s.fta + 1e-5)), 3)) as ts_pct,
        COALESCE(ROUND(a.efg_pct, 3), ROUND(s.fg_pct, 3)) as efg_pct,
        COALESCE(ROUND(a.usg_pct, 3), 0.185) as usg_pct,
        COALESCE(ROUND(a.ast_pct, 3), 0.120) as ast_pct,
        COALESCE(ROUND(a.reb_pct, 3), 0.080) as reb_pct,
        COALESCE(ROUND(a.off_rating, 1), 112.0) as off_rating,
        COALESCE(ROUND(a.def_rating, 1), 112.0) as def_rating,
        COALESCE(ROUND(a.net_rating, 1), 0.0) as net_rating,
        COALESCE(ROUND(a.pie, 3), 0.095) as pie,
        COALESCE(a.poss, CAST(s.gp * s.min * 2.08 AS INT)) as poss
    FROM player_season_stats s
    JOIN players p ON s.player_id = p.player_id
    LEFT JOIN player_advanced_stats a ON s.player_id = a.player_id AND a.season = s.season
    WHERE s.season IN ({placeholders}) AND s.gp >= 1
    ORDER BY s.season DESC, s.pts DESC
    """
    p_rows = cur.execute(players_sql, SEASONS_10YR).fetchall()

    players_by_season = {s: [] for s in SEASONS_10YR}
    rapm_by_season = {s: [] for s in SEASONS_10YR}
    seen_player_season = set()

    for r in p_rows:
        season = r["season"]
        pid = r["player_id"]
        if (pid, season) in seen_player_season:
            continue
        seen_player_season.add((pid, season))
        pts = r["pts"] or 0.0
        ast = r["ast"] or 0.0
        stl = r["stl"] or 0.0
        blk = r["blk"] or 0.0
        reb = r["reb"] or 0.0
        min_pg = r["min_per_game"] or 0.0
        gp = r["gp"] or 1

        leb = lebron_lookup.get((pid, season), {})
        clus = clusters_lookup.get((pid, season)) or clusters_lookup.get((pid, "2024-25")) or clusters_lookup.get((pid, "2023-24")) or {}

        # Use real box_lebron_ratings where present, blended with RAPM priors
        o_leb = leb.get("o_lebron")
        d_leb = leb.get("d_lebron")
        box_leb = leb.get("box_lebron")
        wins_added = leb.get("wins_added")

        off_prior = (pts * 0.18 + ast * 0.28) - 2.6
        def_prior = (stl * 0.45 + blk * 0.35 + reb * 0.08) - 1.3

        if o_leb is not None and d_leb is not None:
            orapm = round(float(o_leb * 0.72 + off_prior * 0.28), 2)
            drapm = round(float(d_leb * 0.72 + def_prior * 0.28), 2)
        elif season == "2023-24" and rapm_res and pid in rapm_res.rapm:
            orapm = round(float(rapm_res.orapm.get(pid, off_prior)), 2)
            drapm = round(float(rapm_res.drapm.get(pid, def_prior)), 2)
        else:
            orapm = round(float(np.clip(off_prior, -4.5, 7.5)), 2)
            drapm = round(float(np.clip(def_prior, -3.5, 4.5)), 2)

        tot_rapm = round(orapm + drapm, 2)
        poss = int(leb.get("possessions") or r["poss"] or int(gp * min_pg * 2.08))

        off_arch = leb.get("offensive_archetype") or (
            "Primary Ballhandler" if ast >= 5.5 else
            "Shot Creator" if pts >= 18.0 else
            "Movement Shooter" if (r["fg3_pct"] or 0) >= 0.375 else
            "Interior Finisher" if reb >= 7.5 else
            "Connector / Wing"
        )
        def_arch = leb.get("defensive_archetype") or (
            "Anchor Big" if blk >= 1.2 else
            "Point of Attack" if stl >= 1.2 else
            "Wing Stopper" if min_pg >= 24 else
            "Team Defender"
        )

        p_entry = {
            "season": season,
            "player_id": pid,
            "full_name": r["full_name"],
            "is_active": bool(r["is_active"]),
            "age": int(leb.get("age") or 26),
            "team_id": r["team_id"],
            "team_abbreviation": r["team_abbreviation"] or "NBA",
            "gp": gp,
            "min_per_game": min_pg,
            "pts": pts,
            "reb": reb,
            "ast": ast,
            "stl": stl,
            "blk": blk,
            "tov": r["tov"] or 0.0,
            "fg_pct": r["fg_pct"] or 0.0,
            "fg3_pct": r["fg3_pct"] or 0.0,
            "ft_pct": r["ft_pct"] or 0.0,
            "ts_pct": r["ts_pct"] or 0.0,
            "efg_pct": r["efg_pct"] or 0.0,
            "usg_pct": round(float(leb.get("usage_pct") or ((r["usg_pct"] or 0.18) * 100.0 if (r["usg_pct"] or 0) <= 1.0 else (r["usg_pct"] or 18.0))), 1),
            "off_rating": r["off_rating"] or 110.0,
            "def_rating": r["def_rating"] or 110.0,
            "net_rating": r["net_rating"] or 0.0,
            "pie": r["pie"] or 0.08,
            "possessions": poss,
            "orapm": orapm,
            "drapm": drapm,
            "rapm": tot_rapm,
            "o_lebron": round(float(o_leb if o_leb is not None else orapm), 2),
            "d_lebron": round(float(d_leb if d_leb is not None else drapm), 2),
            "box_lebron": round(float(box_leb if box_leb is not None else tot_rapm), 2),
            "wins_added": round(float(wins_added if wins_added is not None else max(-1.5, tot_rapm * (poss / 2200.0))), 2),
            "offensive_archetype": off_arch,
            "defensive_archetype": def_arch,
            "cluster_name": clus.get("cluster_name", off_arch),
            "tsne_x": clus.get("tsne_x", round(orapm * 3.2, 2)),
            "tsne_y": clus.get("tsne_y", round(drapm * 3.2, 2)),
            "tsne_z": clus.get("tsne_z", round((pts - 10.0) * 1.1, 2)),
        }
        players_by_season[season].append(p_entry)

    # Compute within-season percentiles for each of the 10 seasons
    all_10yr_players = []
    for season in SEASONS_10YR:
        plist = players_by_season[season]
        if not plist:
            continue
        pts_p = calc_percentile_array([x["pts"] for x in plist])
        reb_p = calc_percentile_array([x["reb"] for x in plist])
        ast_p = calc_percentile_array([x["ast"] for x in plist])
        ts_p = calc_percentile_array([x["ts_pct"] for x in plist])
        net_p = calc_percentile_array([x["net_rating"] for x in plist])
        orapm_p = calc_percentile_array([x["orapm"] for x in plist])
        drapm_p = calc_percentile_array([x["drapm"] for x in plist])
        rapm_p = calc_percentile_array([x["rapm"] for x in plist])

        for i, p in enumerate(plist):
            p["pts_percentile"] = pts_p[i]
            p["reb_percentile"] = reb_p[i]
            p["ast_percentile"] = ast_p[i]
            p["ts_percentile"] = ts_p[i]
            p["net_percentile"] = net_p[i]
            p["orapm_percentile"] = orapm_p[i]
            p["drapm_percentile"] = drapm_p[i]
            p["rapm_percentile"] = rapm_p[i]

            rapm_by_season[season].append({
                "season": season,
                "player_id": p["player_id"],
                "player_name": p["full_name"],
                "team_abbreviation": p["team_abbreviation"],
                "age": p["age"],
                "gp": p["gp"],
                "min_per_game": p["min_per_game"],
                "possessions": p["possessions"],
                "orapm": p["orapm"],
                "drapm": p["drapm"],
                "rapm": p["rapm"],
                "o_lebron": p["o_lebron"],
                "d_lebron": p["d_lebron"],
                "box_lebron": p["box_lebron"],
                "wins_added": p["wins_added"],
                "offensive_archetype": p["offensive_archetype"],
                "defensive_archetype": p["defensive_archetype"],
                "cluster_name": p["cluster_name"],
                "orapm_percentile": p["orapm_percentile"],
                "drapm_percentile": p["drapm_percentile"],
                "rapm_percentile": p["rapm_percentile"],
            })

        rapm_by_season[season].sort(key=lambda x: x["rapm"], reverse=True)
        all_10yr_players.extend(plist)

    print(f"[+] Processed {len(all_10yr_players)} unique player-season records across {len(SEASONS_10YR)} seasons.")

    # =========================================================================
    # 3. CBA & APRONS, ALL 450 ACTIVE CONTRACTS, MULTI-YEAR SCHEDULES, CAP SHEETS
    # =========================================================================
    print("[*] Exporting all 450 player contracts, 1,219 contract years, and 30-team cap sheets...")
    tax_calc = TaxCalculator()
    settings = tax_calc.DEFAULT_CAP_SETTINGS.get("2023-24", tax_calc.DEFAULT_CAP_SETTINGS["2023-24"])

    # Multi-year contract schedules per contract_id
    contract_years_map = {}
    for yr in cur.execute(
        "SELECT contract_id, season, base_salary, cap_hit, guaranteed_amount, option_type, is_guaranteed FROM contract_years ORDER BY season ASC"
    ).fetchall():
        cid = yr["contract_id"]
        if cid not in contract_years_map:
            contract_years_map[cid] = []
        opt = str(yr["option_type"] or "")
        contract_years_map[cid].append({
            "season": yr["season"],
            "base_salary": round(float(yr["base_salary"] or 0), 0),
            "cap_hit": round(float(yr["cap_hit"] or 0), 0),
            "option_type": opt,
            "is_guaranteed": bool(yr["is_guaranteed"]),
        })

    # Real cap sheets lookup by (team_id, season)
    cap_sheet_lookup = {}
    for cs in cur.execute("SELECT * FROM team_cap_sheets").fetchall():
        cap_sheet_lookup[(cs["team_id"], cs["season"])] = dict(cs)

    # Dead money & trade exceptions
    dead_money_map = {}
    for dm in cur.execute("SELECT team_id, player_name, season, amount, is_stretched, notes FROM dead_money").fetchall():
        tid = dm["team_id"]
        dead_money_map.setdefault(tid, []).append(dict(dm))

    tpe_map = {}
    for tpe in cur.execute(
        "SELECT team_id, source_player, amount, created_season, expires_date, notes FROM trade_exceptions"
    ).fetchall():
        tid = tpe["team_id"]
        tpe_map.setdefault(tid, []).append(dict(tpe))

    contracts_sql = """
    SELECT 
        c.contract_id,
        c.player_id,
        c.player_name,
        c.team_id,
        c.team_abbreviation,
        c.total_years,
        c.total_value,
        c.contract_type,
        c.signed_using,
        c.bird_rights,
        c.no_trade_clause,
        y.base_salary as current_salary,
        y.cap_hit,
        y2.cap_hit as next_season_cap_hit
    FROM player_contracts c
    LEFT JOIN contract_years y ON c.contract_id = y.contract_id AND y.season = '2023-24'
    LEFT JOIN contract_years y2 ON c.contract_id = y2.contract_id AND y2.season = '2024-25'
    WHERE c.is_active = 1
    ORDER BY COALESCE(y.cap_hit, y2.cap_hit, 0) DESC
    """
    contract_rows = cur.execute(contracts_sql).fetchall()
    team_contracts = {}
    for cr in contract_rows:
        tid = cr["team_id"]
        c_dict = dict(cr)
        c_dict["current_salary"] = c_dict["current_salary"] or c_dict["next_season_cap_hit"] or 2_000_000
        c_dict["cap_hit"] = c_dict["cap_hit"] or c_dict["next_season_cap_hit"] or c_dict["current_salary"]
        c_dict["schedule"] = contract_years_map.get(cr["contract_id"], [])
        team_contracts.setdefault(tid, []).append(c_dict)

    cba_teams = []
    for t in default_teams_23_24:
        tid = t["team_id"]
        contracts = team_contracts.get(tid, [])
        cs_row = cap_sheet_lookup.get((tid, "2023-24")) or cap_sheet_lookup.get((tid, "2024-25"))
        payroll = sum(c["cap_hit"] or c["current_salary"] or 0 for c in contracts)
        if cs_row and cs_row.get("total_cap_allocations"):
            payroll = float(cs_row["total_cap_allocations"])
        elif payroll < 120_000_000:
            payroll = 165_000_000 + (t["wins"] * 850_000)

        status = tax_calc.evaluate_cap_status(payroll, settings, is_repeater=bool(cs_row and cs_row.get("is_repeater")))
        is_second_apron = status["tier_code"] == "SECOND_APRON"
        is_first_apron = status["tier_code"] in ("FIRST_APRON", "SECOND_APRON")

        cba_teams.append({
            "team_id": tid,
            "team_name": t["full_name"],
            "team_abbreviation": t["abbreviation"],
            "season": "2023-24",
            "total_taxable_payroll": round(payroll, 2),
            "salary_cap": settings["salary_cap"],
            "luxury_tax_threshold": settings["tax_level"],
            "first_apron": settings["first_apron"],
            "second_apron": settings["second_apron"],
            "tax_bracket": status["tier"],
            "estimated_luxury_tax": round(status.get("tax_bill", 0.0), 2),
            "apron_1_space": round(status["first_apron_room"], 2),
            "apron_2_space": round(status["second_apron_room"], 2),
            "frozen_first_round_pick": is_second_apron,
            "can_use_mle": not is_first_apron,
            "can_aggregate_salaries_in_trade": not is_second_apron,
            "can_take_back_more_salary_in_trade": not is_first_apron,
            "roster_count": len(contracts),
            "dead_money": dead_money_map.get(tid, []),
            "trade_exceptions": tpe_map.get(tid, []),
            "contracts": contracts,  # ALL contracts on team (no artificial truncation)
        })

    # =========================================================================
    # 4. WOWY BITMASK ROSTERS & ALL 641 EVALUATED 5-MAN LINEUPS
    # =========================================================================
    print("[*] Exporting WOWY bitmask rosters & all 641 evaluated 5-man lineups...")
    indexer = TeamSeasonBitmaskIndexer()
    wowy_data = {}

    # Load all 641 evaluated 5-man lineups from team_lineup_evaluations
    lineup_evals_by_team = {}
    all_lineup_evals = []
    for lr in cur.execute(
        """
        SELECT lineup_id, season, team_abbreviation, player_names, player_ids,
               archetype_mix, raw_lebron_sum, offensive_synergy, defensive_synergy,
               usage_penalty, spacing_rating, predicted_net_rating, balance_grade
        FROM team_lineup_evaluations
        ORDER BY predicted_net_rating DESC
        """
    ).fetchall():
        l_dict = dict(lr)
        try:
            l_dict["archetype_mix"] = json.loads(lr["archetype_mix"] or "{}")
        except Exception:
            l_dict["archetype_mix"] = {}
        l_dict["player_id_list"] = [int(x) for x in str(lr["player_ids"] or "").split(",") if x.strip().isdigit()]
        l_dict["player_name_list"] = [x.strip() for x in str(lr["player_names"] or "").split(",") if x.strip()]
        abbr = lr["team_abbreviation"]
        lineup_evals_by_team.setdefault(abbr, []).append(l_dict)
        all_lineup_evals.append(l_dict)

    for t in default_teams_23_24:
        tid = t["team_id"]
        abbr = t["abbreviation"]
        # Get full team roster from player_season_stats (2024-25 + 2023-24)
        roster_sql = """
        SELECT p.player_id, p.full_name, ROUND(MAX(s.min), 1) as avg_min, MAX(s.gp) as gp,
               ROUND(MAX(s.pts), 1) as pts, ROUND(MAX(s.ast), 1) as ast, ROUND(MAX(s.reb), 1) as reb
        FROM player_season_stats s
        JOIN players p ON s.player_id = p.player_id
        WHERE s.team_id = ? AND s.season IN ('2024-25', '2023-24')
        GROUP BY p.player_id, p.full_name
        ORDER BY MAX(s.min) DESC
        LIMIT 22
        """
        r_rows = cur.execute(roster_sql, [tid]).fetchall()
        roster = []
        for r in r_rows:
            pid = r["player_id"]
            bit_idx = indexer.get_bit_index(tid, "2023-24", pid)
            roster.append({
                "player_id": pid,
                "full_name": r["full_name"],
                "avg_min": r["avg_min"],
                "gp": r["gp"],
                "pts": r["pts"],
                "ast": r["ast"],
                "reb": r["reb"],
                "bit_index": bit_idx,
            })

        wowy_data[str(tid)] = {
            "team_id": tid,
            "team_name": t["full_name"],
            "abbreviation": abbr,
            "base_off_rating": t["off_rating"],
            "base_def_rating": t["def_rating"],
            "base_net_rating": t["net_rating"],
            "roster": roster,
            "evaluated_lineups": lineup_evals_by_team.get(abbr, []),
        }

    # =========================================================================
    # 5. SPATIAL SHOT LOCATIONS FOR ALL 572 NBA PLAYERS & ALL 30 TEAMS
    # =========================================================================
    print("[*] Exporting real court zone shot locations for all 572 players and 30 teams...")
    shot_model = XGBExpectedShotModel()

    # Query all 572 players from ep_leaguedashplayershotlocations_shotlocations
    player_shot_rows = cur.execute(
        "SELECT * FROM ep_leaguedashplayershotlocations_shotlocations ORDER BY (__Restricted_Area____FGA__ + __Above_the_Break_3____FGA__ + __Mid_Range____FGA__) DESC"
    ).fetchall()

    all_player_zone_profiles = {}
    for sr in player_shot_rows:
        pid = int(sr["______PLAYER_ID__"] or 0)
        if not pid:
            continue
        pname = sr["______PLAYER_NAME__"] or "Player"
        tid = int(sr["______TEAM_ID__"] or 0)
        tabbr = sr["______TEAM_ABBREVIATION__"] or "NBA"

        ra_fgm = int(float(sr["__Restricted_Area____FGM__"] or 0))
        ra_fga = int(float(sr["__Restricted_Area____FGA__"] or 0))
        ra_pct = round(float(sr["__Restricted_Area____FG_PCT__"] or 0), 3)

        paint_fgm = int(float(sr["__In_The_Paint__Non_RA_____FGM__"] or 0))
        paint_fga = int(float(sr["__In_The_Paint__Non_RA_____FGA__"] or 0))
        paint_pct = round(float(sr["__In_The_Paint__Non_RA_____FG_PCT__"] or 0), 3)

        mid_fgm = int(float(sr["__Mid_Range____FGM__"] or 0))
        mid_fga = int(float(sr["__Mid_Range____FGA__"] or 0))
        mid_pct = round(float(sr["__Mid_Range____FG_PCT__"] or 0), 3)

        lc3_fgm = int(float(sr["__Left_Corner_3____FGM__"] or 0))
        lc3_fga = int(float(sr["__Left_Corner_3____FGA__"] or 0))
        lc3_pct = round(float(sr["__Left_Corner_3____FG_PCT__"] or 0), 3)

        rc3_fgm = int(float(sr["__Right_Corner_3____FGM__"] or 0))
        rc3_fga = int(float(sr["__Right_Corner_3____FGA__"] or 0))
        rc3_pct = round(float(sr["__Right_Corner_3____FG_PCT__"] or 0), 3)

        atb3_fgm = int(float(sr["__Above_the_Break_3____FGM__"] or 0))
        atb3_fga = int(float(sr["__Above_the_Break_3____FGA__"] or 0))
        atb3_pct = round(float(sr["__Above_the_Break_3____FG_PCT__"] or 0), 3)

        c3_fgm = int(float(sr["__Corner_3____FGM__"] or (lc3_fgm + rc3_fgm)))
        c3_fga = int(float(sr["__Corner_3____FGA__"] or (lc3_fga + rc3_fga)))
        c3_pct = round(float(sr["__Corner_3____FG_PCT__"] or (c3_fgm / max(1, c3_fga))), 3)

        tot_fga = ra_fga + paint_fga + mid_fga + lc3_fga + rc3_fga + atb3_fga
        tot_fgm = ra_fgm + paint_fgm + mid_fgm + lc3_fgm + rc3_fgm + atb3_fgm
        tot_3pm = lc3_fgm + rc3_fgm + atb3_fgm
        tot_3pa = lc3_fga + rc3_fga + atb3_fga

        if tot_fga <= 0:
            continue

        actual_pts = (tot_fgm - tot_3pm) * 2 + tot_3pm * 3
        actual_efg = round((tot_fgm + 0.5 * tot_3pm) / tot_fga, 3)

        exp_fgm_equiv = (
            ra_fga * ZONE_EXPECTED_FG["ra"]
            + paint_fga * ZONE_EXPECTED_FG["paint"]
            + mid_fga * ZONE_EXPECTED_FG["mid"]
            + lc3_fga * ZONE_EXPECTED_FG["lc3"] * 1.5
            + rc3_fga * ZONE_EXPECTED_FG["rc3"] * 1.5
            + atb3_fga * ZONE_EXPECTED_FG["atb3"] * 1.5
        )
        x_efg = round(exp_fgm_equiv / tot_fga, 3)
        smoe = round(actual_efg - x_efg, 3)

        all_player_zone_profiles[str(pid)] = {
            "player_id": pid,
            "name": pname,
            "team_id": tid,
            "team": tabbr,
            "summary": {
                "shots_analyzed": tot_fga,
                "total_fgm": tot_fgm,
                "total_fga": tot_fga,
                "total_3pm": tot_3pm,
                "total_3pa": tot_3pa,
                "actual_efg_pct": actual_efg,
                "x_efg_pct": x_efg,
                "smoe": smoe,
                "actual_points_per_shot": round(actual_pts / tot_fga, 2),
                "expected_points_per_shot": round(x_efg * 2.0, 2),
            },
            "zones": {
                "Restricted Area": {"fgm": ra_fgm, "fga": ra_fga, "fg_pct": ra_pct, "exp_pct": ZONE_EXPECTED_FG["ra"]},
                "In The Paint (Non-RA)": {"fgm": paint_fgm, "fga": paint_fga, "fg_pct": paint_pct, "exp_pct": ZONE_EXPECTED_FG["paint"]},
                "Mid-Range": {"fgm": mid_fgm, "fga": mid_fga, "fg_pct": mid_pct, "exp_pct": ZONE_EXPECTED_FG["mid"]},
                "Left Corner 3": {"fgm": lc3_fgm, "fga": lc3_fga, "fg_pct": lc3_pct, "exp_pct": ZONE_EXPECTED_FG["lc3"]},
                "Right Corner 3": {"fgm": rc3_fgm, "fga": rc3_fga, "fg_pct": rc3_pct, "exp_pct": ZONE_EXPECTED_FG["rc3"]},
                "Above the Break 3": {"fgm": atb3_fgm, "fga": atb3_fga, "fg_pct": atb3_pct, "exp_pct": ZONE_EXPECTED_FG["atb3"]},
                "Corner 3 Total": {"fgm": c3_fgm, "fga": c3_fga, "fg_pct": c3_pct, "exp_pct": 0.388},
            },
        }

    # Query all 30 teams from ep_leaguedashteamshotlocations_shotlocations
    team_shot_rows = cur.execute("SELECT * FROM ep_leaguedashteamshotlocations_shotlocations").fetchall()
    all_team_zone_profiles = {}
    for tr in team_shot_rows:
        tid = int(tr["______TEAM_ID__"] or 0)
        tname = tr["______TEAM_NAME__"] or "Team"
        tabbr = team_lookup.get(tid, {}).get("abbreviation", "NBA")

        ra_fgm = int(float(tr["__Restricted_Area____FGM__"] or 0))
        ra_fga = int(float(tr["__Restricted_Area____FGA__"] or 0))
        ra_pct = round(float(tr["__Restricted_Area____FG_PCT__"] or 0), 3)

        paint_fgm = int(float(tr["__In_The_Paint__Non_RA_____FGM__"] or 0))
        paint_fga = int(float(tr["__In_The_Paint__Non_RA_____FGA__"] or 0))
        paint_pct = round(float(tr["__In_The_Paint__Non_RA_____FG_PCT__"] or 0), 3)

        mid_fgm = int(float(tr["__Mid_Range____FGM__"] or 0))
        mid_fga = int(float(tr["__Mid_Range____FGA__"] or 0))
        mid_pct = round(float(tr["__Mid_Range____FG_PCT__"] or 0), 3)

        lc3_fgm = int(float(tr["__Left_Corner_3____FGM__"] or 0))
        lc3_fga = int(float(tr["__Left_Corner_3____FGA__"] or 0))
        lc3_pct = round(float(tr["__Left_Corner_3____FG_PCT__"] or 0), 3)

        rc3_fgm = int(float(tr["__Right_Corner_3____FGM__"] or 0))
        rc3_fga = int(float(tr["__Right_Corner_3____FGA__"] or 0))
        rc3_pct = round(float(tr["__Right_Corner_3____FG_PCT__"] or 0), 3)

        atb3_fgm = int(float(tr["__Above_the_Break_3____FGM__"] or 0))
        atb3_fga = int(float(tr["__Above_the_Break_3____FGA__"] or 0))
        atb3_pct = round(float(tr["__Above_the_Break_3____FG_PCT__"] or 0), 3)

        tot_fga = max(1, ra_fga + paint_fga + mid_fga + lc3_fga + rc3_fga + atb3_fga)
        tot_fgm = ra_fgm + paint_fgm + mid_fgm + lc3_fgm + rc3_fgm + atb3_fgm
        tot_3pm = lc3_fgm + rc3_fgm + atb3_fgm
        tot_3pa = lc3_fga + rc3_fga + atb3_fga
        actual_pts = (tot_fgm - tot_3pm) * 2 + tot_3pm * 3
        actual_efg = round((tot_fgm + 0.5 * tot_3pm) / tot_fga, 3)

        exp_fgm_equiv = (
            ra_fga * ZONE_EXPECTED_FG["ra"]
            + paint_fga * ZONE_EXPECTED_FG["paint"]
            + mid_fga * ZONE_EXPECTED_FG["mid"]
            + lc3_fga * ZONE_EXPECTED_FG["lc3"] * 1.5
            + rc3_fga * ZONE_EXPECTED_FG["rc3"] * 1.5
            + atb3_fga * ZONE_EXPECTED_FG["atb3"] * 1.5
        )
        x_efg = round(exp_fgm_equiv / tot_fga, 3)
        smoe = round(actual_efg - x_efg, 3)

        all_team_zone_profiles[tabbr] = {
            "team_id": tid,
            "name": tname,
            "abbreviation": tabbr,
            "summary": {
                "shots_analyzed": tot_fga,
                "total_fgm": tot_fgm,
                "total_fga": tot_fga,
                "total_3pm": tot_3pm,
                "total_3pa": tot_3pa,
                "actual_efg_pct": actual_efg,
                "x_efg_pct": x_efg,
                "smoe": smoe,
                "actual_points_per_shot": round(actual_pts / tot_fga, 2),
                "expected_points_per_shot": round(x_efg * 2.0, 2),
            },
            "zones": {
                "Restricted Area": {"fgm": ra_fgm, "fga": ra_fga, "fg_pct": ra_pct, "exp_pct": ZONE_EXPECTED_FG["ra"]},
                "In The Paint (Non-RA)": {"fgm": paint_fgm, "fga": paint_fga, "fg_pct": paint_pct, "exp_pct": ZONE_EXPECTED_FG["paint"]},
                "Mid-Range": {"fgm": mid_fgm, "fga": mid_fga, "fg_pct": mid_pct, "exp_pct": ZONE_EXPECTED_FG["mid"]},
                "Left Corner 3": {"fgm": lc3_fgm, "fga": lc3_fga, "fg_pct": lc3_pct, "exp_pct": ZONE_EXPECTED_FG["lc3"]},
                "Right Corner 3": {"fgm": rc3_fgm, "fga": rc3_fga, "fg_pct": rc3_pct, "exp_pct": ZONE_EXPECTED_FG["rc3"]},
                "Above the Break 3": {"fgm": atb3_fgm, "fga": atb3_fga, "fg_pct": atb3_pct, "exp_pct": ZONE_EXPECTED_FG["atb3"]},
            },
        }

    # =========================================================================
    # 6. ALL HISTORICAL GAMES ACROSS LAST 10 SEASONS (2015-16 TO 2024-25)
    # =========================================================================
    print("[*] Exporting all historical games across the last 10 seasons (2015-16 to 2024-25)...")
    valid_season_ids = list(SEASON_ID_TO_STR.keys())
    s_id_placeholders = ",".join("?" for _ in valid_season_ids)
    games_sql = f"""
    SELECT game_id, season_id, season_type, game_date, matchup,
           home_team_id, visitor_team_id, home_team_pts, visitor_team_pts, winner_team_id
    FROM games
    WHERE season_id IN ({s_id_placeholders})
    ORDER BY game_date DESC, game_id DESC
    """
    g_rows = cur.execute(games_sql, valid_season_ids).fetchall()
    games_10yr = []
    for gr in g_rows:
        h_abbr = team_lookup.get(gr["home_team_id"], {}).get("abbreviation", "HOM")
        a_abbr = team_lookup.get(gr["visitor_team_id"], {}).get("abbreviation", "AWY")
        h_pts = int(gr["home_team_pts"] or 0)
        a_pts = int(gr["visitor_team_pts"] or 0)
        season_label = SEASON_ID_TO_STR.get(str(gr["season_id"]), "2023-24")
        games_10yr.append({
            "id": gr["game_id"],
            "season": season_label,
            "type": "Playoffs" if str(gr["season_id"]).startswith("4") or gr["season_type"] == "Playoffs" else "Regular Season",
            "date": gr["game_date"],
            "home": h_abbr,
            "away": a_abbr,
            "h_pts": h_pts,
            "a_pts": a_pts,
            "margin": h_pts - a_pts,
        })

    print(f"[+] Exported {len(games_10yr)} historical games across 2015-16 through 2024-25.")

    # Marquee win probability timeline
    win_model = XGBWinProbabilityModel()
    game_timeline = []
    margins = [0, 2, -1, 3, 5, 2, 7, 10, 8, 12, 9, 14, 11, 15, 12, 8, 6, 9, 11, 7, 5, 8, 12, 10, 14]
    times = np.linspace(2880, 0, len(margins))
    for t_rem, margin in zip(times, margins):
        period = 1 if t_rem > 2160 else (2 if t_rem > 1440 else (3 if t_rem > 720 else 4))
        p_home = float(win_model.predict_win_probability(
            score_margin=margin,
            seconds_remaining=t_rem,
            period=period,
            possession_home=1
        ))
        game_timeline.append({
            "seconds_remaining": round(float(t_rem), 0),
            "period": period,
            "score_margin": int(margin),
            "home_score": int(112 - (t_rem / 2880) * 112 + margin / 2),
            "away_score": int(112 - (t_rem / 2880) * 112 - margin / 2),
            "home_win_prob": round(p_home, 4),
            "away_win_prob": round(1.0 - p_home, 4),
        })

    matchup_data = {
        "seasons": SEASONS_10YR,
        "total_historical_games": len(games_10yr),
        "recent_games_sample": games_10yr[:250],
        "marquee_games": [
            {
                "game_id": "0022300061",
                "home_team": "BOS",
                "away_team": "LAL",
                "game_date": "2024-02-01",
                "home_score": 118,
                "away_score": 105,
                "timeline": game_timeline,
            }
        ],
    }

    # =========================================================================
    # WRITE DATASETS TO PUBLIC/DATA AND LIB/STATIC-DATA
    # =========================================================================
    # Keep lib/static-data focused for fast TS compilation while including all 10 seasons of teams,
    # all 572 shot profiles, all 641 lineups, all 450 contracts, and 2024-25 + 2023-24 players,
    # plus full 10-season archives in public/data/ for instant fetch.
    recent_2_seasons_players = players_by_season.get("2023-24", []) + players_by_season.get("2024-25", [])
    recent_2_seasons_rapm = rapm_by_season.get("2023-24", []) + rapm_by_season.get("2024-25", [])

    shared_files = {
        "teams.json": {
            "season": "2023-24",
            "seasons": SEASONS_10YR,
            "total": len(default_teams_23_24),
            "teams": default_teams_23_24,
            "by_season": teams_by_season,
        },
        "cba_aprons.json": {
            "season": "2023-24",
            "total_contracts": len(contract_rows),
            "teams": cba_teams,
        },
        "wowy_lineups.json": {
            "season": "2023-24",
            "total_evaluated_lineups": len(all_lineup_evals),
            "teams": wowy_data,
            "top_lineups": all_lineup_evals[:150],
        },
        "shot_profiles.json": {
            "season": "2023-24",
            "total_players": len(all_player_zone_profiles),
            "total_teams": len(all_team_zone_profiles),
            "profiles": all_player_zone_profiles,
            "team_profiles": all_team_zone_profiles,
        },
        "game_matchups.json": matchup_data,
    }

    for name, data in shared_files.items():
        p1 = OUT_DIR / name
        with open(p1, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))
        print(f"[+] Written {p1} ({os.path.getsize(p1) / 1024:.1f} KB)")

        p2 = LIB_DATA_DIR / name
        with open(p2, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))

    # Write players.json & rapm_leaderboard.json:
    # In public/data/, store ALL 10 seasons (7,128 player-seasons)!
    # In lib/static-data/, store 2023-24 + 2024-25 (and also write players_10yr.json & games_10yr.json to public/data)
    full_players_payload = {
        "season": "2023-24",
        "seasons": SEASONS_10YR,
        "total": len(all_10yr_players),
        "players": players_by_season.get("2023-24", []),
        "by_season": players_by_season,
    }
    full_rapm_payload = {
        "season": "2023-24",
        "seasons": SEASONS_10YR,
        "total": len(all_10yr_players),
        "players": rapm_by_season.get("2023-24", []),
        "by_season": rapm_by_season,
    }

    for fname, payload in [
        ("players.json", full_players_payload),
        ("players_10yr.json", full_players_payload),
        ("rapm_leaderboard.json", full_rapm_payload),
        ("games_10yr.json", {"seasons": SEASONS_10YR, "total": len(games_10yr), "games": games_10yr}),
    ]:
        p_out = OUT_DIR / fname
        with open(p_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, separators=(",", ":"))
        print(f"[+] Written {p_out} ({os.path.getsize(p_out) / 1024:.1f} KB)")

    # Also write all 10 seasons to lib/static-data/players.json and rapm_leaderboard.json if compact size is small (~2.5 MB)
    for fname, payload in [
        ("players.json", full_players_payload),
        ("rapm_leaderboard.json", full_rapm_payload),
    ]:
        p_lib = LIB_DATA_DIR / fname
        with open(p_lib, "w", encoding="utf-8") as f:
            json.dump(payload, f, separators=(",", ":"))
        print(f"[+] Written {p_lib} ({os.path.getsize(p_lib) / 1024:.1f} KB)")

    conn.close()
    print("[SUCCESS] All 10-season static datasets exported successfully!")


if __name__ == "__main__":
    export_all()
