"""fix_sip_settings_enums

Recovery migration to convert sip_transport and connection_status columns
from VARCHAR to proper PostgreSQL ENUM types.

The initial migration 001 created these as VARCHAR columns, but the SQLAlchemy
model uses ENUM types. This migration:
1. Creates the ENUM types if they don't exist
2. Alters the columns to use the ENUM types

Revision ID: 008
Revises: 007
Create Date: 2025-12-22 05:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Convert sip_transport and connection_status from VARCHAR to ENUM types.
    This is idempotent - it checks if conversion is needed before proceeding.
    """
    connection = op.get_bind()

    # ============================================
    # Create SIPTransport ENUM if it doesn't exist
    # ============================================
    result = connection.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'siptransport'"))
    if not result.fetchone():
        connection.execute(sa.text("""
            CREATE TYPE siptransport AS ENUM ('UDP', 'TCP', 'TLS')
        """))

    # ============================================
    # Create ConnectionStatus ENUM if it doesn't exist
    # ============================================
    result = connection.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'connectionstatus'"))
    if not result.fetchone():
        connection.execute(sa.text("""
            CREATE TYPE connectionstatus AS ENUM (
                'DISCONNECTED',
                'CONNECTING',
                'CONNECTED',
                'REGISTERED',
                'FAILED'
            )
        """))

    # ============================================
    # Check if sip_transport column needs conversion
    # ============================================
    result = connection.execute(sa.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'sip_settings' AND column_name = 'sip_transport'
    """))
    row = result.fetchone()
    if row and row[0] in ('character varying', 'character', 'text'):
        # Column is VARCHAR, need to convert to ENUM
        # First, update any NULL or invalid values to 'UDP'
        connection.execute(sa.text("""
            UPDATE sip_settings
            SET sip_transport = 'UDP'
            WHERE sip_transport IS NULL OR sip_transport NOT IN ('UDP', 'TCP', 'TLS')
        """))

        # Alter column type to ENUM
        connection.execute(sa.text("""
            ALTER TABLE sip_settings
            ALTER COLUMN sip_transport TYPE siptransport
            USING sip_transport::siptransport
        """))

        # Set default
        connection.execute(sa.text("""
            ALTER TABLE sip_settings
            ALTER COLUMN sip_transport SET DEFAULT 'UDP'::siptransport
        """))

    # ============================================
    # Check if connection_status column needs conversion
    # ============================================
    result = connection.execute(sa.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'sip_settings' AND column_name = 'connection_status'
    """))
    row = result.fetchone()
    if row and row[0] in ('character varying', 'character', 'text'):
        # Column is VARCHAR, need to convert to ENUM
        # First, normalize values - the database might have lowercase values
        connection.execute(sa.text("""
            UPDATE sip_settings
            SET connection_status = UPPER(connection_status)
            WHERE connection_status IS NOT NULL
        """))

        # Update any invalid values to 'DISCONNECTED'
        connection.execute(sa.text("""
            UPDATE sip_settings
            SET connection_status = 'DISCONNECTED'
            WHERE connection_status IS NULL
               OR connection_status NOT IN ('DISCONNECTED', 'CONNECTING', 'CONNECTED', 'REGISTERED', 'FAILED')
        """))

        # Alter column type to ENUM
        connection.execute(sa.text("""
            ALTER TABLE sip_settings
            ALTER COLUMN connection_status TYPE connectionstatus
            USING connection_status::connectionstatus
        """))

        # Set default
        connection.execute(sa.text("""
            ALTER TABLE sip_settings
            ALTER COLUMN connection_status SET DEFAULT 'DISCONNECTED'::connectionstatus
        """))


def downgrade() -> None:
    """
    Convert columns back to VARCHAR if needed.
    This is a recovery migration - downgrade may not be fully reversible.
    """
    connection = op.get_bind()

    # Convert sip_transport back to VARCHAR
    result = connection.execute(sa.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'sip_settings' AND column_name = 'sip_transport'
    """))
    row = result.fetchone()
    if row and row[0] == 'USER-DEFINED':
        connection.execute(sa.text("""
            ALTER TABLE sip_settings
            ALTER COLUMN sip_transport TYPE VARCHAR(10)
            USING sip_transport::text
        """))

    # Convert connection_status back to VARCHAR
    result = connection.execute(sa.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'sip_settings' AND column_name = 'connection_status'
    """))
    row = result.fetchone()
    if row and row[0] == 'USER-DEFINED':
        connection.execute(sa.text("""
            ALTER TABLE sip_settings
            ALTER COLUMN connection_status TYPE VARCHAR(20)
            USING connection_status::text
        """))
