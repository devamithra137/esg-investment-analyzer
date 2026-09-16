"""
main.py
-------
FastAPI application for the Real-Time ESG Investment Analyzer.

Exposes a single analysis endpoint that orchestrates the full pipeline:
  market data → ESG simulation → risk analysis → investment rating

Run
---
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Docs
----
    http://localhost:8000/docs      ← Swagger UI
    http://localhost:8000/redoc     ← ReDoc

Author  : ESG Investment Analyzer
Version : 1.0.0
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Annotated

import numpy as np
from fastapi import FastAPI, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

# ---------------------------------------------------------------------------
# Internal module imports
# ---------------------------------------------------------------------------
from esg_scoring import compute_esg_composite, simulate_esg_scores
from market_data import get_market_data
from risk_analysis import analyse_risk
from investment_rating import generate_investment_rating

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic response schema
# ---------------------------------------------------------------------------
class AnalysisResponse(BaseModel):
    """Full analysis result returned by GET /analyze/{ticker}."""

    ticker:           str   = Field(..., description="Normalised stock ticker symbol")
    price:            float = Field(..., description="Latest closing price (USD)")
    sector:           str   = Field(..., description="GICS sector classification")

    # ESG breakdown
    environment:      float = Field(..., ge=0, le=100, description="Environmental sub-score (0-100)")
    social:           float = Field(..., ge=0, le=100, description="Social sub-score (0-100)")
    governance:       float = Field(..., ge=0, le=100, description="Governance sub-score (0-100)")
    esg_score:        float = Field(..., ge=0, le=100, description="Weighted composite ESG score (0-100)")

    # Risk metrics
    volatility:       float = Field(..., description="Annualised historical volatility (σ)")
    risk_level:       str   = Field(..., description="Risk tier: LOW | MEDIUM | HIGH")

    # Investment rating
    investment_score: int   = Field(..., ge=0, le=100, description="Blended investment score (0-100)")
    rating:           str   = Field(..., description="Investment Sustainability Rating")

    model_config = {"json_schema_extra": {
        "example": {
            "ticker": "AAPL",
            "price": 189.40,
            "sector": "Technology",
            "environment": 71.34,
            "social": 74.82,
            "governance": 83.56,
            "esg_score": 75.83,
            "volatility": 0.2312,
            "risk_level": "MEDIUM",
            "investment_score": 69,
            "rating": "Sustainable Growth",
        }
    }}


class ErrorResponse(BaseModel):
    """Structured error payload."""
    detail:  str = Field(..., description="Human-readable error message")
    ticker:  str = Field(..., description="The ticker that triggered the error")
    code:    int = Field(..., description="HTTP status code")


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Log startup and shutdown events."""
    logger.info("═" * 60)
    logger.info("  ESG Investment Analyzer API  —  starting up")
    logger.info("  Docs  →  http://localhost:8000/docs")
    logger.info("═" * 60)
    yield
    logger.info("ESG Investment Analyzer API  —  shutting down")


# ---------------------------------------------------------------------------
# FastAPI application factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Real-Time ESG Investment Analyzer",
    description=(
        "A modular fintech API that fetches live stock data, simulates ESG metrics, "
        "analyses financial risk, and generates an Investment Sustainability Rating."
    ),
    version="1.0.0",
    contact={"name": "ESG Analyzer Team"},
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS middleware
# ---------------------------------------------------------------------------
cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:8501")
CORS_ORIGINS = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request timing middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Attach X-Process-Time header to every response."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Process-Time"] = f"{elapsed:.4f}s"
    return response


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.warning("ValueError on %s — %s", request.url.path, exc)
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "code": 422},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s — %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred.", "code": 500},
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root():
    """Health-check / index."""
    return {
        "service": "ESG Investment Analyzer",
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/docs",
    }


@app.get("/health", tags=["System"])
async def health_check():
    """Liveness probe — returns 200 if the service is running."""
    return {"status": "ok"}


@app.get(
    "/analyze/{ticker}",
    response_model=AnalysisResponse,
    responses={
        200: {"description": "Full ESG and risk analysis for the requested ticker"},
        404: {"model": ErrorResponse, "description": "Ticker not found or no data available"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Full ESG Investment Analysis",
    description=(
        "Runs the complete analysis pipeline for a given stock ticker:\n\n"
        "1. **Market Data** — fetches real-time price and 1-year OHLCV history via yfinance\n"
        "2. **ESG Simulation** — generates deterministic Environmental, Social, Governance scores\n"
        "3. **Risk Analysis** — computes annualised volatility and risk tier from historical prices\n"
        "4. **Investment Rating** — fuses ESG score and risk tier into a numeric score and label\n"
    ),
    tags=["Analysis"],
)
async def analyze_ticker(
    ticker: Annotated[
        str,
        Path(
            title="Stock Ticker",
            description="NYSE / NASDAQ stock ticker symbol, e.g. AAPL, TSLA, MSFT, BRK.B",
            min_length=1,
            max_length=10,
            pattern=r"^[A-Za-z0-9.\-]+$",
        ),
    ],
    period: Annotated[
        str,
        Query(
            title="History Period",
            description="yfinance period string for historical data (default: 1y)",
        ),
    ] = "1y",
) -> AnalysisResponse:
    """
    Run the full ESG investment analysis pipeline for ``ticker``.

    Pipeline
    --------
    1. ``market_data.get_market_data``        → price, sector, OHLCV history
    2. ``simulate_esg_scores``                → environment, social, governance
    3. ``compute_esg_composite``              → weighted ESG score
    4. ``risk_analysis.analyse_risk``         → volatility, risk_level
    5. ``investment_rating.generate_investment_rating`` → investment_score, rating
    """
    ticker = ticker.strip().upper()
    logger.info("── /analyze/%s — pipeline start ──", ticker)

    # ── Step 1: Market Data (Threadpool execution for blocking I/O) ──────────
    try:
        market = await run_in_threadpool(get_market_data, ticker)
    except ValueError as exc:
        logger.warning("Market data unavailable for '%s': %s", ticker, exc)
        raise HTTPException(
            status_code=404,
            detail=f"No market data found for ticker '{ticker}'. "
                   f"Verify the symbol is listed on a supported exchange.",
        )
    except Exception as exc:
        logger.error("Unexpected error fetching market data for '%s': %s", ticker, exc, exc_info=True)
        raise HTTPException(
            status_code=502,
            detail="Failed to retrieve market data from the upstream provider.",
        )

    price   = market["price"]
    sector  = market["sector"]
    history = market["historical_prices"]

    if not history:
        raise HTTPException(
            status_code=404,
            detail=f"Historical price data is unavailable for '{ticker}'.",
        )

    # ── Step 2: ESG Simulation ─────────────────────────────────────────────
    esg_sub = simulate_esg_scores(ticker, sector)
    esg_score = compute_esg_composite(
        esg_sub["environment"],
        esg_sub["social"],
        esg_sub["governance"],
    )
    logger.info(
        "ESG  E=%.1f  S=%.1f  G=%.1f  composite=%.1f",
        esg_sub["environment"], esg_sub["social"],
        esg_sub["governance"], esg_score,
    )

    # ── Step 3: Risk Analysis ──────────────────────────────────────────────
    close_prices = [day["close"] for day in history]
    try:
        risk = analyse_risk(close_prices)
    except ValueError as exc:
        logger.warning("Risk analysis failed for '%s': %s", ticker, exc)
        raise HTTPException(status_code=422, detail=str(exc))

    logger.info(
        "Risk  volatility=%.4f  risk_level=%s",
        risk["volatility"], risk["risk_level"],
    )

    # ── Step 4: Investment Rating ──────────────────────────────────────────
    try:
        rating_result = generate_investment_rating(
            esg_score=esg_score,
            risk_level=risk["risk_level"],
        )
    except (TypeError, ValueError) as exc:
        logger.error("Rating generation failed for '%s': %s", ticker, exc)
        raise HTTPException(status_code=422, detail=str(exc))

    logger.info(
        "Rating  score=%d  label=%s",
        rating_result["investment_score"], rating_result["rating"],
    )

    # ── Assemble and return ────────────────────────────────────────────────
    logger.info("── /analyze/%s — pipeline complete ──", ticker)

    return AnalysisResponse(
        ticker           = ticker,
        price            = price,
        sector           = sector,
        environment      = esg_sub["environment"],
        social           = esg_sub["social"],
        governance       = esg_sub["governance"],
        esg_score        = esg_score,
        volatility       = risk["volatility"],
        risk_level       = risk["risk_level"],
        investment_score = rating_result["investment_score"],
        rating           = rating_result["rating"],
    )
