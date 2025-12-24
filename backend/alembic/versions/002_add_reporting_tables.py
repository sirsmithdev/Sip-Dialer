"""Add reporting tables

Revision ID: 002
Revises: 001
Create Date: 2024-01-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM types for reporting using op.execute to avoid async issues
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reporttype') THEN
                CREATE TYPE reporttype AS ENUM (
                    'CALL_ANALYTICS',
                    'CAMPAIGN_PERFORMANCE',
                    'CONTACT_LIST_QUALITY',
                    'REAL_TIME_MONITORING',
                    'IVR_SURVEY_ANALYTICS',
                    'COMPLIANCE_QUALITY'
                );
            END IF;
        END$$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reportformat') THEN
                CREATE TYPE reportformat AS ENUM (
                    'JSON',
                    'CSV',
                    'EXCEL',
                    'PDF'
                );
            END IF;
        END$$;
    """)

    # Create enum objects for table definitions
    report_type_enum = postgresql.ENUM(
        'CALL_ANALYTICS',
        'CAMPAIGN_PERFORMANCE',
        'CONTACT_LIST_QUALITY',
        'REAL_TIME_MONITORING',
        'IVR_SURVEY_ANALYTICS',
        'COMPLIANCE_QUALITY',
        name='reporttype',
        create_type=False
    )

    report_format_enum = postgresql.ENUM(
        'JSON',
        'CSV',
        'EXCEL',
        'PDF',
        name='reportformat',
        create_type=False
    )

    # Create report_schedules table
    op.create_table(
        'report_schedules',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('report_type', report_type_enum, nullable=False),
        sa.Column('format', report_format_enum, nullable=False),
        sa.Column('schedule_cron', sa.String(100), nullable=False, comment='Cron expression'),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('recipients_json', postgresql.JSON(), nullable=False, default=[]),
        sa.Column('filters_json', postgresql.JSON(), nullable=False, default={}),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('last_execution_status', sa.String(20), nullable=True),
        sa.Column('created_by_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create report_executions table
    op.create_table(
        'report_executions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('report_schedule_id', sa.String(36), sa.ForeignKey('report_schedules.id'), nullable=True, index=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('report_type', report_type_enum, nullable=False),
        sa.Column('format', report_format_enum, nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='PENDING'),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('execution_time_seconds', sa.Float(), nullable=True),
        sa.Column('records_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.String(1000), nullable=True),
        sa.Column('generated_by_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('filters_json', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes
    op.create_index('ix_report_schedules_organization_active', 'report_schedules', ['organization_id', 'is_active'])
    op.create_index('ix_report_executions_organization_created', 'report_executions', ['organization_id', 'created_at'])


def downgrade() -> None:
    # Drop tables
    op.drop_index('ix_report_executions_organization_created', table_name='report_executions')
    op.drop_index('ix_report_schedules_organization_active', table_name='report_schedules')
    op.drop_table('report_executions')
    op.drop_table('report_schedules')

    # Drop ENUM types
    op.execute('DROP TYPE IF EXISTS reportformat')
    op.execute('DROP TYPE IF EXISTS reporttype')
