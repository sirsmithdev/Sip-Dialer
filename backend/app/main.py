"""
SIP Auto-Dialer API - Main Application Entry Point
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router
from app.api.websocket_manager import manager as ws_manager
from app.db.session import engine
from app.db.base import Base

logger = logging.getLogger(__name__)

# Log S3 configuration at module load time for debugging (using print for visibility)
print("=" * 60)
print("S3 CONFIGURATION DEBUG (from settings)")
print(f"  s3_endpoint: {settings.s3_endpoint}")
print(f"  s3_bucket: {settings.s3_bucket}")
print(f"  s3_secure: {settings.s3_secure} (type: {type(settings.s3_secure).__name__})")
print(f"  s3_region: {settings.s3_region}")
print(f"  s3_access_key: {settings.s3_access_key[:8]}..." if settings.s3_access_key else "  s3_access_key: None")
print("S3 CONFIGURATION DEBUG (from env vars)")
print(f"  S3_ENDPOINT env: {os.environ.get('S3_ENDPOINT', 'NOT SET')}")
print(f"  S3_SECURE env: {os.environ.get('S3_SECURE', 'NOT SET')}")
print(f"  S3_BUCKET env: {os.environ.get('S3_BUCKET', 'NOT SET')}")
print(f"  S3_REGION env: {os.environ.get('S3_REGION', 'NOT SET')}")
print("=" * 60)


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


@app.get("/api/v1/debug/s3-config")
async def debug_s3_config():
    """Debug endpoint to check S3 configuration (remove in production)."""
    return {
        "settings": {
            "s3_endpoint": settings.s3_endpoint,
            "s3_bucket": settings.s3_bucket,
            "s3_secure": settings.s3_secure,
            "s3_secure_type": type(settings.s3_secure).__name__,
            "s3_region": settings.s3_region,
            "s3_access_key_preview": settings.s3_access_key[:8] + "..." if settings.s3_access_key else None,
        },
        "env_vars": {
            "S3_ENDPOINT": os.environ.get("S3_ENDPOINT", "NOT SET"),
            "S3_BUCKET": os.environ.get("S3_BUCKET", "NOT SET"),
            "S3_SECURE": os.environ.get("S3_SECURE", "NOT SET"),
            "S3_REGION": os.environ.get("S3_REGION", "NOT SET"),
            "S3_ACCESS_KEY_PREVIEW": (os.environ.get("S3_ACCESS_KEY", "")[:8] + "...") if os.environ.get("S3_ACCESS_KEY") else "NOT SET",
        }
    }


@app.get("/")
async def root():
    """Root endpoint redirect to API docs."""
    return {
        "message": "SIP Auto-Dialer API",
        "docs": "/api/docs",
        "health": "/api/v1/health",
    }


@app.post("/api/v1/setup/init-admin")
async def init_admin():
    """
    Initialize admin user if not exists.
    This endpoint can only create the admin if no users exist yet.
    """
    from sqlalchemy import select, text
    from app.db.session import async_session_maker
    from app.models.user import User, Organization
    from app.core.security import get_password_hash
    import uuid

    async with async_session_maker() as session:
        try:
            # Check if any users exist
            result = await session.execute(select(User).limit(1))
            existing_user = result.scalar_one_or_none()

            if existing_user:
                return {
                    "status": "skipped",
                    "message": "Users already exist. Admin creation not allowed via this endpoint."
                }

            # Create default organization first
            result = await session.execute(
                select(Organization).where(Organization.slug == "default")
            )
            org = result.scalar_one_or_none()

            if not org:
                org = Organization(
                    name="Default Organization",
                    slug="default",
                    is_active=True,
                    max_concurrent_calls=10,
                    timezone="UTC"
                )
                session.add(org)
                await session.flush()

            # Create admin user via raw SQL to avoid enum issues
            hashed_pwd = get_password_hash("admin123")
            user_id = str(uuid.uuid4())
            await session.execute(
                text("""
                    INSERT INTO users (id, email, hashed_password, first_name, last_name,
                                       is_active, is_superuser, role, organization_id)
                    VALUES (:id, :email, :hashed_password, :first_name, :last_name,
                            :is_active, :is_superuser, :role, :organization_id)
                """),
                {
                    "id": user_id,
                    "email": "admin@example.com",
                    "hashed_password": hashed_pwd,
                    "first_name": "Admin",
                    "last_name": "User",
                    "is_active": True,
                    "is_superuser": True,
                    "role": "admin",
                    "organization_id": str(org.id)
                }
            )

            await session.commit()
            return {
                "status": "success",
                "message": "Admin user created successfully",
                "credentials": {
                    "email": "admin@example.com",
                    "password": "admin123"
                }
            }
        except Exception as e:
            logger.error(f"Admin creation failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
