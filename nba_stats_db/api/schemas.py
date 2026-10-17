"""
schemas.py - Pydantic Request & Response Schemas for FastAPI Endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "2.3.0-PROD"
    database: str
    cache_tier: str
    parquet_possessions_count: int
    active_models: List[str]


class WOWYRequest(BaseModel):
    team_id: int = Field(..., description="NBA Team ID (e.g. 1610612738 for BOS)")
    season: str = Field(default="2023-24", description="NBA Season (e.g. 2023-24)")
    on_player_ids: List[int] = Field(default_factory=list, description="List of Player IDs who must be ON the court")
    off_player_ids: List[int] = Field(default_factory=list, description="List of Player IDs who must be OFF the court")


class WOWYResponse(BaseModel):
    team_id: int
    season: str
    on_player_ids: List[int]
    off_player_ids: List[int]
    m_on: int
    m_off: int
    total_possessions: int
    total_points: int
    offensive_rating: float
    three_pt_attempts: int
    three_pt_makes: int
    turnovers: int
    tov_pct: float
    query_time_ms: float


class RAPMPlayerEntry(BaseModel):
    player_id: int
    player_name: str
    team_abbreviation: Optional[str] = None
    possessions: int
    orapm: float
    drapm: float
    rapm: float
    orapm_percentile: float
    drapm_percentile: float
    rapm_percentile: float


class RAPMLeaderboardResponse(BaseModel):
    season: str
    lambda_reg: float
    player_count: int
    stint_count: int
    solve_time_sec: float
    cached: bool
    players: List[RAPMPlayerEntry]


class ShotEvalRequest(BaseModel):
    shot_x: float = Field(..., description="Court X coordinate in feet from basket")
    shot_y: float = Field(..., description="Court Y coordinate in feet from baseline")
    shot_dist: Optional[float] = Field(default=None, description="Euclidean distance in feet")
    period: int = Field(default=1, description="Period (1-4, OT)")
    clock_seconds: float = Field(default=360.0, description="Seconds remaining in period")
    is_3pt: Optional[int] = Field(default=None, description="1 if 3PT, 0 if 2PT")


class ShotEvalResponse(BaseModel):
    shot_x: float
    shot_y: float
    shot_dist: float
    shot_angle: float
    make_probability: float
    expected_points: float
    x_efg_pct: float


class WinProbabilityRequest(BaseModel):
    score_margin: int = Field(..., description="Home score - Away score")
    seconds_remaining: float = Field(..., description="Total game seconds remaining (from 2880 to 0)")
    period: int = Field(default=1, description="Period")
    possession_home: int = Field(default=1, description="1 if Home has ball, 0 if Away")


class WinProbabilityResponse(BaseModel):
    score_margin: int
    seconds_remaining: float
    period: int
    home_win_prob: float
    away_win_prob: float


class WinProbTimelinePoint(BaseModel):
    period: int
    seconds_remaining: float
    score_margin: int
    home_score: int
    away_score: int
    home_win_prob: float
    away_win_prob: float


class PlayerPercentiles(BaseModel):
    pts: float
    reb: float
    ast: float
    stl: float
    blk: float
    ts_pct: float
    net_rating: float
    pie: float
    orapm: Optional[float] = None
    drapm: Optional[float] = None
    rapm: Optional[float] = None


class PlayerProfileResponse(BaseModel):
    player_id: int
    full_name: str
    team_id: Optional[int] = None
    team_abbreviation: Optional[str] = None
    is_active: bool
    archetype: Optional[str] = None
    traditional_stats: Dict[str, Any]
    advanced_stats: Dict[str, Any]
    percentiles: PlayerPercentiles
    recent_games: List[Dict[str, Any]]


class CBATeamApronResponse(BaseModel):
    team_id: int
    team_name: str
    season: str
    total_taxable_payroll: float
    salary_cap: float
    luxury_tax_threshold: float
    first_apron: float
    second_apron: float
    tax_bracket: str
    estimated_luxury_tax: float
    apron_1_space: float
    apron_2_space: float
    frozen_first_round_pick: bool
    can_use_mle: bool
    can_aggregate_salaries_in_trade: bool
    can_take_back_more_salary_in_trade: bool
