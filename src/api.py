"""FastAPI microservice exposing IPL telemetry and statistical metrics."""

import logging
from typing import List, Optional
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import CLEANED_DATA_PATH, SAMPLE_DATA_PATH
from src.metrics import (
    get_chase_success_rates,
    get_phase_scoring_rates,
    get_team_win_statistics,
    get_top_batsmen,
    get_top_bowlers,
    generate_summary_statistics_df,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="IPL Analytics Platform API",
    description="High-performance analytical microservice for IPL cricket ball telemetry (2008-2024)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory dataframe singleton
_DATA: Optional[pd.DataFrame] = None


def get_dataset() -> pd.DataFrame:
    """Lazy loader for dataset singleton."""
    global _DATA
    if _DATA is None:
        if CLEANED_DATA_PATH.exists():
            logger.info(f"Loading cleaned dataset into memory from {CLEANED_DATA_PATH}")
            _DATA = pd.read_csv(CLEANED_DATA_PATH, low_memory=False)
        elif SAMPLE_DATA_PATH.exists():
            logger.info(f"Loading sample dataset into memory from {SAMPLE_DATA_PATH}")
            _DATA = pd.read_csv(SAMPLE_DATA_PATH, low_memory=False)
        else:
            from src.data_cleaning import run_pipeline
            logger.info("No cleaned dataset found on disk; generating via pipeline...")
            _DATA = run_pipeline(export_cleaned=True)
    return _DATA


# --- Pydantic Schemas ---

class HealthResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "HEALTHY"})
    records_loaded: int = Field(..., json_schema_extra={"example": 278205})
    seasons_covered: str = Field(..., json_schema_extra={"example": "2008 - 2024"})
    version: str = Field(..., json_schema_extra={"example": "1.0.0"})


class BatsmanCareerResponse(BaseModel):
    batter: str = Field(..., json_schema_extra={"example": "V Kohli"})
    total_runs: int = Field(..., description="Total runs scored off bat", json_schema_extra={"example": 8671})
    balls_faced: int = Field(..., description="Deliveries faced", json_schema_extra={"example": 6500})
    strike_rate: float = Field(..., description="Runs scored per 100 balls", json_schema_extra={"example": 133.4})
    matches_played: int = Field(..., json_schema_extra={"example": 259})
    runs_per_match: float = Field(..., json_schema_extra={"example": 33.5})


class BowlerCareerResponse(BaseModel):
    bowler: str = Field(..., json_schema_extra={"example": "YS Chahal"})
    wickets: int = Field(..., description="Total wickets taken", json_schema_extra={"example": 221})
    runs_conceded: int = Field(..., description="Total runs conceded", json_schema_extra={"example": 4500})
    overs_bowled: float = Field(..., description="Overs bowled", json_schema_extra={"example": 600.0})
    economy_rate: float = Field(..., description="Runs per over", json_schema_extra={"example": 7.5})
    wickets_per_match: float = Field(..., json_schema_extra={"example": 1.3})


class TeamStatsResponse(BaseModel):
    team: str = Field(..., json_schema_extra={"example": "Mumbai Indians"})
    matches_played: int = Field(..., json_schema_extra={"example": 260})
    matches_won: int = Field(..., json_schema_extra={"example": 151})
    win_percentage: float = Field(..., json_schema_extra={"example": 58.08})


class ChaseBucketItem(BaseModel):
    target_range: str = Field(..., json_schema_extra={"example": "Low (<130)"})
    attempts: int = Field(..., json_schema_extra={"example": 139})
    successful: int = Field(..., json_schema_extra={"example": 121})
    success_rate: float = Field(..., json_schema_extra={"example": 87.1})


class ChaseAnalyticsResponse(BaseModel):
    overall_chase_win_pct: float = Field(..., json_schema_extra={"example": 53.84})
    breakdown: List[ChaseBucketItem]


class PhaseItem(BaseModel):
    phase: str = Field(..., json_schema_extra={"example": "PowerPlay (1-6)"})
    total_runs: int = Field(..., json_schema_extra={"example": 85000})
    overs: float = Field(..., json_schema_extra={"example": 10600.0})
    runs_per_over: float = Field(..., json_schema_extra={"example": 7.97})


class PhaseAnalyticsResponse(BaseModel):
    phases: List[PhaseItem]


# --- Endpoints ---

@app.get("/health", response_model=HealthResponse, tags=["System"])
def healthcheck():
    """Returns service health status and loaded dataset metadata."""
    df = get_dataset()
    min_yr = df["season_year"].min() if "season_year" in df.columns else df["season"].min()
    max_yr = df["season_year"].max() if "season_year" in df.columns else df["season"].max()
    return HealthResponse(
        status="HEALTHY",
        records_loaded=len(df),
        seasons_covered=f"{min_yr} - {max_yr}",
        version="1.0.0",
    )


@app.get("/api/v1/players/batting", response_model=BatsmanCareerResponse, tags=["Players"])
def get_batsman(name: str = Query(..., examples=["V Kohli"], description="Batsman full name")):
    """Returns all-time career batting telemetry for a specific player."""
    df = get_dataset()
    match_mask = df["batter"].str.lower() == name.strip().lower()
    player_df = df[match_mask]
    
    if player_df.empty:
        raise HTTPException(status_code=404, detail=f"Batter '{name}' not found.")

    runs = int(player_df["runs"].sum())
    balls = int(len(player_df))
    matches = int(player_df["match_id"].nunique())
    sr = round((runs / balls * 100), 2) if balls > 0 else 0.0
    rpm = round((runs / matches), 2) if matches > 0 else 0.0

    return BatsmanCareerResponse(
        batter=player_df["batter"].iloc[0],
        total_runs=runs,
        balls_faced=balls,
        strike_rate=sr,
        matches_played=matches,
        runs_per_match=rpm,
    )


@app.get("/api/v1/players/bowling", response_model=BowlerCareerResponse, tags=["Players"])
def get_bowler(name: str = Query(..., examples=["YS Chahal"], description="Bowler full name")):
    """Returns all-time career bowling telemetry for a specific player."""
    df = get_dataset()
    match_mask = df["bowler"].str.lower() == name.strip().lower()
    player_df = df[match_mask]
    
    if player_df.empty:
        raise HTTPException(status_code=404, detail=f"Bowler '{name}' not found.")

    runs_col = "runs_conceded_bowler" if "runs_conceded_bowler" in player_df.columns else "runs_total"
    wicket_col = "is_wicket" if "is_wicket" in player_df.columns else "wickets"

    runs = int(player_df[runs_col].sum())
    wickets = int(player_df[wicket_col].sum())
    balls = int(len(player_df))
    overs = round(balls / 6.0, 1)
    matches = int(player_df["match_id"].nunique())
    economy = round(runs / overs, 2) if overs > 0 else 0.0
    wpm = round(wickets / matches, 2) if matches > 0 else 0.0

    return BowlerCareerResponse(
        bowler=player_df["bowler"].iloc[0],
        wickets=wickets,
        runs_conceded=runs,
        overs_bowled=overs,
        economy_rate=economy,
        wickets_per_match=wpm,
    )


@app.get("/api/v1/teams/summary", response_model=List[TeamStatsResponse], tags=["Teams"])
def list_team_stats(min_matches: int = Query(0, description="Minimum matches played filter")):
    """Returns all franchise win rates and appearance counts."""
    df = get_dataset()
    stats = get_team_win_statistics(df, min_matches=min_matches)
    return stats.to_dict(orient="records")


@app.get("/api/v1/teams/{team_name}", response_model=TeamStatsResponse, tags=["Teams"])
def get_team_stats(team_name: str):
    """Returns record and win percentage for a specific franchise."""
    df = get_dataset()
    stats = get_team_win_statistics(df, min_matches=0)
    match_row = stats[stats["team"].str.lower() == team_name.strip().lower()]
    if match_row.empty:
        raise HTTPException(status_code=404, detail=f"Franchise '{team_name}' not found.")
    return match_row.iloc[0].to_dict()


@app.get("/api/v1/analytics/chase-success", response_model=ChaseAnalyticsResponse, tags=["Analytics"])
def get_chase_analytics():
    """Returns historical chase win rate broken down by target score bucket."""
    df = get_dataset()
    overall_rate, range_df = get_chase_success_rates(df)
    items = [
        ChaseBucketItem(
            target_range=str(r["target_range"]),
            attempts=int(r["attempts"]),
            successful=int(r["successful"]),
            success_rate=float(r["success_rate"]),
        )
        for _, r in range_df.iterrows()
    ]
    return ChaseAnalyticsResponse(overall_chase_win_pct=overall_rate, breakdown=items)


@app.get("/api/v1/analytics/over-phases", response_model=PhaseAnalyticsResponse, tags=["Analytics"])
def get_phase_analytics():
    """Returns runs per over by phase (PowerPlay, Middle, Death)."""
    df = get_dataset()
    phase_df = get_phase_scoring_rates(df)
    items = [
        PhaseItem(
            phase=str(r["phase"]),
            total_runs=int(r["total_runs"]),
            overs=float(r["overs"]),
            runs_per_over=float(r["runs_per_over"]),
        )
        for _, r in phase_df.iterrows()
    ]
    return PhaseAnalyticsResponse(phases=items)
