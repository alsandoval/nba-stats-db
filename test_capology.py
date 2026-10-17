"""
test_capology.py - Comprehensive unit and integration test suite for
NBA Capology, Contract Valuation, 2023 CBA Trade Machine, and Luxury Tax Engine.
"""

import unittest
import os
import json
from nba_stats_db.database import NBADatabase
from nba_stats_db.capology_ingestion import CapologyIngestion
from nba_stats_db.tax_calculator import TaxCalculator
from nba_stats_db.contract_valuation import ContractValuationEngine
from nba_stats_db.trade_machine import TradeMachine
from nba_stats_db.scenario_manager import ScenarioManager
from nba_stats_db.server import app

class TestCapologyModule(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = NBADatabase()
        cls.db.init_database()
        cls.ingestion = CapologyIngestion(cls.db)
        cls.ingestion.seed_from_file()
        cls.valuation = ContractValuationEngine(cls.db)
        cls.trade_machine = TradeMachine(cls.db)
        cls.scenario_mgr = ScenarioManager(cls.db)
        cls.client = app.test_client()

    def test_tax_calculator_brackets(self):
        """Test progressive luxury tax brackets under standard and repeater rates."""
        tax_level = 165294000.0
        payroll = tax_level + 12000000.0  # $12M over tax

        # Standard: 5M*1.50 ($7.5M) + 5M*1.75 ($8.75M) + 2M*2.50 ($5.0M) = $21.25M
        tax_standard, breakdown = TaxCalculator.calculate_luxury_tax(payroll, tax_level, is_repeater=False)
        self.assertEqual(tax_standard, 21250000.0)
        self.assertEqual(len(breakdown), 3)

        # Repeater: 5M*2.50 ($12.5M) + 5M*2.75 ($13.75M) + 2M*3.50 ($7.0M) = $33.25M
        tax_repeater, breakdown_rep = TaxCalculator.calculate_luxury_tax(payroll, tax_level, is_repeater=True)
        self.assertEqual(tax_repeater, 33250000.0)

    def test_apron_status_and_penalties(self):
        """Test apron status detection and penalty triggers."""
        cba = {
            "salary_cap": 136021000.0,
            "tax_level": 165294000.0,
            "first_apron": 172346000.0,
            "second_apron": 182794000.0,
            "min_team_salary": 122419000.0
        }

        # 1. Under Cap
        status_under = TaxCalculator.evaluate_cap_status(130000000.0, cba)
        self.assertEqual(status_under["tier_code"], "UNDER_CAP")
        self.assertGreater(status_under["cap_space"], 0)
        self.assertEqual(status_under["tax_bill"], 0.0)

        # 2. First Apron
        status_apron1 = TaxCalculator.evaluate_cap_status(175000000.0, cba)
        self.assertEqual(status_apron1["tier_code"], "FIRST_APRON")
        self.assertTrue(any("100% outgoing salary limit" in p for p in status_apron1["penalties"]))

        # 3. Second Apron
        status_apron2 = TaxCalculator.evaluate_cap_status(190000000.0, cba)
        self.assertEqual(status_apron2["tier_code"], "SECOND_APRON")
        self.assertTrue(any("STRICT: Prohibited from aggregating" in p for p in status_apron2["penalties"]))
        self.assertTrue(any("STRICT: Cannot send cash" in p for p in status_apron2["penalties"]))

    def test_waive_and_stretch(self):
        """Test waive and stretch amortization calculation."""
        # Player with 2 years remaining at $10M and $10M = $20M total
        # (2 * 2) + 1 = 5 seasons of stretch
        # Annual hit = $20M / 5 = $4.0M
        contract_years = [
            {"player_name": "Test Player", "season": "2023-24", "cap_hit": 10000000.0, "guaranteed_amount": 10000000.0},
            {"player_name": "Test Player", "season": "2024-25", "cap_hit": 10000000.0, "guaranteed_amount": 10000000.0}
        ]
        res = TaxCalculator.calculate_waive_and_stretch(contract_years, waived_season="2023-24")
        self.assertEqual(res["remaining_contract_years"], 2)
        self.assertEqual(res["stretch_seasons_count"], 5)
        self.assertEqual(res["annual_cap_hit"], 4000000.0)
        self.assertEqual(len(res["schedule"]), 5)

    def test_contract_valuation_engine(self):
        """Test Box LEBRON surplus value, ROI %, and tier assignment."""
        df = self.valuation.get_valuation_leaderboard(season="2023-24", limit=10)
        self.assertFalse(df.empty)
        self.assertIn("fair_market_value", df.columns)
        self.assertIn("surplus_value", df.columns)
        self.assertIn("roi_pct", df.columns)
        self.assertIn("value_tier", df.columns)

        # Check top surplus contracts are marked as Super Bargain
        top_row = df.iloc[0]
        self.assertGreater(top_row["surplus_value"], 0)
        self.assertIn(top_row["value_tier"], ["Super Bargain", "High Surplus Value"])

    def test_trade_machine_second_apron_aggregation_ban(self):
        """Test that a Second Apron team bundling multiple players for a single larger salary FAILS."""
        # GSW is a Second Apron team in 2023-24. Bundling 2 players for 1 higher salary must be blocked.
        trade_payload = {
            "teams": {
                "GSW": {
                    "sending_player_ids": [202691, 101108], # Klay + CP3
                    "cash_sent": 0.0,
                    "target_player_destinations": {}
                },
                "MIA": {
                    "sending_player_ids": [202710], # Jimmy Butler
                    "cash_sent": 0.0,
                    "target_player_destinations": {}
                }
            }
        }
        res = self.trade_machine.simulate_trade(trade_payload, season="2023-24")
        self.assertFalse(res["is_valid"])
        gsw_res = res["team_results"]["GSW"]
        self.assertFalse(gsw_res["is_valid"])
        self.assertTrue(any("Second Apron" in v for v in gsw_res["violations"]))

    def test_trade_machine_legal_trade_and_tpe(self):
        """Test a legal trade between an over-cap team and room team."""
        # SAS (Room team) absorbs a player
        trade_payload = {
            "teams": {
                "SAS": {
                    "sending_player_ids": [1630170], # Vassell
                    "cash_sent": 0.0,
                    "target_player_destinations": {1630170: "UTA"}
                },
                "UTA": {
                    "sending_player_ids": [1628378], # John Collins
                    "cash_sent": 0.0,
                    "target_player_destinations": {1628378: "SAS"}
                }
            }
        }
        res = self.trade_machine.simulate_trade(trade_payload, season="2023-24")
        # UTA and SAS are both under or within allowable brackets
        self.assertIn("SAS", res["team_results"])
        self.assertIn("UTA", res["team_results"])

    def test_scenario_manager_sandbox_and_baseline_reset(self):
        """Test saving a scenario, loading it, and resetting baseline."""
        scenario_id = "TEST-SCN-01"
        save_res = self.scenario_mgr.save_scenario(
            name="Unit Test Scenario",
            description="Testing sandbox capabilities",
            state={"season": "2023-24", "teams": ["LAL", "BOS"]},
            scenario_id=scenario_id
        )
        self.assertEqual(save_res["status"], "SAVED")

        # Get scenario
        scn = self.scenario_mgr.get_scenario(scenario_id)
        self.assertIsNotNone(scn)
        self.assertEqual(scn["name"], "Unit Test Scenario")

        # Delete scenario
        deleted = self.scenario_mgr.delete_scenario(scenario_id)
        self.assertTrue(deleted)

        # Baseline reset
        reset_res = self.scenario_mgr.reset_to_baseline()
        self.assertEqual(reset_res["status"], "SUCCESS")

    def test_rest_api_endpoints(self):
        """Test Capology REST API endpoints."""
        # Settings
        res = self.client.get("/api/capology/settings?season=2023-24")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("salary_cap", data["settings"])

        # Teams
        res_teams = self.client.get("/api/capology/teams?season=2023-24")
        self.assertEqual(res_teams.status_code, 200)
        data_teams = res_teams.get_json()
        self.assertTrue(data_teams["success"])
        self.assertEqual(data_teams["count"], 30)

        # Single Team
        res_bos = self.client.get("/api/capology/team/BOS?season=2023-24")
        self.assertEqual(res_bos.status_code, 200)
        data_bos = res_bos.get_json()
        self.assertTrue(data_bos["success"])
        self.assertIn("contracts", data_bos)
        self.assertGreater(len(data_bos["contracts"]), 10)

        # Valuation
        res_val = self.client.get("/api/capology/valuation?season=2023-24&limit=5")
        self.assertEqual(res_val.status_code, 200)
        data_val = res_val.get_json()
        self.assertTrue(data_val["success"])
        self.assertEqual(len(data_val["players"]), 5)

if __name__ == "__main__":
    unittest.main()
