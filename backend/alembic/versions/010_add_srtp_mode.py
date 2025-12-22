"""add_srtp_mode

Add srtp_mode column to sip_settings table for SRTP (Secure RTP)
media encryption configuration.

SRTP modes:
- DISABLED: No SRTP, use regular RTP
- OPTIONAL: Use SRTP if available, fallback to RTP
- MANDATORY: Require SRTP, fail if not available

Revision ID: 010
Revises: 009
Create Date: 2025-12-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '010'
down_revision: Union[str, None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add srtp_mode ENUM type and column to sip_settings."""
    connection = op.get_bind()

    # Create SRTPMode ENUM type if it doesn't exist
    result = connection.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'srtpmode'"))
    if not result.fetchone():
        connection.execute(sa.text("""
            CREATE TYPE srtpmode AS ENUM ('DISABLED', 'OPTIONAL', 'MANDATORY')
        """))

    # Check if srtp_mode column already exists
    result = connection.execute(sa.text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'sip_settings' AND column_name = 'srtp_mode'
    """))
    if not result.fetchone():
        # Add srtp_mode column with default OPTIONAL
        connection.execute(sa.text("""
            ALTER TABLE sip_settings
            ADD COLUMN srtp_mode srtpmode DEFAULT 'OPTIONAL'::srtpmode
        """))


def downgrade() -> None:
    """Remove srtp_mode column and ENUM type."""
    connection = op.get_bind()

    # Drop the column if it exists
    result = connection.execute(sa.text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'sip_settings' AND column_name = 'srtp_mode'
    """))
    if result.fetchone():
        connection.execute(sa.text("""
            ALTER TABLE sip_settings DROP COLUMN srtp_mode
        """))

    # Drop the ENUM type if it exists
    result = connection.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'srtpmode'"))
    if result.fetchone():
        connection.execute(sa.text("DROP TYPE srtpmode"))
