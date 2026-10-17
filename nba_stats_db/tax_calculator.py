"""
tax_calculator.py - Progressive NBA Luxury Tax, Apron Thresholds,
Penalty Diagnostics, and Waive & Stretch Calculations under the 2023 CBA.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

class TaxCalculator:
    """Calculates luxury tax bills, apron statuses, penalties, and stretch provisions."""

    # Default 2023-24 & 2024-25 benchmarks
    DEFAULT_CAP_SETTINGS = {
        "2023-24": {
            "salary_cap": 136021000.0,
            "tax_level": 165294000.0,
            "first_apron": 172346000.0,
            "second_apron": 182794000.0,
            "min_team_salary": 122419000.0,
            "tax_bracket_size": 5000000.0,
            "nontaxpayer_mle": 12405000.0,
            "taxpayer_mle": 5000000.0,
            "room_mle": 7723000.0,
            "biannual_exception": 4516000.0,
            "cost_per_win": 3400000.0
        },
        "2024-25": {
            "salary_cap": 140588000.0,
            "tax_level": 170814000.0,
            "first_apron": 178132000.0,
            "second_apron": 188931000.0,
            "min_team_salary": 126529000.0,
            "tax_bracket_size": 5000000.0,
            "nontaxpayer_mle": 12822000.0,
            "taxpayer_mle": 5168000.0,
            "room_mle": 7983000.0,
            "biannual_exception": 4668000.0,
            "cost_per_win": 3550000.0
        }
    }

    # Standard tax rate steps: (bracket_floor, bracket_ceiling, rate_per_dollar)
    STANDARD_RATES = [
        (0.0, 5000000.0, 1.50),
        (5000000.0, 10000000.0, 1.75),
        (10000000.0, 15000000.0, 2.50),
        (15000000.0, 20000000.0, 3.25),
    ]
    # For every $5M above $20M in standard rate, add $0.50
    STANDARD_BASE_ABOVE_20M = 3.75

    # Repeater tax rate steps
    REPEATER_RATES = [
        (0.0, 5000000.0, 2.50),
        (5000000.0, 10000000.0, 2.75),
        (10000000.0, 15000000.0, 3.50),
        (15000000.0, 20000000.0, 4.25),
    ]
    # For every $5M above $20M in repeater rate, add $0.50
    REPEATER_BASE_ABOVE_20M = 4.75

    @classmethod
    def calculate_luxury_tax(
        cls,
        total_payroll: float,
        tax_level: float,
        is_repeater: bool = False,
        bracket_size: float = 5000000.0
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Computes progressive luxury tax according to official NBA CBA brackets.
        Returns (total_tax_bill, list_of_bracket_breakdowns).
        """
        if total_payroll <= tax_level:
            return 0.0, []

        taxable_amount = total_payroll - tax_level
        remaining = taxable_amount
        total_bill = 0.0
        breakdown = []

        rates = cls.REPEATER_RATES if is_repeater else cls.STANDARD_RATES
        base_above_20m = cls.REPEATER_BASE_ABOVE_20M if is_repeater else cls.STANDARD_BASE_ABOVE_20M

        # First four 5M brackets
        for b_start, b_end, rate in rates:
            if remaining <= 0:
                break
            taxable_in_bracket = min(remaining, b_end - b_start)
            cost = taxable_in_bracket * rate
            total_bill += cost
            breakdown.append({
                "bracket_range": f"${b_start/1e6:.1f}M - ${b_end/1e6:.1f}M",
                "taxable_amount": round(taxable_in_bracket, 2),
                "rate": rate,
                "tax_cost": round(cost, 2)
            })
            remaining -= taxable_in_bracket

        # Brackets above $20M: compounding rate (+0.50 per 5M)
        bracket_index = 0
        current_floor = 20000000.0
        while remaining > 0:
            rate = base_above_20m + (bracket_index * 0.50)
            current_ceiling = current_floor + bracket_size
            taxable_in_bracket = min(remaining, bracket_size)
            cost = taxable_in_bracket * rate
            total_bill += cost
            breakdown.append({
                "bracket_range": f"${current_floor/1e6:.1f}M - ${current_ceiling/1e6:.1f}M",
                "taxable_amount": round(taxable_in_bracket, 2),
                "rate": rate,
                "tax_cost": round(cost, 2)
            })
            remaining -= taxable_in_bracket
            current_floor = current_ceiling
            bracket_index += 1

        return round(total_bill, 2), breakdown

    @classmethod
    def evaluate_cap_status(
        cls,
        total_payroll: float,
        cap_settings: Dict[str, float],
        is_repeater: bool = False,
        hard_capped_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Determines cap status, apron room, luxury tax, and CBA restriction flags.
        """
        salary_cap = cap_settings.get("salary_cap", 136021000.0)
        tax_level = cap_settings.get("tax_level", 165294000.0)
        first_apron = cap_settings.get("first_apron", 172346000.0)
        second_apron = cap_settings.get("second_apron", 182794000.0)
        min_team_salary = cap_settings.get("min_team_salary", 122419000.0)

        cap_space = max(0.0, salary_cap - total_payroll)
        tax_room = tax_level - total_payroll
        first_apron_room = first_apron - total_payroll
        second_apron_room = second_apron - total_payroll

        # Determine Tier
        if total_payroll < salary_cap:
            tier = "Under Cap"
            tier_code = "UNDER_CAP"
        elif total_payroll < tax_level:
            tier = "Over Cap (Non-Taxpayer)"
            tier_code = "OVER_CAP"
        elif total_payroll < first_apron:
            tier = "Taxpayer"
            tier_code = "TAXPAYER"
        elif total_payroll < second_apron:
            tier = "First Apron"
            tier_code = "FIRST_APRON"
        else:
            tier = "Second Apron"
            tier_code = "SECOND_APRON"

        # Luxury Tax
        tax_bill, breakdown = cls.calculate_luxury_tax(
            total_payroll, tax_level, is_repeater=is_repeater
        )

        # Restrictions & Penalties
        penalties = []
        warnings = []
        is_hard_cap_violated = False

        if hard_capped_at == "First Apron" and total_payroll > first_apron:
            penalties.append("HARD CAP VIOLATION: Team exceeded First Apron after triggering hard cap!")
            is_hard_cap_violated = True
        elif hard_capped_at == "Second Apron" and total_payroll > second_apron:
            penalties.append("HARD CAP VIOLATION: Team exceeded Second Apron after triggering hard cap!")
            is_hard_cap_violated = True

        if tier_code in ("FIRST_APRON", "SECOND_APRON"):
            penalties.append("Cannot take back more salary in trades (100% outgoing salary limit).")
            penalties.append("Prohibited from signing buyout market free agents whose prior salary exceeded Non-Tax MLE.")
            penalties.append("Cannot use pre-existing trade exceptions (TPEs) created in prior seasons.")

        if tier_code == "SECOND_APRON":
            penalties.append("STRICT: Prohibited from aggregating multiple outgoing salaries in a trade.")
            penalties.append("STRICT: Cannot send cash considerations in any trade.")
            penalties.append("STRICT: First-round draft pick 7 years out is frozen (cannot be traded).")
            penalties.append("STRICT: Taxpayer Mid-Level Exception ($5M+) is completely eliminated ($0 available).")
            warnings.append("If remaining in Second Apron 2 of next 4 seasons, frozen 1st round pick drops to end of round (#30).")

        if total_payroll < min_team_salary:
            diff = min_team_salary - total_payroll
            warnings.append(f"Team is below the Salary Floor ($122.4M) by ${diff/1e6:.2f}M. Surcharge distributed to players at season end.")

        return {
            "total_payroll": round(total_payroll, 2),
            "tier": tier,
            "tier_code": tier_code,
            "cap_space": round(cap_space, 2),
            "tax_room": round(tax_room, 2),
            "first_apron_room": round(first_apron_room, 2),
            "second_apron_room": round(second_apron_room, 2),
            "tax_bill": round(tax_bill, 2),
            "total_team_cost": round(total_payroll + tax_bill, 2),
            "is_repeater": is_repeater,
            "hard_capped_at": hard_capped_at,
            "is_hard_cap_violated": is_hard_cap_violated,
            "penalties": penalties,
            "warnings": warnings,
            "tax_breakdown": breakdown
        }

    @classmethod
    def calculate_waive_and_stretch(
        cls,
        contract_years: List[Dict[str, Any]],
        waived_season: str = "2023-24"
    ) -> Dict[str, Any]:
        """
        Calculates annual cap hits when a player is waived and stretched.
        Rule: If waived after July 1st, current season is paid in full (or stretched if before Aug 31),
        remaining seasons are stretched over (2 * remaining_years) + 1 seasons.
        """
        # Filter applicable remaining contract years
        seasons_sorted = sorted(contract_years, key=lambda x: x["season"])
        remaining = [y for y in seasons_sorted if y["season"] >= waived_season]

        if not remaining:
            return {"total_stretched": 0.0, "seasons_count": 0, "annual_hit": 0.0, "schedule": []}

        # Calculate total remaining guaranteed money
        total_guaranteed = sum(y.get("guaranteed_amount", y.get("cap_hit", 0.0)) for y in remaining)
        num_remaining_years = len(remaining)
        stretch_seasons_count = (2 * num_remaining_years) + 1
        annual_cap_hit = round(total_guaranteed / stretch_seasons_count, 2)

        # Generate schedule
        start_year = int(waived_season.split("-")[0])
        schedule = []
        for i in range(stretch_seasons_count):
            s_year = start_year + i
            s_label = f"{s_year}-{str(s_year+1)[-2:]}"
            schedule.append({
                "season": s_label,
                "annual_hit": annual_cap_hit
            })

        return {
            "player_name": remaining[0].get("player_name", "Unknown"),
            "total_guaranteed_stretched": round(total_guaranteed, 2),
            "remaining_contract_years": num_remaining_years,
            "stretch_seasons_count": stretch_seasons_count,
            "annual_cap_hit": annual_cap_hit,
            "schedule": schedule
        }
