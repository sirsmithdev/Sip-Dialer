"""
Alembic environment configuration.
"""
import asyncio
import ssl
import sys
from logging.config import fileConfig
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Import models and configuration
from app.config import settings
from app.db.base import Base

# Import all models so they're registered with Base.metadata
from app.models import (
    User, Organization, Contact, ContactList, DNCEntry,
    Campaign, CampaignContact, AudioFile, IVRFlow, IVRFlowVersion,
    CallLog, SurveyResponse, SIPSettings
)

# Alembic Config object
config = context.config


def debug(msg):
    """Print debug message to stderr."""
    print(f"[ALEMBIC] {msg}", file=sys.stderr, flush=True)


def get_async_url_and_ssl():
    """
    Get the async database URL, SSL context, and target schema for asyncpg.

    asyncpg doesn't accept sslmode parameter - it needs ssl=True or an SSL context.
    We strip sslmode from the URL and return SSL settings separately.

    For DigitalOcean App Platform dev databases, the only writable schema is one
    that matches the database username (which is also the database name).
    """
    db_url = settings.async_database_url
    use_ssl = False
    target_schema = None  # None means use public schema

    # Parse URL to get components
    parsed = urlparse(db_url)

    # Check if this is a DO managed database
    is_do_db = (
        "db.ondigitalocean.com" in db_url or
        "@db-" in db_url or
        ":25060/" in db_url
    )

    if is_do_db:
        use_ssl = True
        # For DO App Platform dev databases, the writable schema is the username
        # The username is typically the same as the database name
        if parsed.username:
            target_schema = parsed.username
            debug(f"DigitalOcean database detected - will use schema: {target_schema}")
        else:
            debug("DigitalOcean database detected but couldn't extract username")

    # Handle query parameters
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

    return db_url, use_ssl, target_schema


# Get clean URL, SSL settings, and target schema
db_url, use_ssl, target_schema = get_async_url_and_ssl()
config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection, schema_name: str = None) -> None:
    """Run migrations with a connection."""
    from sqlalchemy import text

    if schema_name:
        debug(f"Running migrations in schema: {schema_name}")
        # Set search_path so tables are created in the target schema
        connection.execute(text(f"SET search_path TO {schema_name}, public"))

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=schema_name,
            include_schemas=True,
        )
    else:
        debug("Running migrations in public schema")
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

    with context.begin_transaction():
        context.run_migrations()
    debug("Migrations completed successfully!")


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    debug(f"Database URL (masked): ...{db_url[-50:] if len(db_url) > 50 else db_url}")
    debug(f"use_ssl: {use_ssl}, target_schema: {target_schema}")

    # Build connect_args for SSL and schema
    connect_args = {}
    if use_ssl:
        # Create SSL context that doesn't verify certificates (for managed DBs)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_context
        debug("Using SSL context for database connection")

    # Set search_path for DO databases so tables go in the right schema
    if target_schema:
        connect_args["server_settings"] = {"search_path": f"{target_schema}, public"}
        debug(f"Set search_path to: {target_schema}, public")

    connectable = create_async_engine(
        db_url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(lambda conn: do_run_migrations(conn, target_schema))
    except Exception as e:
        debug(f"Migration error: {type(e).__name__}: {e}")
        import traceback
        debug(f"Traceback:\n{traceback.format_exc()}")
        raise
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
