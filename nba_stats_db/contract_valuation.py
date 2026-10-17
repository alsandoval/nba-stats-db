"""
contract_valuation.py - Economic Wins Added (WAR) contract valuation engine.
Computes Fair Market Value, Surplus Value, ROI %, and Contract Value Tiers
by connecting player on-court Box LEBRON production with league economics.
"""

import logging
from typing import Any, Dict, List, Optional
import pandas as pd
from .database import NBADatabase

logger = logging.getLogger(__name__)

class ContractValuationEngine:
    """Evaluates contract surplus, ROI, and efficiency tiers using Box LEBRON WAR."""

    # Default economic constants per season
    SEASON_ECONOMICS = {
        "2023-24": {
            "dollar_per_war": 850000.0,
            "min_salary": 2019706.0,
            "max_salary": 47607350.0
        },
        "2024-25": {
            "dollar_per_war": 880000.0,
            "min_salary": 2087519.0,
            "max_salary": 51415938.0
        },
        "2025-26": {
            "dollar_per_war": 950000.0,
            "min_salary": 2200000.0,
            "max_salary": 55224526.0
        }
    }

    def __init__(self, db: Optional[NBADatabase] = None):
        self.db = db or NBADatabase()

    def evaluate_player_contract(
        self,
        player_id: int,
        season: str = "2023-24"
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates a single player's contract efficiency for a season.
        """
        df = self.get_valuation_leaderboard(season=season, player_id=player_id)
        if df.empty:
            return None
        return df.iloc[0].to_dict()

    def get_valuation_leaderboard(
        self,
        season: str = "2023-24",
        team_abbreviation: Optional[str] = None,
        tier: Optional[str] = None,
        sort_by: str = "surplus_value",
        ascending: bool = False,
        limit: int = 100,
        player_id: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Returns ranked DataFrame of players with their contract cap hit, Box LEBRON,
        Wins Added, Fair Market Value, Surplus Value, ROI %, and Contract Tier.
        """
        econ = self.SEASON_ECONOMICS.get(season, self.SEASON_ECONOMICS["2023-24"])
        dollar_per_war = econ["dollar_per_war"]
        min_salary = econ["min_salary"]

        # Fetch contract data joined with box_lebron_ratings
        # If box_lebron_ratings for current season is empty (e.g. future 24-25),
        # fall back to most recent available regular season (2023-24)
        sql = """
        SELECT 
            pc.contract_id,
            pc.player_id,
            pc.player_name,
            pc.team_abbreviation,
            pc.contract_type,
            pc.total_years,
            pc.total_value,
            pc.trade_kicker_pct,
            pc.poison_pill,
            pc.no_trade_clause,
            cy.season,
            cy.base_salary,
            cy.cap_hit,
            cy.guaranteed_amount,
            cy.option_type,
            COALESCE(blr.box_lebron, blr_fb.box_lebron, 0.0) as box_lebron,
            COALESCE(blr.o_lebron, blr_fb.o_lebron, 0.0) as o_lebron,
            COALESCE(blr.d_lebron, blr_fb.d_lebron, 0.0) as d_lebron,
            COALESCE(blr.wins_added, blr_fb.wins_added, 0.0) as wins_added,
            COALESCE(blr.offensive_archetype, blr_fb.offensive_archetype, 'Rotation') as offensive_archetype,
            COALESCE(blr.defensive_archetype, blr_fb.defensive_archetype, 'Rotation') as defensive_archetype
        FROM player_contracts pc
        JOIN contract_years cy ON pc.contract_id = cy.contract_id
        LEFT JOIN box_lebron_ratings blr 
            ON pc.player_id = blr.player_id 
            AND blr.season = cy.season 
            AND blr.season_type = 'Regular Season'
        LEFT JOIN box_lebron_ratings blr_fb 
            ON pc.player_id = blr_fb.player_id 
            AND blr_fb.season = '2023-24' 
            AND blr_fb.season_type = 'Regular Season'
        WHERE cy.season = ? AND pc.is_active = 1
        """
        params: List[Any] = [season]

        if team_abbreviation:
            sql += " AND pc.team_abbreviation = ?"
            params.append(team_abbreviation)

        if player_id:
            sql += " AND pc.player_id = ?"
            params.append(player_id)

        df = self.db.query_df(sql, tuple(params))
        if df.empty:
            return pd.DataFrame()

        # Compute Fair Market Value, Surplus, ROI, and Tiers
        def compute_market_value(war: float) -> float:
            if war <= 0:
                return min_salary
            val = (war * dollar_per_war) + min_salary
            return round(val, 2)

        df["fair_market_value"] = df["wins_added"].apply(compute_market_value)
        df["surplus_value"] = np_round = (df["fair_market_value"] - df["cap_hit"]).round(2)
        
        # ROI %
        def compute_roi(row) -> float:
            cap = row["cap_hit"]
            if cap <= 0:
                return 100.0
            return round((row["fair_market_value"] / cap) * 100.0, 1)

        df["roi_pct"] = df.apply(compute_roi, axis=1)

        # Classify Tiers
        def classify_tier(surplus: float) -> str:
            if surplus >= 15000000.0:
                return "Super Bargain"
            elif surplus >= 5000000.0:
                return "High Surplus Value"
            elif surplus >= -5000000.0:
                return "Fair Market Value"
            elif surplus >= -15000000.0:
                return "Overpaid"
            else:
                return "Toxic Contract"

        df["value_tier"] = df["surplus_value"].apply(classify_tier)

        # Filter by tier if specified
        if tier:
            df = df[df["value_tier"].str.lower() == tier.lower()]

        # Sorting
        if sort_by in df.columns:
            df = df.sort_values(by=sort_by, ascending=ascending)

        if limit > 0:
            df = df.head(limit)

        return df

    def get_team_contract_summary(self, team_abbreviation: str, season: str = "2023-24") -> Dict[str, Any]:
        """
        Returns team-level contract breakdown and total surplus generated.
        """
        df = self.get_valuation_leaderboard(season=season, team_abbreviation=team_abbreviation, limit=50)
        if df.empty:
            return {}

        total_cap = df["cap_hit"].sum()
        total_market_val = df["fair_market_value"].sum()
        total_surplus = df["surplus_value"].sum()
        total_war = df["wins_added"].sum()

        bargains = df[df["value_tier"].isin(["Super Bargain", "High Surplus Value"])]
        overpays = df[df["value_tier"].isin(["Overpaid", "Toxic Contract"])]

        return {
            "team_abbreviation": team_abbreviation,
            "season": season,
            "total_cap_hit": round(float(total_cap), 2),
            "total_market_value": round(float(total_market_val), 2),
            "total_surplus_value": round(float(total_surplus), 2),
            "total_wins_added": round(float(total_war), 2),
            "roster_count": len(df),
            "super_bargains_count": len(bargains),
            "overpaid_count": len(overpays),
            "players": df.to_dict(orient="records")
        }
