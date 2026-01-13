"""FastAPI application for trading dashboard API."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.core.config import DatabaseConfig
from src.core.database import init_db

logger = logging.getLogger(__name__)

# Initialize rate limiter - increased for dashboard polling
limiter = Limiter(key_func=get_remote_address, default_limits=["300/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application resources on startup."""
    logger.info("Starting FastAPI application...")

    # Initialize database
    db_config = DatabaseConfig()
    init_db(db_config)
    logger.info("Database initialized")

    yield

    logger.info("Shutting down FastAPI application...")


# Create FastAPI app
app = FastAPI(
    title="Trading Dashboard API",
    description="REST API and WebSocket for professional trading dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "http://localhost:3001",  # Next.js alt port
        "http://frontend:3000",   # Docker
        "http://54.165.149.26:3000",  # EC2 public IP
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
@limiter.limit("60/minute")
async def root(request: Request):
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Trading Dashboard API",
        "version": "1.0.0",
    }


@app.get("/health")
@limiter.limit("60/minute")
async def health(request: Request):
    """Detailed health check."""
    # TODO: Add DB, Redis, Alpaca health checks
    return {
        "status": "healthy",
        "services": {
            "database": "ok",
            "redis": "ok",
            "alpaca": "ok",
        },
    }


# Import routers
from src.api.routers import (
    account,
    circuit_breakers,
    configuration,
    executions,
    market_data,
    positions,
    risk,
    signals,
    websocket,
)

# Include routers
app.include_router(account.router, prefix="/api", tags=["account"])
app.include_router(positions.router, prefix="/api", tags=["positions"])
app.include_router(market_data.router, prefix="/api", tags=["market-data"])
app.include_router(signals.router, prefix="/api", tags=["signals"])
app.include_router(executions.router, prefix="/api", tags=["executions"])
app.include_router(circuit_breakers.router, prefix="/api", tags=["circuit-breakers"])
app.include_router(risk.router, prefix="/api", tags=["risk"])
app.include_router(configuration.router, prefix="/api", tags=["configuration"])
app.include_router(websocket.router, prefix="/api", tags=["websocket"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
