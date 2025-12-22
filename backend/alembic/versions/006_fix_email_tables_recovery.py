"""fix_email_tables_recovery

Recovery migration to create email tables and enum types that may have been
missed if migration 005 failed after updating alembic_version.

This migration is idempotent - it checks if objects exist before creating them.

Revision ID: 006
Revises: 005
Create Date: 2025-12-22 04:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Idempotent migration to ensure email_settings and email_logs tables exist.
    This handles the case where migration 005 partially failed but alembic_version
    was already updated to 005.
    """
    connection = op.get_bind()

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
        # Define enum types for table columns (create_type=False since we created them above)
        email_type_enum = postgresql.ENUM(
            'campaign_report',
            'daily_summary',
            'weekly_summary',
            'campaign_completed',
            'system_alert',
            'test',
            name='emailtype',
            create_type=False
        )

        email_status_enum = postgresql.ENUM(
            'pending',
            'sending',
            'sent',
            'failed',
            'bounced',
            name='emailstatus',
            create_type=False
        )

        # Create email_settings table
        op.create_table(
            'email_settings',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False, unique=True),
            sa.Column('smtp_host', sa.String(255), nullable=False),
            sa.Column('smtp_port', sa.Integer(), nullable=False, server_default='587'),
            sa.Column('smtp_username', sa.String(255), nullable=False),
            sa.Column('smtp_password_encrypted', sa.String(500), nullable=False),
            sa.Column('from_email', sa.String(255), nullable=False),
            sa.Column('from_name', sa.String(100), nullable=False, server_default='SIP Auto-Dialer'),
            sa.Column('use_tls', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('use_ssl', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('last_test_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_test_success', sa.Boolean(), nullable=True),
            sa.Column('last_test_error', sa.String(500), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        )

    # Check if email_logs table exists
    result = connection.execute(sa.text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'email_logs'
    """))
    if not result.fetchone():
        email_type_enum = postgresql.ENUM(
            'campaign_report',
            'daily_summary',
            'weekly_summary',
            'campaign_completed',
            'system_alert',
            'test',
            name='emailtype',
            create_type=False
        )

        email_status_enum = postgresql.ENUM(
            'pending',
            'sending',
            'sent',
            'failed',
            'bounced',
            name='emailstatus',
            create_type=False
        )

        # Create email_logs table
        op.create_table(
            'email_logs',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False, index=True),
            sa.Column('recipient_email', sa.String(255), nullable=False, index=True),
            sa.Column('subject', sa.String(500), nullable=False),
            sa.Column('email_type', email_type_enum, nullable=False, index=True),
            sa.Column('status', email_status_enum, nullable=False, server_default='pending', index=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('campaign_id', sa.String(36), sa.ForeignKey('campaigns.id'), nullable=True, index=True),
            sa.Column('report_schedule_id', sa.String(36), nullable=True),
            sa.Column('smtp_message_id', sa.String(255), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        )

        # Create indexes
        op.create_index('ix_email_logs_org_created', 'email_logs', ['organization_id', 'created_at'])
        op.create_index('ix_email_logs_org_type', 'email_logs', ['organization_id', 'email_type'])


def downgrade() -> None:
    """
    This is a recovery migration - downgrade does nothing since we're just
    ensuring objects from migration 005 exist.
    """
    pass
