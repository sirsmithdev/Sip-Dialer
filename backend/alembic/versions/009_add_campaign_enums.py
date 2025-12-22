"""add_campaign_enums

Create PostgreSQL ENUM types for campaign-related enums:
- campaignstatus
- dialingmode
- contactstatus
- calldisposition

These are needed because SQLAlchemy model uses SQLEnum which requires
PostgreSQL ENUM types, but the initial migration used VARCHAR columns.

Revision ID: 009
Revises: 008
Create Date: 2025-12-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create campaign-related ENUM types and convert VARCHAR columns.
    This is idempotent - checks if conversion is needed before proceeding.
    """
    connection = op.get_bind()

    # ============================================
    # Create CampaignStatus ENUM if it doesn't exist
    # ============================================
    result = connection.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'campaignstatus'"))
    if not result.fetchone():
        connection.execute(sa.text("""
            CREATE TYPE campaignstatus AS ENUM (
                'draft', 'scheduled', 'running', 'paused', 'completed', 'cancelled'
            )
        """))

    # ============================================
    # Create DialingMode ENUM if it doesn't exist
    # ============================================
    result = connection.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'dialingmode'"))
    if not result.fetchone():
        connection.execute(sa.text("""
            CREATE TYPE dialingmode AS ENUM ('progressive', 'predictive')
        """))

    # ============================================
    # Create ContactStatus ENUM if it doesn't exist
    # ============================================
    result = connection.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'contactstatus'"))
    if not result.fetchone():
        connection.execute(sa.text("""
            CREATE TYPE contactstatus AS ENUM (
                'pending', 'in_progress', 'completed', 'failed', 'dnc', 'skipped'
            )
        """))

    # ============================================
    # Create CallDisposition ENUM if it doesn't exist
    # ============================================
    result = connection.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'calldisposition'"))
    if not result.fetchone():
        connection.execute(sa.text("""
            CREATE TYPE calldisposition AS ENUM (
                'answered_human', 'answered_machine', 'no_answer', 'busy',
                'failed', 'invalid_number', 'dnc'
            )
        """))

    # ============================================
    # Convert campaigns.status from VARCHAR to ENUM
    # ============================================
    result = connection.execute(sa.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'campaigns' AND column_name = 'status'
    """))
    row = result.fetchone()
    if row and row[0] in ('character varying', 'character', 'text'):
        # Normalize values to lowercase
        connection.execute(sa.text("""
            UPDATE campaigns
            SET status = LOWER(status)
            WHERE status IS NOT NULL
        """))
        # Set default for NULL values
        connection.execute(sa.text("""
            UPDATE campaigns
            SET status = 'draft'
            WHERE status IS NULL
               OR status NOT IN ('draft', 'scheduled', 'running', 'paused', 'completed', 'cancelled')
        """))
        # Alter column type
        connection.execute(sa.text("""
            ALTER TABLE campaigns
            ALTER COLUMN status TYPE campaignstatus
            USING status::campaignstatus
        """))
        connection.execute(sa.text("""
            ALTER TABLE campaigns
            ALTER COLUMN status SET DEFAULT 'draft'::campaignstatus
        """))

    # ============================================
    # Convert campaigns.dialing_mode from VARCHAR to ENUM
    # ============================================
    result = connection.execute(sa.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'campaigns' AND column_name = 'dialing_mode'
    """))
    row = result.fetchone()
    if row and row[0] in ('character varying', 'character', 'text'):
        # Normalize values to lowercase
        connection.execute(sa.text("""
            UPDATE campaigns
            SET dialing_mode = LOWER(dialing_mode)
            WHERE dialing_mode IS NOT NULL
        """))
        # Set default for NULL values
        connection.execute(sa.text("""
            UPDATE campaigns
            SET dialing_mode = 'progressive'
            WHERE dialing_mode IS NULL OR dialing_mode NOT IN ('progressive', 'predictive')
        """))
        # Alter column type
        connection.execute(sa.text("""
            ALTER TABLE campaigns
            ALTER COLUMN dialing_mode TYPE dialingmode
            USING dialing_mode::dialingmode
        """))
        connection.execute(sa.text("""
            ALTER TABLE campaigns
            ALTER COLUMN dialing_mode SET DEFAULT 'progressive'::dialingmode
        """))

    # ============================================
    # Convert campaign_contacts.status from VARCHAR to ENUM
    # ============================================
    result = connection.execute(sa.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'campaign_contacts' AND column_name = 'status'
    """))
    row = result.fetchone()
    if row and row[0] in ('character varying', 'character', 'text'):
        # Normalize values to lowercase
        connection.execute(sa.text("""
            UPDATE campaign_contacts
            SET status = LOWER(status)
            WHERE status IS NOT NULL
        """))
        # Set default for NULL values
        connection.execute(sa.text("""
            UPDATE campaign_contacts
            SET status = 'pending'
            WHERE status IS NULL
               OR status NOT IN ('pending', 'in_progress', 'completed', 'failed', 'dnc', 'skipped')
        """))
        # Alter column type
        connection.execute(sa.text("""
            ALTER TABLE campaign_contacts
            ALTER COLUMN status TYPE contactstatus
            USING status::contactstatus
        """))
        connection.execute(sa.text("""
            ALTER TABLE campaign_contacts
            ALTER COLUMN status SET DEFAULT 'pending'::contactstatus
        """))

    # ============================================
    # Convert campaign_contacts.last_disposition from VARCHAR to ENUM
    # ============================================
    result = connection.execute(sa.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'campaign_contacts' AND column_name = 'last_disposition'
    """))
    row = result.fetchone()
    if row and row[0] in ('character varying', 'character', 'text'):
        # Normalize values to lowercase
        connection.execute(sa.text("""
            UPDATE campaign_contacts
            SET last_disposition = LOWER(last_disposition)
            WHERE last_disposition IS NOT NULL
        """))
        # Set invalid values to NULL (disposition is nullable)
        connection.execute(sa.text("""
            UPDATE campaign_contacts
            SET last_disposition = NULL
            WHERE last_disposition IS NOT NULL
               AND last_disposition NOT IN (
                   'answered_human', 'answered_machine', 'no_answer', 'busy',
                   'failed', 'invalid_number', 'dnc'
               )
        """))
        # Alter column type
        connection.execute(sa.text("""
            ALTER TABLE campaign_contacts
            ALTER COLUMN last_disposition TYPE calldisposition
            USING last_disposition::calldisposition
        """))


def downgrade() -> None:
    """
    Convert columns back to VARCHAR if needed.
    """
    connection = op.get_bind()

    # Convert campaigns.status back to VARCHAR
    result = connection.execute(sa.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'campaigns' AND column_name = 'status'
    """))
    row = result.fetchone()
    if row and row[0] == 'USER-DEFINED':
        connection.execute(sa.text("""
            ALTER TABLE campaigns
            ALTER COLUMN status TYPE VARCHAR(20)
            USING status::text
        """))

    # Convert campaigns.dialing_mode back to VARCHAR
    result = connection.execute(sa.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'campaigns' AND column_name = 'dialing_mode'
    """))
    row = result.fetchone()
    if row and row[0] == 'USER-DEFINED':
        connection.execute(sa.text("""
            ALTER TABLE campaigns
            ALTER COLUMN dialing_mode TYPE VARCHAR(20)
            USING dialing_mode::text
        """))

    # Convert campaign_contacts.status back to VARCHAR
    result = connection.execute(sa.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'campaign_contacts' AND column_name = 'status'
    """))
    row = result.fetchone()
    if row and row[0] == 'USER-DEFINED':
        connection.execute(sa.text("""
            ALTER TABLE campaign_contacts
            ALTER COLUMN status TYPE VARCHAR(20)
            USING status::text
        """))

    # Convert campaign_contacts.last_disposition back to VARCHAR
    result = connection.execute(sa.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'campaign_contacts' AND column_name = 'last_disposition'
    """))
    row = result.fetchone()
    if row and row[0] == 'USER-DEFINED':
        connection.execute(sa.text("""
            ALTER TABLE campaign_contacts
            ALTER COLUMN last_disposition TYPE VARCHAR(30)
            USING last_disposition::text
        """))
