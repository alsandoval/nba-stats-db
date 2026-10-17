"""
routes_cba.py - 2023 CBA Apron Status, Tax Brackets, and Trade Restrictions Endpoints.
"""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Query

from ..tax_calculator import TaxCalculator
from .schemas import CBATeamApronResponse
from .cache import cache

router = APIRouter(prefix="/api/cba", tags=["CBA & Contracts"])

_tax_calc = TaxCalculator()

# Estimated 2023-24 payroll defaults per team for illustrative accuracy
SAMPLE_TEAM_PAYROLLS = {
    1610612738: 184500000.0,  # BOS (Second Apron)
    1610612747: 169000000.0,  # LAL (Over Tax, Below First Apron)
    1610612744: 192000000.0,  # GSW (Second Apron)
    1610612756: 188000000.0,  # PHX (Second Apron)
    1610612743: 175000000.0,  # DEN (First Apron)
}


@router.get("/teams/{team_id}/apron", response_model=CBATeamApronResponse)
def get_team_cba_apron(
    team_id: int,
    season: str = Query(default="2023-24"),
    payroll: float = Query(default=0.0),
) -> CBATeamApronResponse:
    """Evaluates CBA Apron Tier (Under Tax, Taxpayer, Apron 1, Apron 2) and penalties."""
    cache_key = f"cba_apron:{team_id}:{season}:{payroll}"
    cached = cache.get_json(cache_key)
    if cached:
        return CBATeamApronResponse(**cached)

    settings = _tax_calc.DEFAULT_CAP_SETTINGS.get(season, _tax_calc.DEFAULT_CAP_SETTINGS["2023-24"])
    team_payroll = payroll if payroll > 0 else SAMPLE_TEAM_PAYROLLS.get(team_id, 166000000.0)

    # Evaluate cap status
    cap_info = _tax_calc.evaluate_cap_status(team_payroll, settings, is_repeater=False)

    is_second_apron = cap_info["tier_code"] == "SECOND_APRON"
    is_first_apron = cap_info["tier_code"] in ("FIRST_APRON", "SECOND_APRON")

    resp = {
        "team_id": team_id,
        "team_name": f"Franchise {team_id}",
        "season": season,
        "total_taxable_payroll": round(team_payroll, 2),
        "salary_cap": settings["salary_cap"],
        "luxury_tax_threshold": settings["tax_level"],
        "first_apron": settings["first_apron"],
        "second_apron": settings["second_apron"],
        "tax_bracket": cap_info["tier"],
        "estimated_luxury_tax": round(cap_info.get("tax_bill", 0.0), 2),
        "apron_1_space": round(cap_info["first_apron_room"], 2),
        "apron_2_space": round(cap_info["second_apron_room"], 2),
        "frozen_first_round_pick": is_second_apron,
        "can_use_mle": not is_first_apron,
        "can_aggregate_salaries_in_trade": not is_second_apron,
        "can_take_back_more_salary_in_trade": not is_first_apron,
    }

    cache.set_json(cache_key, resp, ttl=86400)
    return CBATeamApronResponse(**resp)
