"""
trade_machine.py - Pro-grade NBA Trade Simulator implementing the full 2023 CBA rules:
Multi-team routing, First & Second Apron restrictions, aggregation bans,
trade kickers, poison pill provisions, roster limits, and TPE creation.
"""

import copy
import logging
from typing import Any, Dict, List, Optional, Tuple
from .database import NBADatabase
from .tax_calculator import TaxCalculator

logger = logging.getLogger(__name__)

class TradeMachine:
    """Simulates multi-team trades and validates strict 2023 CBA compliance."""

    def __init__(self, db: Optional[NBADatabase] = None):
        self.db = db or NBADatabase()

    def simulate_trade(
        self,
        trade_data: Dict[str, Any],
        season: str = "2023-24"
    ) -> Dict[str, Any]:
        """
        Simulates and validates a multi-team trade.
        trade_data structure:
        {
            "teams": {
                "LAL": {
                    "sending_player_ids": [2544, 1629060],
                    "cash_sent": 0.0,
                    "target_player_destinations": {2544: "BOS", 1629060: "BOS"}
                },
                "BOS": {
                    "sending_player_ids": [1628369],
                    "cash_sent": 0.0,
                    "target_player_destinations": {1628369: "LAL"}
                }
            }
        }
        """
        teams_input = trade_data.get("teams", {})
        if len(teams_input) < 2:
            return {
                "is_valid": False,
                "summary": "A trade requires at least two teams.",
                "team_results": {}
            }

        # 1. Fetch CBA Cap Settings
        cba_settings = self._get_cba_settings(season)
        salary_cap = cba_settings.get("salary_cap", 136021000.0)
        tax_level = cba_settings.get("tax_level", 165294000.0)
        first_apron = cba_settings.get("first_apron", 172346000.0)
        second_apron = cba_settings.get("second_apron", 182794000.0)
        max_player_salary = cba_settings.get("tax_level", 165294000.0) * 0.35

        # 2. Gather player and contract records for all involved players
        all_player_ids = []
        for tabbr, tinfo in teams_input.items():
            all_player_ids.extend(tinfo.get("sending_player_ids", []))

        players_dict = self._get_players_contract_data(all_player_ids, season)

        # 3. Route incoming players per team
        incoming_by_team: Dict[str, List[Dict[str, Any]]] = {t: [] for t in teams_input}
        outgoing_by_team: Dict[str, List[Dict[str, Any]]] = {t: [] for t in teams_input}

        for sender_team, tinfo in teams_input.items():
            dest_map = tinfo.get("target_player_destinations", {})
            for pid in tinfo.get("sending_player_ids", []):
                p_data = players_dict.get(pid)
                if not p_data:
                    return {
                        "is_valid": False,
                        "summary": f"Player ID {pid} not found in database or has no active contract for {season}.",
                        "team_results": {}
                    }
                outgoing_by_team[sender_team].append(p_data)

                # Determine destination team
                dest_team = dest_map.get(pid)
                if not dest_team or dest_team not in teams_input:
                    # Default: if 2-team trade, route to the other team
                    other_teams = [t for t in teams_input if t != sender_team]
                    if len(other_teams) == 1:
                        dest_team = other_teams[0]
                    else:
                        return {
                            "is_valid": False,
                            "summary": f"Destination team for player {p_data.get('player_name')} is unspecified in multi-team deal.",
                            "team_results": {}
                        }
                incoming_by_team[dest_team].append(p_data)

        # 4. Fetch team pre-trade cap sheets and rosters
        team_results = {}
        all_teams_valid = True

        for tabbr, tinfo in teams_input.items():
            pre_cap_sheet = self._get_team_cap_sheet(tabbr, season)
            pre_payroll = pre_cap_sheet.get("total_cap_allocations", 0.0)
            is_repeater = bool(pre_cap_sheet.get("is_repeater", 0))
            hard_capped_at = pre_cap_sheet.get("hard_capped_at")
            roster_count = self._get_roster_count(tabbr)

            outgoing_players = outgoing_by_team[tabbr]
            incoming_players = incoming_by_team[tabbr]
            cash_sent = float(tinfo.get("cash_sent", 0.0))

            # Evaluate outgoing salary and incoming salary with kickers & poison pills
            out_sal_total, in_sal_total, out_details, in_details = self._calculate_trade_salaries(
                outgoing_players=outgoing_players,
                incoming_players=incoming_players,
                season=season,
                max_salary=max_player_salary
            )

            post_payroll = pre_payroll - out_sal_total + in_sal_total
            post_roster_count = roster_count - len(outgoing_players) + len(incoming_players)

            # Evaluate pre and post tax statuses
            pre_status = TaxCalculator.evaluate_cap_status(
                total_payroll=pre_payroll,
                cap_settings=cba_settings,
                is_repeater=is_repeater,
                hard_capped_at=hard_capped_at
            )
            post_status = TaxCalculator.evaluate_cap_status(
                total_payroll=post_payroll,
                cap_settings=cba_settings,
                is_repeater=is_repeater,
                hard_capped_at=hard_capped_at
            )

            # Check 2023 CBA Trade Matching Rules
            validation = self._validate_cba_team_rules(
                team_abbreviation=tabbr,
                pre_status=pre_status,
                post_status=post_status,
                out_sal=out_sal_total,
                in_sal=in_sal_total,
                outgoing_players=out_details,
                incoming_players=in_details,
                cash_sent=cash_sent,
                post_roster_count=post_roster_count,
                cba_settings=cba_settings
            )

            if not validation["is_valid"]:
                all_teams_valid = False

            team_results[tabbr] = {
                "team_abbreviation": tabbr,
                "is_valid": validation["is_valid"],
                "cba_rule_applied": validation["rule_applied"],
                "max_allowed_incoming": validation["max_allowed_incoming"],
                "outgoing_salary": round(out_sal_total, 2),
                "incoming_salary": round(in_sal_total, 2),
                "net_salary_change": round(in_sal_total - out_sal_total, 2),
                "pre_trade_payroll": round(pre_payroll, 2),
                "post_trade_payroll": round(post_payroll, 2),
                "pre_trade_tax": round(pre_status["tax_bill"], 2),
                "post_trade_tax": round(post_status["tax_bill"], 2),
                "tax_difference": round(post_status["tax_bill"] - pre_status["tax_bill"], 2),
                "pre_trade_tier": pre_status["tier"],
                "post_trade_tier": post_status["tier"],
                "pre_roster_count": roster_count,
                "post_roster_count": post_roster_count,
                "outgoing_players": out_details,
                "incoming_players": in_details,
                "violations": validation["violations"],
                "warnings": validation["warnings"],
                "generated_tpe": validation["generated_tpe"]
            }

        summary = "Trade is 100% CBA LEGAL under 2023 NBA rules!" if all_teams_valid else "Trade FAILS 2023 CBA trade regulations."

        return {
            "is_valid": all_teams_valid,
            "season": season,
            "summary": summary,
            "team_results": team_results
        }

    def _calculate_trade_salaries(
        self,
        outgoing_players: List[Dict[str, Any]],
        incoming_players: List[Dict[str, Any]],
        season: str,
        max_salary: float
    ) -> Tuple[float, float, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Calculates outgoing and incoming salary values accounting for kickers & poison pills."""
        out_details = []
        out_total = 0.0
        for p in outgoing_players:
            cap_hit = float(p.get("cap_hit", 0.0))
            out_total += cap_hit
            out_details.append({
                "player_id": p.get("player_id"),
                "player_name": p.get("player_name"),
                "salary": cap_hit,
                "poison_pill": bool(p.get("poison_pill", 0)),
                "no_trade_clause": bool(p.get("no_trade_clause", 0))
            })

        in_details = []
        in_total = 0.0
        for p in incoming_players:
            cap_hit = float(p.get("cap_hit", 0.0))
            kicker_pct = float(p.get("trade_kicker_pct", 0.0))
            kicker_bonus = 0.0
            
            # Trade Kicker Calculation
            if kicker_pct > 0.0:
                remaining_val = float(p.get("total_value", cap_hit)) - cap_hit
                if remaining_val > 0:
                    kicker_bonus = min(remaining_val * kicker_pct, max_salary - cap_hit)
                    if kicker_bonus < 0:
                        kicker_bonus = 0.0

            # Poison Pill Provision: If player signed rookie extension, incoming cap hit = average of all years
            effective_in_salary = cap_hit + kicker_bonus
            if p.get("poison_pill", 0) and p.get("total_years", 1) > 1:
                avg_salary = float(p.get("total_value", cap_hit)) / float(p.get("total_years", 1))
                effective_in_salary = max(effective_in_salary, avg_salary)

            in_total += effective_in_salary
            in_details.append({
                "player_id": p.get("player_id"),
                "player_name": p.get("player_name"),
                "base_salary": cap_hit,
                "effective_incoming_salary": effective_in_salary,
                "trade_kicker_applied": round(kicker_bonus, 2) if kicker_bonus > 0 else 0.0,
                "poison_pill_adjusted": bool(p.get("poison_pill", 0))
            })

        return out_total, in_total, out_details, in_details

    def _validate_cba_team_rules(
        self,
        team_abbreviation: str,
        pre_status: Dict[str, Any],
        post_status: Dict[str, Any],
        out_sal: float,
        in_sal: float,
        outgoing_players: List[Dict[str, Any]],
        incoming_players: List[Dict[str, Any]],
        cash_sent: float,
        post_roster_count: int,
        cba_settings: Dict[str, float]
    ) -> Dict[str, Any]:
        """Validates specific CBA rules for a participating team."""
        salary_cap = cba_settings.get("salary_cap", 136021000.0)
        first_apron = cba_settings.get("first_apron", 172346000.0)
        second_apron = cba_settings.get("second_apron", 182794000.0)

        pre_payroll = pre_status["total_payroll"]
        post_payroll = post_status["total_payroll"]
        pre_tier = pre_status["tier_code"]
        post_tier = post_status["tier_code"]

        violations = []
        warnings = []
        rule_applied = "Standard CBA"
        max_allowed_incoming = in_sal
        generated_tpe = 0.0

        # No Trade Clause check
        for p in outgoing_players:
            if p.get("no_trade_clause"):
                warnings.append(f"Player {p.get('player_name')} holds a NO-TRADE CLAUSE. Player consent required to execute trade.")

        # Roster Count Rules: Max 15 standard contracts, Min 14
        if post_roster_count > 15:
            violations.append(f"Roster Limit Exceeded: Team will have {post_roster_count} players (Max allowed: 15). A player must be waived.")
        elif post_roster_count < 14:
            warnings.append(f"Roster below minimum: Team will have {post_roster_count} players (Minimum: 14). Must sign a player within 14 days.")

        # 1. ROOM TEAMS (Post-trade payroll below Salary Cap)
        if post_payroll <= salary_cap:
            rule_applied = "Room Team Exception"
            cap_room = max(0.0, salary_cap - pre_payroll)
            max_allowed_incoming = out_sal + cap_room + 250000.0
            # Always legal if under cap
            if out_sal > in_sal:
                generated_tpe = 0.0  # Room teams do not generate TPEs

        # 2. OVER-THE-CAP, NON-TAXPAYER TEAMS
        elif pre_payroll <= salary_cap and post_payroll > salary_cap:
            # Transitioned from under cap to over cap: can absorb up to cap room + standard rule
            cap_room = max(0.0, salary_cap - pre_payroll)
            excess_incoming = max(0.0, in_sal - cap_room)
            rule_applied = "Cap Room + Matching Exception"
            max_allowed_incoming = cap_room + (out_sal * 2.0) + 250000.0
            if in_sal > max_allowed_incoming:
                diff = in_sal - max_allowed_incoming
                violations.append(f"Incoming salary exceeds room exception by ${diff/1e6:.2f}M.")

        elif pre_tier in ("OVER_CAP", "TAXPAYER") and post_tier not in ("FIRST_APRON", "SECOND_APRON"):
            # Standard 2023 CBA Over-Cap Brackets:
            # <= $7.5M: 200% + $250k
            # $7.5M - $29M: out + $7.5M
            # > $29M: 125% + $250k
            if out_sal <= 7500000.0:
                max_allowed_incoming = (out_sal * 2.0) + 250000.0
                rule_applied = "Non-Taxpayer 200% Rule (<= $7.5M)"
            elif out_sal <= 29000000.0:
                max_allowed_incoming = out_sal + 7500000.0
                rule_applied = "Non-Taxpayer Outgoing + $7.5M Rule"
            else:
                max_allowed_incoming = (out_sal * 1.25) + 250000.0
                rule_applied = "Non-Taxpayer 125% Rule (> $29M)"

            if in_sal > max_allowed_incoming:
                diff = in_sal - max_allowed_incoming
                violations.append(f"Salary Matching Failed: Incoming (${in_sal/1e6:.2f}M) exceeds maximum allowed (${max_allowed_incoming/1e6:.2f}M) by ${diff/1e6:.2f}M.")

            # Check TPE generation
            if out_sal > in_sal and len(outgoing_players) == 1:
                generated_tpe = round(out_sal - in_sal, 2)

        # 3. FIRST APRON RESTRICTIONS (Pre or Post-trade >= First Apron)
        elif (pre_tier in ("FIRST_APRON", "SECOND_APRON") or post_tier in ("FIRST_APRON", "SECOND_APRON")) and (pre_tier != "SECOND_APRON" and post_tier != "SECOND_APRON"):
            rule_applied = "First Apron 100% Matching Rule"
            max_allowed_incoming = out_sal  # 100% max!

            if in_sal > out_sal:
                diff = in_sal - out_sal
                violations.append(f"First Apron Violation: Teams at or above First Apron cannot take back more salary than sent out (Incoming: ${in_sal/1e6:.2f}M vs Outgoing: ${out_sal/1e6:.2f}M, over by ${diff/1e6:.2f}M).")

            # Check Hard Cap
            if pre_status.get("hard_capped_at") == "First Apron" and post_payroll > first_apron:
                violations.append("Hard Cap Violation: Team is hard-capped at First Apron and post-trade payroll exceeds First Apron threshold.")

        # 4. SECOND APRON STRICT RESTRICTIONS (Pre or Post-trade >= Second Apron)
        else:
            rule_applied = "Second Apron Strict Restrictions"
            max_allowed_incoming = out_sal

            # Rule A: 100% Matching
            if in_sal > out_sal:
                diff = in_sal - out_sal
                violations.append(f"Second Apron Violation: Cannot take back more salary than sent out (Incoming: ${in_sal/1e6:.2f}M vs Outgoing: ${out_sal/1e6:.2f}M, over by ${diff/1e6:.2f}M).")

            # Rule B: NO SALARY AGGREGATION
            if len(outgoing_players) > 1 and len(incoming_players) > 0:
                # If team is bundling 2+ players, no single incoming player can exceed any single outgoing player
                max_single_out = max(p["salary"] for p in outgoing_players)
                for inp in incoming_players:
                    if inp["effective_incoming_salary"] > max_single_out:
                        diff = inp["effective_incoming_salary"] - max_single_out
                        violations.append(
                            f"Second Apron Aggregation Ban: Cannot combine multiple players to acquire {inp.get('player_name')} (${inp['effective_incoming_salary']/1e6:.2f}M), which exceeds highest outgoing salary (${max_single_out/1e6:.2f}M) by ${diff/1e6:.2f}M."
                        )

            # Rule C: NO CASH CONSIDERATIONS
            if cash_sent > 0:
                violations.append(f"Second Apron Cash Ban: Teams in the Second Apron are prohibited from sending cash (${cash_sent/1e6:.2f}M) in any trade.")

            # Check Hard Cap
            if pre_status.get("hard_capped_at") and post_payroll > second_apron:
                violations.append("Hard Cap Violation: Team is hard-capped and post-trade payroll exceeds Second Apron.")

        is_valid = len(violations) == 0

        return {
            "is_valid": is_valid,
            "rule_applied": rule_applied,
            "max_allowed_incoming": round(max_allowed_incoming, 2),
            "violations": violations,
            "warnings": warnings,
            "generated_tpe": generated_tpe
        }

    def _get_cba_settings(self, season: str) -> Dict[str, float]:
        rows = self.db.execute_query("SELECT * FROM cba_cap_settings WHERE season = ?", (season,))
        if rows:
            return dict(rows[0])
        return TaxCalculator.DEFAULT_CAP_SETTINGS.get(season, TaxCalculator.DEFAULT_CAP_SETTINGS["2023-24"])

    def _get_team_cap_sheet(self, team_abbreviation: str, season: str) -> Dict[str, Any]:
        rows = self.db.execute_query(
            "SELECT * FROM team_cap_sheets WHERE team_abbreviation = ? AND season = ?",
            (team_abbreviation, season)
        )
        if rows:
            return dict(rows[0])
        return {"total_cap_allocations": 0.0, "is_repeater": 0, "hard_capped_at": None}

    def _get_roster_count(self, team_abbreviation: str) -> int:
        rows = self.db.execute_query(
            "SELECT count(*) as cnt FROM player_contracts WHERE team_abbreviation = ? AND is_active = 1",
            (team_abbreviation,)
        )
        return int(rows[0]["cnt"]) if rows else 15

    def _get_players_contract_data(self, player_ids: List[int], season: str) -> Dict[int, Dict[str, Any]]:
        if not player_ids:
            return {}
        placeholders = ",".join("?" for _ in player_ids)
        sql = f"""
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
            cy.cap_hit,
            cy.base_salary
        FROM player_contracts pc
        JOIN contract_years cy ON pc.contract_id = cy.contract_id
        WHERE pc.player_id IN ({placeholders}) AND cy.season = ? AND pc.is_active = 1
        """
        params = list(player_ids) + [season]
        rows = self.db.execute_query(sql, tuple(params))
        return {r["player_id"]: dict(r) for r in rows}
