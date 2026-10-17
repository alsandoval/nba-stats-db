"""
lineup_synergy.py - Team Composition & Lineup Synergy Engine based on MIT Sloan White Papers.

Implements:
1. Muthu Alagappan (MIT Sloan 2012): Role Diversity & Lineup Balance Theory
2. Maymin, Maymin & Shen (MIT Sloan 2012 / IJCSS 2013): Skills Plus Minus (SPM) Non-Linear Synergy Matrix
3. Eli Witus & Dean Oliver (Houston Rockets / APBRmetrics): Diminishing Returns on Ball-Dominance & Usage Collision
4. Kirk Goldsberry & Cervone et al.: Geometric Floor Spacing & Perimeter Gravity
"""

import json
import itertools
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from .database import NBADatabase

logger = logging.getLogger(__name__)

# Canonical Archetype Names
ARCHETYPES = [
    "Versatile 3-and-D Wing",
    "Two-Way Mobile Big & Stretch Anchor",
    "Point-of-Attack Defensive Disruptor",
    "Heliocentric MVP Engine & Focal Hub",
    "Primary Playmaker / Floor General",
    "Dynamic Shot Creator / Slasher",
    "Rim-Protecting Roll Anchor",
    "3-and-D Movement Specialist",
]

# Baseline Theoretical Pairwise Synergy Matrix (Maymin et al. SPM Chemistry framework)
# Positive = complementary skill multiplication; Negative = skill cannibalization / spacing choke
PAIRWISE_SYNERGY_DEFAULTS = {
    ("Heliocentric MVP Engine & Focal Hub", "3-and-D Movement Specialist"): 0.85,
    ("Heliocentric MVP Engine & Focal Hub", "Rim-Protecting Roll Anchor"): 0.75,
    ("Heliocentric MVP Engine & Focal Hub", "Two-Way Mobile Big & Stretch Anchor"): 0.90,
    ("Heliocentric MVP Engine & Focal Hub", "Point-of-Attack Defensive Disruptor"): 0.60,
    ("Heliocentric MVP Engine & Focal Hub", "Versatile 3-and-D Wing"): 0.55,
    ("Heliocentric MVP Engine & Focal Hub", "Dynamic Shot Creator / Slasher"): -0.30,
    ("Heliocentric MVP Engine & Focal Hub", "Primary Playmaker / Floor General"): -0.45,
    ("Heliocentric MVP Engine & Focal Hub", "Heliocentric MVP Engine & Focal Hub"): -1.25,

    ("Primary Playmaker / Floor General", "3-and-D Movement Specialist"): 0.70,
    ("Primary Playmaker / Floor General", "Rim-Protecting Roll Anchor"): 0.65,
    ("Primary Playmaker / Floor General", "Two-Way Mobile Big & Stretch Anchor"): 0.75,
    ("Primary Playmaker / Floor General", "Dynamic Shot Creator / Slasher"): 0.40,
    ("Primary Playmaker / Floor General", "Primary Playmaker / Floor General"): -0.60,

    ("Dynamic Shot Creator / Slasher", "3-and-D Movement Specialist"): 0.60,
    ("Dynamic Shot Creator / Slasher", "Two-Way Mobile Big & Stretch Anchor"): 0.55,
    ("Dynamic Shot Creator / Slasher", "Rim-Protecting Roll Anchor"): 0.45,
    ("Dynamic Shot Creator / Slasher", "Dynamic Shot Creator / Slasher"): -0.40,

    ("3-and-D Movement Specialist", "Rim-Protecting Roll Anchor"): 0.50,
    ("3-and-D Movement Specialist", "Two-Way Mobile Big & Stretch Anchor"): 0.65,
    ("3-and-D Movement Specialist", "3-and-D Movement Specialist"): 0.45,

    ("Point-of-Attack Defensive Disruptor", "Rim-Protecting Roll Anchor"): 0.60,
    ("Point-of-Attack Defensive Disruptor", "Two-Way Mobile Big & Stretch Anchor"): 0.55,

    ("Rim-Protecting Roll Anchor", "Rim-Protecting Roll Anchor"): -0.95,
}


class LineupSynergyModel:
    """Evaluates 5-player lineup synergy, optimal roster composition, and trade chemistry."""

    def __init__(self, db: Optional[NBADatabase] = None):
        self.db = db or NBADatabase()

    def get_player_data(self, player_identifiers: List[Union[int, str]], season: str = "2024-25") -> pd.DataFrame:
        """Fetches tactical stats, archetype, and LEBRON ratings for a given list of player names or IDs."""
        import unicodedata
        conn = self.db.get_connection()
        if not player_identifiers:
            return pd.DataFrame()

        def strip_accents(text: str) -> str:
            return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn").lower()

        # Check if identifiers are ints (IDs) or strings (Names)
        is_id = all(isinstance(x, (int, np.integer)) or (isinstance(x, str) and x.isdigit()) for x in player_identifiers)

        if is_id:
            ids = [int(x) for x in player_identifiers]
            placeholders = ",".join(["?"] * len(ids))
            query = f"""
                SELECT 
                    c.player_id, c.player_name, c.team_abbreviation, c.season,
                    c.cluster_id, c.cluster_name,
                    COALESCE(b.box_lebron, 0.0) as box_lebron,
                    COALESCE(b.o_lebron, 0.0) as o_lebron,
                    COALESCE(b.d_lebron, 0.0) as d_lebron,
                    COALESCE(a.usg_pct, 0.20) * 100.0 as usg_pct,
                    COALESCE(a.ast_pct, 0.12) * 100.0 as ast_pct,
                    COALESCE(a.reb_pct, 0.08) * 100.0 as reb_pct,
                    COALESCE(a.ts_pct, 0.56) * 100.0 as ts_pct,
                    COALESCE(p.pts, 10.0) as pts,
                    COALESCE(p.fg3a, 0.0) / NULLIF(COALESCE(p.fga, 0.0), 0) * 100.0 as fg3a_rate,
                    COALESCE(p.fg3_pct, 0.0) * 100.0 as fg3_pct,
                    COALESCE(b.stl_pct, 0.015) as stl_pct,
                    COALESCE(b.blk_pct, 0.015) as blk_pct,
                    COALESCE(b.rim_defense_diff, 0.0) as rim_defense_diff,
                    COALESCE(b.deflections_per_100, 2.5) as deflections_per_100
                FROM player_position_clusters c
                LEFT JOIN box_lebron_ratings b ON c.player_id = b.player_id AND c.season = b.season
                LEFT JOIN player_season_stats p ON c.player_id = p.player_id AND c.season = p.season
                LEFT JOIN player_advanced_stats a ON c.player_id = a.player_id AND c.season = a.season
                WHERE c.season = ? AND c.player_id IN ({placeholders})
            """
            df = pd.read_sql_query(query, conn, params=[season] + ids)
            return df.drop_duplicates(subset=["player_id"])

        # Fetch all players for season and match in Python for robust accent & partial name matching
        query_all = f"""
            SELECT 
                c.player_id, c.player_name, c.team_abbreviation, c.season,
                c.cluster_id, c.cluster_name,
                COALESCE(b.box_lebron, 0.0) as box_lebron,
                COALESCE(b.o_lebron, 0.0) as o_lebron,
                COALESCE(b.d_lebron, 0.0) as d_lebron,
                COALESCE(a.usg_pct, 0.20) * 100.0 as usg_pct,
                COALESCE(a.ast_pct, 0.12) * 100.0 as ast_pct,
                COALESCE(a.reb_pct, 0.08) * 100.0 as reb_pct,
                COALESCE(a.ts_pct, 0.56) * 100.0 as ts_pct,
                COALESCE(p.pts, 10.0) as pts,
                COALESCE(p.fg3a, 0.0) / NULLIF(COALESCE(p.fga, 0.0), 0) * 100.0 as fg3a_rate,
                COALESCE(p.fg3_pct, 0.0) * 100.0 as fg3_pct,
                COALESCE(b.stl_pct, 0.015) as stl_pct,
                COALESCE(b.blk_pct, 0.015) as blk_pct,
                COALESCE(b.rim_defense_diff, 0.0) as rim_defense_diff,
                COALESCE(b.deflections_per_100, 2.5) as deflections_per_100
            FROM player_position_clusters c
            LEFT JOIN box_lebron_ratings b ON c.player_id = b.player_id AND c.season = b.season
            LEFT JOIN player_season_stats p ON c.player_id = p.player_id AND c.season = p.season
            LEFT JOIN player_advanced_stats a ON c.player_id = a.player_id AND c.season = a.season
            WHERE c.season = ?
        """
        df_all = pd.read_sql_query(query_all, conn, params=[season])
        if df_all.empty:
            return pd.DataFrame()

        df_all["norm_name"] = df_all["player_name"].apply(strip_accents)

        matched_indices = []
        for raw_ident in player_identifiers:
            clean_ident = strip_accents(str(raw_ident).strip())
            # Exact match first
            exact = df_all[df_all["norm_name"] == clean_ident]
            if not exact.empty:
                matched_indices.append(exact.index[0])
                continue
            # Substring match
            sub = df_all[df_all["norm_name"].str.contains(clean_ident, regex=False)]
            if not sub.empty:
                matched_indices.append(sub.index[0])
                continue
            # Split tokens (e.g. "Jokic" -> "jokic")
            tokens = clean_ident.split()
            token_match = df_all[df_all["norm_name"].apply(lambda n: all(t in n for t in tokens))]
            if not token_match.empty:
                matched_indices.append(token_match.index[0])

        if not matched_indices:
            return pd.DataFrame()

        matched_df = df_all.loc[matched_indices].copy()
        return matched_df.drop_duplicates(subset=["player_id"]).drop(columns=["norm_name"], errors="ignore")

    def _evaluate_dataframe(self, df: pd.DataFrame, season: str = "2024-25") -> Dict[str, Any]:
        """Evaluates a 5-player DataFrame slice using non-linear synergy and role diversity models."""
        if len(df) != 5:
            return {
                "error": f"Expected exactly 5 valid players for lineup evaluation, but resolved {len(df)}.",
                "resolved_players": df["player_name"].tolist() if not df.empty else []
            }

        # 1. Base Talent Sum (Linear LEBRON baseline)
        raw_lebron_sum = float(df["box_lebron"].sum())
        raw_o_lebron_sum = float(df["o_lebron"].sum())
        raw_d_lebron_sum = float(df["d_lebron"].sum())

        # 2. Archetype Counts & Mix
        archetype_counts = df["cluster_name"].value_counts().to_dict()
        archetypes = df["cluster_name"].tolist()

        # 3. Usage Cannibalization (Oliver / Witus Diminishing Returns)
        total_usg = float(df["usg_pct"].sum())
        num_engines = archetype_counts.get("Heliocentric MVP Engine & Focal Hub", 0)
        num_creators = archetype_counts.get("Dynamic Shot Creator / Slasher", 0)
        num_playmakers = archetype_counts.get("Primary Playmaker / Floor General", 0)

        usage_penalty = 0.0
        if total_usg > 105.0:
            usage_penalty += (total_usg - 105.0) * 0.045
        if (num_engines + num_creators + num_playmakers) >= 3:
            usage_penalty += 0.65 * ((num_engines + num_creators + num_playmakers) - 2)
        if num_engines >= 2:
            usage_penalty += 1.20 * (num_engines - 1)

        # 4. Spatial Spacing Index (Goldsberry / Cervone et al.)
        spacing_threats = df[(df["fg3a_rate"] >= 35.0) & (df["fg3_pct"] >= 33.0)]
        num_spacers = len(spacing_threats)

        spacing_score = float(np.sum((df["fg3a_rate"].fillna(0) / 100.0) * (df["fg3_pct"].fillna(0) / 100.0) * 10.0))
        
        spacing_bonus = 0.0
        if num_spacers >= 4:
            spacing_bonus += 1.40
        elif num_spacers == 3:
            spacing_bonus += 0.85
        elif num_spacers == 2:
            spacing_bonus += 0.20
        elif num_spacers <= 1:
            spacing_bonus -= 1.10  # Spacing choke penalty

        # 5. Frontcourt & Interior Anchor Integrity
        num_roll_anchors = archetype_counts.get("Rim-Protecting Roll Anchor", 0)
        num_stretch_anchors = archetype_counts.get("Two-Way Mobile Big & Stretch Anchor", 0)
        total_bigs = num_roll_anchors + num_stretch_anchors

        interior_bonus = 0.0
        if total_bigs == 1:
            interior_bonus += 0.80
        elif total_bigs == 2 and num_stretch_anchors >= 1:
            interior_bonus += 0.50
        elif num_roll_anchors >= 2:
            interior_bonus -= 1.30
        elif total_bigs == 0:
            interior_bonus -= 1.50

        # 6. Point-of-Attack Defense & Perimeter Containment
        num_poa = archetype_counts.get("Point-of-Attack Defensive Disruptor", 0)
        num_wings = archetype_counts.get("Versatile 3-and-D Wing", 0)
        num_3d_movers = archetype_counts.get("3-and-D Movement Specialist", 0)
        total_perimeter_defenders = num_poa + num_wings + num_3d_movers

        poa_bonus = 0.0
        if total_perimeter_defenders >= 2:
            poa_bonus += 0.70
        elif total_perimeter_defenders == 1:
            poa_bonus += 0.30
        else:
            poa_bonus -= 0.80

        # 7. Pairwise Synergy Aggregation (Maymin Chemistry Matrix)
        pairwise_synergy = 0.0
        pairs = list(itertools.combinations(archetypes, 2))
        for a1, a2 in pairs:
            pair_key = (a1, a2) if (a1, a2) in PAIRWISE_SYNERGY_DEFAULTS else (a2, a1)
            pairwise_synergy += PAIRWISE_SYNERGY_DEFAULTS.get(pair_key, 0.10)

        pairwise_synergy_scaled = pairwise_synergy * 0.25

        # Aggregate Offensive & Defensive Synergies
        offensive_synergy = float(spacing_bonus + (0.5 * pairwise_synergy_scaled) - usage_penalty)
        defensive_synergy = float(interior_bonus + poa_bonus + (0.5 * pairwise_synergy_scaled))
        total_synergy = offensive_synergy + defensive_synergy

        # 8. Predicted Net Rating
        predicted_net_rating = float((raw_lebron_sum * 1.85) + total_synergy)

        # 9. Alagappan Role Diversity & Balance Grade
        balance_score = 100.0
        if total_bigs == 0:
            balance_score -= 25.0
        if num_roll_anchors >= 2:
            balance_score -= 20.0
        if num_engines >= 2:
            balance_score -= 22.0
        if num_spacers <= 1:
            balance_score -= 25.0
        if total_usg > 115.0:
            balance_score -= 15.0
        if total_perimeter_defenders == 0:
            balance_score -= 20.0
        
        if (num_engines == 1 or num_creators >= 1) and num_spacers >= 3 and total_bigs >= 1 and total_perimeter_defenders >= 2:
            balance_score += 15.0

        balance_score = max(30.0, min(100.0, balance_score))

        if balance_score >= 90.0:
            balance_grade = "A+"
        elif balance_score >= 80.0:
            balance_grade = "A"
        elif balance_score >= 70.0:
            balance_grade = "B"
        elif balance_score >= 60.0:
            balance_grade = "C"
        elif balance_score >= 50.0:
            balance_grade = "D"
        else:
            balance_grade = "F"

        player_details = []
        for _, row in df.iterrows():
            player_details.append({
                "player_id": int(row["player_id"]),
                "player_name": str(row["player_name"]),
                "team": str(row["team_abbreviation"]),
                "archetype": str(row["cluster_name"]),
                "cluster_id": int(row["cluster_id"]),
                "box_lebron": round(float(row["box_lebron"]), 2),
                "o_lebron": round(float(row["o_lebron"]), 2),
                "d_lebron": round(float(row["d_lebron"]), 2),
                "usg_pct": round(float(row["usg_pct"]), 1),
                "ast_pct": round(float(row["ast_pct"]), 1),
                "reb_pct": round(float(row["reb_pct"]), 1),
                "fg3a_rate": round(float(row["fg3a_rate"]), 1),
                "fg3_pct": round(float(row["fg3_pct"]), 1),
            })

        sorted_ids = sorted([int(x) for x in df["player_id"].tolist()])
        lineup_id = "-".join(map(str, sorted_ids))

        return {
            "lineup_id": lineup_id,
            "season": season,
            "team": df["team_abbreviation"].iloc[0] if df["team_abbreviation"].nunique() == 1 else "MULTI",
            "players": player_details,
            "player_names": ", ".join(df["player_name"].tolist()),
            "archetype_mix": archetype_counts,
            "raw_lebron_sum": round(raw_lebron_sum, 2),
            "raw_o_lebron_sum": round(raw_o_lebron_sum, 2),
            "raw_d_lebron_sum": round(raw_d_lebron_sum, 2),
            "total_usage_pct": round(total_usg, 1),
            "num_shooters": num_spacers,
            "spacing_rating": round(spacing_score, 2),
            "offensive_synergy": round(offensive_synergy, 2),
            "defensive_synergy": round(defensive_synergy, 2),
            "usage_penalty": round(usage_penalty, 2),
            "total_synergy": round(total_synergy, 2),
            "predicted_net_rating": round(predicted_net_rating, 2),
            "balance_score": round(balance_score, 1),
            "balance_grade": balance_grade,
        }

    def evaluate_lineup(self, player_identifiers: List[Union[int, str]], season: str = "2024-25") -> Dict[str, Any]:
        """Evaluates a 5-man lineup using non-linear synergy and role diversity models."""
        df = self.get_player_data(player_identifiers, season=season)
        return self._evaluate_dataframe(df, season=season)

    def save_lineup_evaluation(self, eval_result: Dict[str, Any]) -> bool:
        """Persists evaluated lineup metrics into the team_lineup_evaluations table."""
        if "error" in eval_result or "lineup_id" not in eval_result:
            return False

        now = datetime.utcnow().isoformat()
        player_ids_str = ",".join(str(p["player_id"]) for p in eval_result["players"])

        query = """
            INSERT OR REPLACE INTO team_lineup_evaluations (
                lineup_id, season, season_type, team_abbreviation, player_names, player_ids,
                archetype_mix, raw_lebron_sum, offensive_synergy, defensive_synergy,
                usage_penalty, spacing_rating, predicted_net_rating, balance_grade,
                evaluation_json, updated_at
            ) VALUES (?, ?, 'Regular Season', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            eval_result["lineup_id"],
            eval_result["season"],
            eval_result.get("team", "NBA"),
            eval_result["player_names"],
            player_ids_str,
            json.dumps(eval_result["archetype_mix"]),
            eval_result["raw_lebron_sum"],
            eval_result["offensive_synergy"],
            eval_result["defensive_synergy"],
            eval_result["usage_penalty"],
            eval_result["spacing_rating"],
            eval_result["predicted_net_rating"],
            eval_result["balance_grade"],
            json.dumps(eval_result),
            now
        )
        self.db.execute_non_query(query, params)
        return True

    def optimize_team_lineup(
        self, team: str, season: str = "2024-25", top_k: int = 5, min_minutes: float = 200.0
    ) -> List[Dict[str, Any]]:
        """Finds the most synergistic 5-man lineups from a team's roster using combinatorial evaluation."""
        conn = self.db.get_connection()
        query = """
            SELECT player_id
            FROM player_position_clusters
            WHERE season = ? AND team_abbreviation = ? AND min >= ?
            ORDER BY min DESC
        """
        df_roster_ids = pd.read_sql_query(query, conn, params=(season, team, min_minutes))

        if len(df_roster_ids) < 5:
            query_all = """
                SELECT player_id
                FROM player_position_clusters
                WHERE season = ? AND team_abbreviation = ?
                ORDER BY min DESC
            """
            df_roster_ids = pd.read_sql_query(query_all, conn, params=(season, team))

        if len(df_roster_ids) < 5:
            return []

        # Cap combinations to top 12 roster members
        roster_ids = df_roster_ids.head(12)["player_id"].tolist()
        df_full = self.get_player_data(roster_ids, season=season)
        if len(df_full) < 5:
            return []

        combos = list(itertools.combinations(df_full.index, 5))
        evaluated = []
        for combo in combos:
            slice_df = df_full.loc[list(combo)]
            res = self._evaluate_dataframe(slice_df, season=season)
            if "error" not in res:
                evaluated.append(res)

        evaluated.sort(key=lambda x: x["predicted_net_rating"], reverse=True)
        top_results = evaluated[:top_k]
        for res in top_results:
            self.save_lineup_evaluation(res)

        return top_results


    def evaluate_trade_fit(
        self, target_player: Union[int, str], current_lineup: List[Union[int, str]], replaced_player: Union[int, str], season: str = "2024-25"
    ) -> Dict[str, Any]:
        """Evaluates the marginal chemistry and net rating impact of swapping a player in a lineup (Maymin Trade Theorem)."""
        before_eval = self.evaluate_lineup(current_lineup, season=season)
        if "error" in before_eval:
            return {"error": f"Current lineup invalid: {before_eval['error']}"}

        # Replace player
        new_lineup = []
        replaced_found = False
        for p in current_lineup:
            if str(p).strip().lower() == str(replaced_player).strip().lower() or (isinstance(p, int) and p == replaced_player):
                new_lineup.append(target_player)
                replaced_found = True
            else:
                new_lineup.append(p)

        if not replaced_found:
            # Match by resolved names
            target_name = str(replaced_player).lower()
            matched_id = None
            for p in before_eval["players"]:
                if target_name in p["player_name"].lower():
                    matched_id = p["player_id"]
                    break
            if matched_id:
                new_lineup = [target_player if p["player_id"] == matched_id else p["player_id"] for p in before_eval["players"]]
            else:
                return {"error": f"Replaced player '{replaced_player}' was not found in the current lineup."}

        after_eval = self.evaluate_lineup(new_lineup, season=season)
        if "error" in after_eval:
            return {"error": f"New lineup invalid: {after_eval['error']}"}

        delta_net_rtg = after_eval["predicted_net_rating"] - before_eval["predicted_net_rating"]
        delta_synergy = after_eval["total_synergy"] - before_eval["total_synergy"]
        delta_lebron = after_eval["raw_lebron_sum"] - before_eval["raw_lebron_sum"]

        return {
            "target_player": target_player,
            "replaced_player": replaced_player,
            "before_lineup": before_eval,
            "after_lineup": after_eval,
            "delta_predicted_net_rating": round(delta_net_rtg, 2),
            "delta_total_synergy": round(delta_synergy, 2),
            "delta_raw_lebron_sum": round(delta_lebron, 2),
            "synergy_verdict": (
                "Highly Synergistic Fit (+)" if delta_synergy > 0.5
                else "Neutral Fit" if delta_synergy >= -0.3
                else "Negative Chemistry Friction (-)"
            )
        }

    def compute_archetype_synergy_matrix(self, season: str = "2024-25") -> Dict[str, Any]:
        """Returns the full 8x8 pairwise archetype synergy and compatibility matrix."""
        matrix = []
        for i, a1 in enumerate(ARCHETYPES):
            row = []
            for j, a2 in enumerate(ARCHETYPES):
                pair_key = (a1, a2) if (a1, a2) in PAIRWISE_SYNERGY_DEFAULTS else (a2, a1)
                val = PAIRWISE_SYNERGY_DEFAULTS.get(pair_key, 0.10)
                row.append(round(val, 2))
            matrix.append({"archetype": a1, "synergies": row})

        return {
            "season": season,
            "archetypes": ARCHETYPES,
            "matrix": matrix
        }
