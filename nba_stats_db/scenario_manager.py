"""
scenario_manager.py - Scenario sandbox manager with save, load,
'Apply to Active Rosters', and 'Reset to Baseline' capabilities.
"""

import datetime
import json
import logging
import uuid
from typing import Any, Dict, List, Optional
from .database import NBADatabase
from .capology_ingestion import CapologyIngestion

logger = logging.getLogger(__name__)

class ScenarioManager:
    """Manages saved trade/cap scenarios and active state synchronization."""

    def __init__(self, db: Optional[NBADatabase] = None):
        self.db = db or NBADatabase()
        self.ingestion = CapologyIngestion(self.db)

    def list_scenarios(self) -> List[Dict[str, Any]]:
        """Lists all saved scenarios."""
        rows = self.db.execute_query(
            "SELECT scenario_id, name, description, created_at, updated_at FROM cap_scenarios ORDER BY updated_at DESC"
        )
        return [dict(r) for r in rows]

    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single scenario by ID with parsed state JSON."""
        rows = self.db.execute_query(
            "SELECT * FROM cap_scenarios WHERE scenario_id = ?",
            (scenario_id,)
        )
        if not rows:
            return None
        res = dict(rows[0])
        try:
            res["state"] = json.loads(res["state_json"])
        except Exception:
            res["state"] = {}
        return res

    def save_scenario(
        self,
        name: str,
        description: str,
        state: Dict[str, Any],
        scenario_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Saves or updates a simulation scenario."""
        sid = scenario_id or f"SCN-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.datetime.utcnow().isoformat()
        state_json = json.dumps(state)

        row = {
            "scenario_id": sid,
            "name": name,
            "description": description,
            "state_json": state_json,
            "created_at": now,
            "updated_at": now
        }

        self.db.upsert_rows(
            table_name="cap_scenarios",
            rows=[row],
            conflict_keys=["scenario_id"]
        )

        return {
            "scenario_id": sid,
            "name": name,
            "description": description,
            "updated_at": now,
            "status": "SAVED"
        }

    def delete_scenario(self, scenario_id: str) -> bool:
        """Deletes a saved scenario."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cap_scenarios WHERE scenario_id = ?", (scenario_id,))
            conn.commit()
            return cursor.rowcount > 0

    def apply_trade_to_active(
        self,
        trade_simulation_result: Dict[str, Any],
        season: str = "2023-24"
    ) -> Dict[str, Any]:
        """
        Applies a validated trade simulation directly to active player contracts and team rosters.
        Updates player_contracts team_abbreviation & team_id, generates TPEs,
        and recalculates affected team cap sheets.
        """
        if not trade_simulation_result.get("is_valid"):
            raise ValueError("Cannot apply an invalid trade to active rosters.")

        team_results = trade_simulation_result.get("team_results", {})
        team_map = self.ingestion.get_team_id_map()
        affected_teams = list(team_results.keys())

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # For each team, update player teams
            for tabbr, tinfo in team_results.items():
                dest_tid = team_map.get(tabbr, 0)
                incoming_players = tinfo.get("incoming_players", [])
                for inp in incoming_players:
                    pid = inp["player_id"]
                    cursor.execute(
                        """
                        UPDATE player_contracts 
                        SET team_abbreviation = ?, team_id = ?, updated_at = ?
                        WHERE player_id = ?
                        """,
                        (tabbr, dest_tid, datetime.datetime.utcnow().isoformat(), pid)
                    )

                # If TPE generated, insert into trade_exceptions
                tpe_amount = tinfo.get("generated_tpe", 0.0)
                if tpe_amount > 0:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO trade_exceptions 
                        (team_id, team_abbreviation, amount, created_season, expires_date, source_player, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (dest_tid, tabbr, tpe_amount, season, "2025-07-01", "Trade Surplus", "Auto-generated from trade execution")
                    )

            conn.commit()

        # Recalculate cap sheets for affected teams
        updated_sheets = []
        for tabbr in affected_teams:
            sheet = self.ingestion.recalculate_team_cap_sheet(tabbr, season)
            updated_sheets.append(sheet)

        return {
            "status": "SUCCESS",
            "message": f"Successfully applied trade across {len(affected_teams)} teams to active rosters.",
            "affected_teams": affected_teams,
            "updated_cap_sheets": updated_sheets
        }

    def reset_to_baseline(self) -> Dict[str, Any]:
        """
        Resets all active player contracts, dead money, and team cap sheets
        back to the official baseline seed dataset.
        """
        counts = self.ingestion.seed_from_file()
        return {
            "status": "SUCCESS",
            "message": "Successfully restored official baseline contracts and team cap sheets.",
            "counts": counts
        }
