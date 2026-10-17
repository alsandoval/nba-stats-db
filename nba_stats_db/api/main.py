"""
main.py - FastAPI Application Entry Point for Antigravity NBA Analytics Platform.
"""

import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ..possession.olap import DuckDBPossessionEngine
from .cache import cache
from .schemas import HealthResponse

from .routes_wowy import router as wowy_router
from .routes_rapm import router as rapm_router
from .routes_shots import router as shots_router
from .routes_games import router as games_router
from .routes_players import router as players_router
from .routes_teams import router as teams_router
from .routes_cba import router as cba_router
from .routes_arrow import router as arrow_router

app = FastAPI(
    title="Antigravity NBA Analytics Platform",
    description="Sub-15ms WOWY filtering, Sparse Stint Ridge RAPM, XGBoost xeFG% & Win Probability, and Apache Arrow IPC streaming.",
    version="2.3.0-PROD",
)

# Enable CORS for Next.js frontend and external integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(wowy_router)
app.include_router(rapm_router)
app.include_router(shots_router)
app.include_router(games_router)
app.include_router(players_router)
app.include_router(teams_router)
app.include_router(cba_router)
app.include_router(arrow_router)

# Mount static frontend directory
STATIC_DIR = Path("nba_stats_db/static")
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def serve_root():
    """Serves the integrated single-page analytics application."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse(
        {
            "name": "Antigravity NBA Analytics Platform API",
            "version": "2.3.0-PROD",
            "docs": "/docs",
            "status": "healthy",
        }
    )


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
def health_check() -> HealthResponse:
    """Returns database, cache tier, parquet storage, and model health diagnostics."""
    engine = DuckDBPossessionEngine(parquet_dir="data/gold/possessions")
    try:
        poss_count = engine.conn.execute("SELECT count(*) FROM possessions").fetchone()[0]
    except Exception:
        poss_count = 0

    return HealthResponse(
        status="ok",
        version="2.3.0-PROD",
        database="DuckDB + SQLite (Hybrid Metadata)",
        cache_tier="Remote Redis" if cache.redis_client else "In-Memory LRU/TTL",
        parquet_possessions_count=poss_count,
        active_models=[
            "PossessionStateMachine (Forward Scanner)",
            "Sparse Matrix Ridge RAPM (scipy.sparse.csc_matrix)",
            "XGBExpectedShotModel (xeFG% & SMOE)",
            "XGBWinProbabilityModel (Brownian Motion Calibrated)",
        ],
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("nba_stats_db.api.main:app", host="0.0.0.0", port=8000, reload=True)
