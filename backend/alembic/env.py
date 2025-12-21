"""
Alembic environment configuration.
"""
import asyncio
import ssl
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


def get_async_url_and_ssl():
    """
    Get the async database URL and SSL context for asyncpg.

    asyncpg doesn't accept sslmode parameter - it needs ssl=True or an SSL context.
    We strip sslmode from the URL and return SSL settings separately.
    """
    db_url = settings.async_database_url
    use_ssl = False

    # Check if this is a DO managed database
    if "db.ondigitalocean.com" in db_url or "@db-" in db_url:
        use_ssl = True

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

    return db_url, use_ssl


# Get clean URL and SSL settings
db_url, use_ssl = get_async_url_and_ssl()
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


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with a connection."""
    from sqlalchemy import text
    import logging
    logger = logging.getLogger("alembic.env")

    use_app_schema = False

    # Check if this is a DO App Platform database
    is_do_db = "db.ondigitalocean.com" in db_url or "@db-" in db_url

    if is_do_db:
        # For DO App Platform dev databases, we need to handle potential schema permission issues
        # The database is fresh but public schema may have restricted CREATE permissions
        # Solution: Create our own schema that we own
        try:
            # Try to create 'app' schema in its own transaction (autocommit mode)
            connection.execute(text("COMMIT"))  # End any existing transaction
            connection.execute(text("CREATE SCHEMA IF NOT EXISTS app"))
            connection.execute(text("SET search_path TO app, public"))
            logger.info("Using 'app' schema for database tables")
            use_app_schema = True
        except Exception as e:
            logger.warning(f"Could not create app schema: {e}")
            # Rollback any failed transaction and try with public schema
            try:
                connection.execute(text("ROLLBACK"))
            except Exception:
                pass

    if use_app_schema:
        # Configure alembic to use app schema for version table
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema="app",
            include_schemas=True,
        )
    else:
        # Use default public schema
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    import logging
    logger = logging.getLogger("alembic.env")

    # Check if this is a DO App Platform database
    is_do_db = "db.ondigitalocean.com" in db_url or "@db-" in db_url

    # Build connect_args for SSL if needed
    connect_args = {}
    if use_ssl:
        # Create SSL context that doesn't verify certificates (for managed DBs)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_context

    # For DO databases, first create the app schema, then set search_path
    if is_do_db:
        logger.info("DO database detected - creating app schema first")
        # First connection: create the schema
        import asyncpg
        from urllib.parse import urlparse

        parsed = urlparse(db_url)
        try:
            # Connect directly with asyncpg to create schema
            conn = await asyncpg.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip('/'),
                ssl=connect_args.get("ssl", False) if use_ssl else False
            )
            try:
                await conn.execute("CREATE SCHEMA IF NOT EXISTS app")
                logger.info("Created 'app' schema successfully")
            finally:
                await conn.close()
        except Exception as e:
            logger.warning(f"Could not create app schema: {e}")

        # Now set server_settings to use the app schema
        connect_args["server_settings"] = {"search_path": "app,public"}
        logger.info("Setting search_path to app,public via server_settings")

    connectable = create_async_engine(
        db_url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
