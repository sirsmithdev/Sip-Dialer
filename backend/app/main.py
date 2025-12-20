"""
SIP Auto-Dialer API - Main Application Entry Point
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router
from app.api.websocket_manager import manager as ws_manager
from app.db.session import engine
from app.db.base import Base

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    # Create database tables (in production, use Alembic migrations instead)
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)

    # Start WebSocket Redis subscriber
    await ws_manager.start_redis_subscriber()
    logger.info("WebSocket Redis subscriber started")

    yield

    # Shutdown
    await ws_manager.stop_redis_subscriber()
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description="SIP Auto-Dialer Broadcast Application with IVR Surveys",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "environment": settings.app_env,
    }


@app.get("/")
async def root():
    """Root endpoint redirect to API docs."""
    return {
        "message": "SIP Auto-Dialer API",
        "docs": "/api/docs",
        "health": "/api/v1/health",
    }
