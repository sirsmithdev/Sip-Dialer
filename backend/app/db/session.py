"""
Database session management.
"""
import ssl
from contextlib import contextmanager
from typing import AsyncGenerator, Generator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


def get_async_url_and_connect_args():
    """
    Get the async database URL and connect_args for asyncpg.

    asyncpg doesn't accept sslmode parameter - it needs ssl=True or an SSL context.
    We strip sslmode from the URL and return SSL settings separately.
    """
    db_url = settings.async_database_url
    connect_args = {}

    # Check if this is a DO managed database
    use_ssl = "db.ondigitalocean.com" in db_url or "@db-" in db_url

    # Parse URL and remove sslmode parameter (asyncpg doesn't accept it)
    parsed = urlparse(db_url)
    if parsed.query:
        params = parse_qs(parsed.query)
        # Check if sslmode was specified
        if "sslmode" in params:
            sslmode = params.pop("sslmode", [""])[0]
            if sslmode in ("require", "verify-ca", "verify-full"):
                use_ssl = True
        # Remove any ssl parameter too (we'll handle it via connect_args)
        params.pop("ssl", None)
        # Rebuild URL without ssl params
        new_query = urlencode({k: v[0] for k, v in params.items()}, doseq=False) if params else ""
        db_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

    if use_ssl:
        # Create SSL context that doesn't verify certificates (for managed DBs)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_context

    return db_url, connect_args


# Get clean URL and connect_args for async engine
async_db_url, async_connect_args = get_async_url_and_connect_args()

# Check if this is a DO managed database that needs app schema
# Detection: DO domain patterns, port 25060, production environment, or DO database name patterns
import os

# DO App Platform dev databases use patterns like:
# postgresql://db:password@private-xxx.db.ondigitalocean.com:25060/db
# The domain contains .db.ondigitalocean.com or private-* patterns
_is_do_db = (
    "db.ondigitalocean.com" in async_db_url or
    "@db-" in async_db_url or
    ":25060/" in async_db_url or
    "private-" in async_db_url or
    os.environ.get("APP_ENV") == "production"
)

# For DO databases, add server_settings to set search_path
if _is_do_db:
    # Set search_path to look in app schema first, then public
    async_connect_args["server_settings"] = {"search_path": "app, public"}

# Create async engine
engine = create_async_engine(
    async_db_url,
    echo=settings.debug,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args=async_connect_args,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create sync engine for Celery tasks
# For sync engine, we use psycopg2 which handles sslmode differently
sync_db_url = settings.sync_database_url
sync_connect_args = {}

# Also check sync URL for DO detection
_is_do_db_sync = (
    "db.ondigitalocean.com" in sync_db_url or
    "@db-" in sync_db_url or
    ":25060/" in sync_db_url or
    "private-" in sync_db_url or
    os.environ.get("APP_ENV") == "production"
)

# For DO databases, configure SSL and schema
if _is_do_db_sync:
    # psycopg2 uses options parameter for search_path
    sync_connect_args["options"] = "-c search_path=app,public"
    # Add sslmode if not present in URL
    if "sslmode" not in sync_db_url:
        if "?" in sync_db_url:
            sync_db_url += "&sslmode=require"
        else:
            sync_db_url += "?sslmode=require"

sync_engine = create_engine(
    sync_db_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args=sync_connect_args if sync_connect_args else None,
)

# Create sync session factory
sync_session_maker = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """Context manager for synchronous database session (for Celery tasks)."""
    session = sync_session_maker()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
