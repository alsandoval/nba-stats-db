"""
capology_ingestion.py - Ingestion pipeline for seeding and recalculating NBA Capology,
Contracts, and Team Cap Sheets.
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional
import pandas as pd
from .database import NBADatabase
from .tax_calculator import TaxCalculator

logger = logging.getLogger(__name__)

class CapologyIngestion:
    """Manages loading contracts, cap settings, dead money, and recomputing team cap sheets."""

    def __init__(self, db: Optional[NBADatabase] = None):
        self.db = db or NBADatabase()

    def seed_from_file(self, seed_filepath: Optional[str] = None) -> Dict[str, int]:
        """
        Loads contract seed data from JSON and populates SQLite database.
        """
        if seed_filepath is None:
            # Look in data/contracts_seed.json relative to project root
            seed_filepath = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "data", "contracts_seed.json")
            )

        if not os.path.exists(seed_filepath):
            raise FileNotFoundError(f"Contracts seed file not found at: {seed_filepath}")

        with open(seed_filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        counts = {
            "cba_settings": 0,
            "contracts": 0,
            "contract_years": 0,
            "dead_money": 0,
            "trade_exceptions": 0,
            "team_cap_sheets": 0
        }

        # 1. Seed CBA Settings
        if "cba_settings" in data:
            cba_rows = data["cba_settings"]
            counts["cba_settings"] = self.db.upsert_rows(
                table_name="cba_cap_settings",
                rows=cba_rows,
                conflict_keys=["season"]
            )

        # 2. Seed Master Contracts
        if "contracts" in data:
            counts["contracts"] = self.db.upsert_rows(
                table_name="player_contracts",
                rows=data["contracts"],
                conflict_keys=["contract_id"]
            )

        # 3. Seed Contract Years
        if "contract_years" in data:
            counts["contract_years"] = self.db.upsert_rows(
                table_name="contract_years",
                rows=data["contract_years"],
                conflict_keys=["contract_id", "season"]
            )

        # 4. Seed Dead Money
        if "dead_money" in data:
            team_map = self.get_team_id_map()
            for dm in data["dead_money"]:
                if "team_id" not in dm:
                    dm["team_id"] = team_map.get(dm.get("team_abbreviation"), 0)
            counts["dead_money"] = self.db.upsert_rows(
                table_name="dead_money",
                rows=data["dead_money"],
                conflict_keys=["team_abbreviation", "player_name", "season"]
            )

        # 5. Seed Trade Exceptions
        if "trade_exceptions" in data:
            team_map = self.get_team_id_map()
            for tpe in data["trade_exceptions"]:
                if "team_id" not in tpe:
                    tpe["team_id"] = team_map.get(tpe.get("team_abbreviation"), 0)
            counts["trade_exceptions"] = self.db.upsert_rows(
                table_name="trade_exceptions",
                rows=data["trade_exceptions"],
                conflict_keys=["team_abbreviation", "source_player", "created_season"]
            )

        # 6. Recalculate Team Cap Sheets for both 2023-24 and 2024-25
        s23 = self.recalculate_all_team_cap_sheets("2023-24")
        s24 = self.recalculate_all_team_cap_sheets("2024-25")
        counts["team_cap_sheets"] = s23 + s24

        logger.info("Seeded Capology database successfully: %s", counts)
        return counts

    def get_team_id_map(self) -> Dict[str, int]:
        """Returns map of team_abbreviation -> team_id."""
        team_map = {
            "ATL": 1610612737, "BOS": 1610612738, "CLE": 1610612739, "NOP": 1610612740,
            "CHI": 1610612741, "DAL": 1610612742, "DEN": 1610612743, "GSW": 1610612744,
            "HOU": 1610612745, "LAC": 1610612746, "LAL": 1610612747, "MIA": 1610612748,
            "MIL": 1610612749, "MIN": 1610612750, "BKN": 1610612751, "NYK": 1610612752,
            "ORL": 1610612753, "IND": 1610612754, "PHI": 1610612755, "PHX": 1610612756,
            "POR": 1610612757, "SAC": 1610612758, "SAS": 1610612759, "OKC": 1610612760,
            "TOR": 1610612761, "UTA": 1610612762, "MEM": 1610612763, "WAS": 1610612764,
            "DET": 1610612765, "CHA": 1610612766
        }
        return team_map

    def get_cba_settings(self, season: str = "2023-24") -> Dict[str, float]:
        """Fetches CBA cap figures for a given season."""
        rows = self.db.execute_query(
            "SELECT * FROM cba_cap_settings WHERE season = ?",
            (season,)
        )
        if rows:
            return dict(rows[0])
        return TaxCalculator.DEFAULT_CAP_SETTINGS.get(
            season, TaxCalculator.DEFAULT_CAP_SETTINGS["2023-24"]
        )

    def recalculate_team_cap_sheet(self, team_abbreviation: str, season: str = "2023-24") -> Dict[str, Any]:
        """
        Recalculates a single team's active payroll, dead money, cap room, tax bill, and apron tier.
        """
        team_map = self.get_team_id_map()
        team_id = team_map.get(team_abbreviation, 0)
        cba = self.get_cba_settings(season)

        # 1. Sum active player salaries
        active_sal_query = """
        SELECT COALESCE(SUM(cy.cap_hit), 0.0) as active_sum
        FROM player_contracts pc
        JOIN contract_years cy ON pc.contract_id = cy.contract_id
        WHERE pc.team_abbreviation = ? AND cy.season = ? AND pc.is_active = 1
        """
        active_res = self.db.execute_query(active_sal_query, (team_abbreviation, season))
        active_salary = float(active_res[0]["active_sum"]) if active_res else 0.0

        # 2. Sum dead money
        dead_query = """
        SELECT COALESCE(SUM(amount), 0.0) as dead_sum
        FROM dead_money
        WHERE team_abbreviation = ? AND season = ?
        """
        dead_res = self.db.execute_query(dead_query, (team_abbreviation, season))
        dead_money = float(dead_res[0]["dead_sum"]) if dead_res else 0.0

        total_payroll = active_salary + dead_money

        # Check existing repeater & hard-cap status
        existing = self.db.execute_query(
            "SELECT is_repeater, hard_capped_at FROM team_cap_sheets WHERE team_abbreviation = ? AND season = ?",
            (team_abbreviation, season)
        )
        is_repeater = bool(existing[0]["is_repeater"]) if existing and existing[0]["is_repeater"] is not None else False
        hard_capped_at = existing[0]["hard_capped_at"] if existing else None

        # Standard repeater teams (historically Warriors, Clippers, Celtics, Bucks)
        if team_abbreviation in ("GSW", "LAC") and season in ("2023-24", "2024-25"):
            is_repeater = True

        status = TaxCalculator.evaluate_cap_status(
            total_payroll=total_payroll,
            cap_settings=cba,
            is_repeater=is_repeater,
            hard_capped_at=hard_capped_at
        )

        cap_sheet_row = {
            "team_id": team_id,
            "team_abbreviation": team_abbreviation,
            "season": season,
            "active_salary": round(active_salary, 2),
            "dead_money": round(dead_money, 2),
            "total_cap_allocations": round(total_payroll, 2),
            "cap_space": round(status["cap_space"], 2),
            "tax_room": round(status["tax_room"], 2),
            "first_apron_room": round(status["first_apron_room"], 2),
            "second_apron_room": round(status["second_apron_room"], 2),
            "tax_bill": round(status["tax_bill"], 2),
            "is_repeater": 1 if is_repeater else 0,
            "hard_capped_at": hard_capped_at
        }

        self.db.upsert_rows(
            table_name="team_cap_sheets",
            rows=[cap_sheet_row],
            conflict_keys=["team_id", "season"]
        )

        cap_sheet_row.update(status)
        return cap_sheet_row

    def recalculate_all_team_cap_sheets(self, season: str = "2023-24") -> int:
        """
        Recalculates cap sheets for all 30 NBA teams for a season.
        """
        team_map = self.get_team_id_map()
        count = 0
        for tabbr in team_map.keys():
            self.recalculate_team_cap_sheet(tabbr, season)
            count += 1
        return count
