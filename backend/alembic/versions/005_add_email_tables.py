"""add_email_tables

Add email_settings and email_logs tables for email functionality.

Revision ID: 005
Revises: 004
Create Date: 2025-12-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Define enum types first
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

    # Create ENUM types using the proper alembic/SQLAlchemy method
    # This ensures proper binding to the connection
    bind = op.get_bind()
    email_type_enum.create(bind, checkfirst=True)
    email_status_enum.create(bind, checkfirst=True)

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
        # Note: report_schedule_id FK removed - report_schedules table created in later migration
        sa.Column('report_schedule_id', sa.String(36), nullable=True),
        sa.Column('smtp_message_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )

    # Create indexes for performance
    op.create_index('ix_email_logs_org_created', 'email_logs', ['organization_id', 'created_at'])
    op.create_index('ix_email_logs_org_type', 'email_logs', ['organization_id', 'email_type'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_email_logs_org_type', table_name='email_logs')
    op.drop_index('ix_email_logs_org_created', table_name='email_logs')

    # Drop tables
    op.drop_table('email_logs')
    op.drop_table('email_settings')

    # Drop ENUM types
    op.execute('DROP TYPE IF EXISTS emailstatus')
    op.execute('DROP TYPE IF EXISTS emailtype')
