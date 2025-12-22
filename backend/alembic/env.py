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


def do_run_migrations(connection: Connection, schema_name: str = None) -> None:
    """Run migrations with a connection."""
    import logging
    logger = logging.getLogger("alembic.env")

    if schema_name:
        logger.info(f"Configuring alembic to use '{schema_name}' schema for version table and tables")
        # Configure alembic to use the target schema for version table
        # The search_path was already set via server_settings in connect_args
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=schema_name,
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
    import os
    import sys

    # Use print for debugging since alembic logging may not be configured yet
    def debug(msg):
        print(f"[ALEMBIC-DEBUG] {msg}", file=sys.stderr, flush=True)

    # Check if this is a DO App Platform database
    # Detection: check URL patterns, port 25060, or explicit env var
    is_do_db = (
        "db.ondigitalocean.com" in db_url or
        "@db-" in db_url or
        ":25060/" in db_url or
        os.environ.get("APP_ENV") == "production"
    )

    debug(f"Database URL (masked): ...{db_url[-50:] if len(db_url) > 50 else db_url}")
    debug(f"Detected as DO database: {is_do_db}, use_ssl: {use_ssl}")
    debug(f"APP_ENV: {os.environ.get('APP_ENV', 'not set')}")

    # Build connect_args for SSL if needed
    connect_args = {}
    if use_ssl:
        # Create SSL context that doesn't verify certificates (for managed DBs)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_context

    # For DO databases, find a schema we can write to
    target_schema = None  # None means use default (public)

    if is_do_db:
        debug("DO database detected - finding writable schema")
        import asyncpg

        parsed = urlparse(db_url)
        db_name = parsed.path.lstrip('/')
        debug(f"Connecting to: {parsed.hostname}:{parsed.port or 5432}/{db_name}")
        try:
            # Connect directly with asyncpg to check schemas
            ssl_arg = connect_args.get("ssl", False) if use_ssl else False
            debug(f"Using SSL: {bool(ssl_arg)}")
            conn = await asyncpg.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=db_name,
                ssl=ssl_arg
            )
            try:
                # List all available schemas
                schemas = await conn.fetch(
                    "SELECT schema_name FROM information_schema.schemata ORDER BY schema_name"
                )
                schema_list = [r['schema_name'] for r in schemas]
                debug(f"Available schemas: {schema_list}")

                # Check current search_path
                search_path = await conn.fetchval("SHOW search_path")
                debug(f"Current search_path: {search_path}")

                # DO App Platform dev databases use a schema matching the database name
                # or the username. Let's check for common patterns.
                username = parsed.username

                # Priority order for schema selection:
                # 1. Schema matching database name (DO convention for dev DBs)
                # 2. Schema matching username
                # 3. 'app' schema
                # 4. Try to create 'app' schema
                # 5. Fall back to public

                for candidate in [db_name, username, 'app']:
                    if candidate in schema_list:
                        debug(f"Found candidate schema: '{candidate}'")
                        # Test if we can write to this schema
                        try:
                            test_table = f'"{candidate}"._alembic_test_{os.getpid()}'
                            await conn.execute(f"CREATE TABLE {test_table} (id int)")
                            await conn.execute(f"DROP TABLE {test_table}")
                            debug(f"Schema '{candidate}' is writable!")
                            target_schema = candidate
                            break
                        except Exception as test_err:
                            debug(f"Schema '{candidate}' not writable: {test_err}")
                            continue

                # If no existing schema works, try to create 'app'
                if not target_schema:
                    try:
                        await conn.execute("CREATE SCHEMA IF NOT EXISTS app")
                        debug("Created 'app' schema successfully")
                        target_schema = 'app'
                    except Exception as schema_err:
                        debug(f"Cannot create app schema: {schema_err}")

                # Last resort: try public
                if not target_schema:
                    try:
                        test_table = f'public._alembic_test_{os.getpid()}'
                        await conn.execute(f"CREATE TABLE {test_table} (id int)")
                        await conn.execute(f"DROP TABLE {test_table}")
                        debug("'public' schema is writable")
                        target_schema = None  # Use default
                    except Exception as pub_err:
                        debug(f"WARNING: 'public' schema also not writable: {pub_err}")
                        debug("Migrations may fail!")

            finally:
                await conn.close()
        except Exception as e:
            debug(f"ERROR: Could not connect to check schemas: {type(e).__name__}: {e}")
            import traceback
            debug(f"Traceback: {traceback.format_exc()}")

        if target_schema:
            connect_args["server_settings"] = {"search_path": f"{target_schema},public"}
            debug(f"Using '{target_schema}' schema - setting search_path to {target_schema},public")
        else:
            debug("Using default 'public' schema")
    else:
        debug("Not a DO database, using public schema")

    connectable = create_async_engine(
        db_url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        # Pass the target schema to configure alembic correctly
        await connection.run_sync(lambda conn: do_run_migrations(conn, target_schema))

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
