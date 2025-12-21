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
sync_engine = create_engine(
    settings.sync_database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
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
