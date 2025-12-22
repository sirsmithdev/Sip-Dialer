"""fix_email_tables_recovery

Recovery migration to create email tables, enum types, and columns that may have been
missed if migrations 005 or 006 failed after updating alembic_version.

This migration is idempotent - it checks if objects exist before creating them.

Revision ID: 007
Revises: 006
Create Date: 2025-12-22 04:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Idempotent migration to ensure all email-related objects exist.
    This handles the case where migrations 005/006 partially failed but
    alembic_version was already updated.
    """
    connection = op.get_bind()

    # ============================================
    # Fix objects from migration 005
    # ============================================

    # Check and create EmailType ENUM if it doesn't exist
    result = connection.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'emailtype'"))
    if not result.fetchone():
        connection.execute(sa.text("""
            CREATE TYPE emailtype AS ENUM (
                'campaign_report',
                'daily_summary',
                'weekly_summary',
                'campaign_completed',
                'system_alert',
                'test'
            )
        """))

    # Check and create EmailStatus ENUM if it doesn't exist
    result = connection.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'emailstatus'"))
    if not result.fetchone():
        connection.execute(sa.text("""
            CREATE TYPE emailstatus AS ENUM (
                'pending',
                'sending',
                'sent',
                'failed',
                'bounced'
            )
        """))

    # Check if email_settings table exists
    result = connection.execute(sa.text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'email_settings'
    """))
    if not result.fetchone():
        # Create email_settings table
        connection.execute(sa.text("""
            CREATE TABLE email_settings (
                id VARCHAR(36) PRIMARY KEY,
                organization_id VARCHAR(36) NOT NULL UNIQUE REFERENCES organizations(id),
                smtp_host VARCHAR(255),
                smtp_port INTEGER NOT NULL DEFAULT 587,
                smtp_username VARCHAR(255),
                smtp_password_encrypted VARCHAR(500),
                from_email VARCHAR(255) NOT NULL,
                from_name VARCHAR(100) NOT NULL DEFAULT 'SIP Auto-Dialer',
                use_tls BOOLEAN NOT NULL DEFAULT true,
                use_ssl BOOLEAN NOT NULL DEFAULT false,
                is_active BOOLEAN NOT NULL DEFAULT false,
                last_test_at TIMESTAMP WITH TIME ZONE,
                last_test_success BOOLEAN,
                last_test_error VARCHAR(500),
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """))

    # Check if email_logs table exists
    result = connection.execute(sa.text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'email_logs'
    """))
    if not result.fetchone():
        # Create email_logs table
        connection.execute(sa.text("""
            CREATE TABLE email_logs (
                id VARCHAR(36) PRIMARY KEY,
                organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id),
                recipient_email VARCHAR(255) NOT NULL,
                subject VARCHAR(500) NOT NULL,
                email_type emailtype NOT NULL,
                status emailstatus NOT NULL DEFAULT 'pending',
                error_message TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                sent_at TIMESTAMP WITH TIME ZONE,
                campaign_id VARCHAR(36) REFERENCES campaigns(id),
                report_schedule_id VARCHAR(36),
                smtp_message_id VARCHAR(255),
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """))
        # Create indexes
        connection.execute(sa.text("CREATE INDEX ix_email_logs_organization_id ON email_logs(organization_id)"))
        connection.execute(sa.text("CREATE INDEX ix_email_logs_recipient_email ON email_logs(recipient_email)"))
        connection.execute(sa.text("CREATE INDEX ix_email_logs_email_type ON email_logs(email_type)"))
        connection.execute(sa.text("CREATE INDEX ix_email_logs_status ON email_logs(status)"))
        connection.execute(sa.text("CREATE INDEX ix_email_logs_campaign_id ON email_logs(campaign_id)"))
        connection.execute(sa.text("CREATE INDEX ix_email_logs_org_created ON email_logs(organization_id, created_at)"))
        connection.execute(sa.text("CREATE INDEX ix_email_logs_org_type ON email_logs(organization_id, email_type)"))

    # ============================================
    # Fix objects from migration 006
    # ============================================

    # Check and create email_provider ENUM if it doesn't exist
    result = connection.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'email_provider'"))
    if not result.fetchone():
        connection.execute(sa.text("""
            CREATE TYPE email_provider AS ENUM ('smtp', 'resend')
        """))

    # Check if provider column exists in email_settings
    result = connection.execute(sa.text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'email_settings' AND column_name = 'provider'
    """))
    if not result.fetchone():
        connection.execute(sa.text("""
            ALTER TABLE email_settings ADD COLUMN provider email_provider NOT NULL DEFAULT 'resend'
        """))

    # Check if resend_api_key_encrypted column exists in email_settings
    result = connection.execute(sa.text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'email_settings' AND column_name = 'resend_api_key_encrypted'
    """))
    if not result.fetchone():
        connection.execute(sa.text("""
            ALTER TABLE email_settings ADD COLUMN resend_api_key_encrypted VARCHAR(500)
        """))


def downgrade() -> None:
    """
    This is a recovery migration - downgrade does nothing since we're just
    ensuring objects from migrations 005 and 006 exist.
    """
    pass
