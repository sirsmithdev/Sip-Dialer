"""Add compliance tracking tables

Revision ID: 011
Revises: 010
Create Date: 2024-12-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '011'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create dnc_check_logs table for tracking DNC compliance checks
    op.create_table(
        'dnc_check_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('campaign_id', sa.String(36), sa.ForeignKey('campaigns.id'), nullable=True, index=True),
        sa.Column('phone_number', sa.String(20), nullable=False, index=True),
        sa.Column('contact_id', sa.String(36), sa.ForeignKey('contacts.id'), nullable=True),
        sa.Column('is_on_dnc', sa.Boolean(), nullable=False, default=False),
        sa.Column('dnc_entry_id', sa.String(36), sa.ForeignKey('dnc_entries.id'), nullable=True),
        sa.Column('call_blocked', sa.Boolean(), nullable=False, default=False),
        sa.Column('check_source', sa.String(50), nullable=False, default='dialer'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create compliance_violations table for tracking all compliance violations
    op.create_table(
        'compliance_violations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('campaign_id', sa.String(36), sa.ForeignKey('campaigns.id'), nullable=True, index=True),
        sa.Column('call_log_id', sa.String(36), sa.ForeignKey('call_logs.id'), nullable=True),
        sa.Column('phone_number', sa.String(20), nullable=False, index=True),
        sa.Column('violation_type', sa.String(50), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False, default='medium'),
        sa.Column('is_reviewed', sa.Boolean(), nullable=False, default=False),
        sa.Column('reviewed_by_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes for efficient querying
    op.create_index(
        'ix_dnc_check_logs_org_created',
        'dnc_check_logs',
        ['organization_id', 'created_at']
    )
    op.create_index(
        'ix_dnc_check_logs_campaign_created',
        'dnc_check_logs',
        ['campaign_id', 'created_at']
    )
    op.create_index(
        'ix_dnc_check_logs_is_on_dnc',
        'dnc_check_logs',
        ['organization_id', 'is_on_dnc']
    )
    op.create_index(
        'ix_compliance_violations_org_created',
        'compliance_violations',
        ['organization_id', 'created_at']
    )
    op.create_index(
        'ix_compliance_violations_type',
        'compliance_violations',
        ['organization_id', 'violation_type']
    )
    op.create_index(
        'ix_compliance_violations_unreviewed',
        'compliance_violations',
        ['organization_id', 'is_reviewed'],
        postgresql_where=sa.text('is_reviewed = false')
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_compliance_violations_unreviewed', table_name='compliance_violations')
    op.drop_index('ix_compliance_violations_type', table_name='compliance_violations')
    op.drop_index('ix_compliance_violations_org_created', table_name='compliance_violations')
    op.drop_index('ix_dnc_check_logs_is_on_dnc', table_name='dnc_check_logs')
    op.drop_index('ix_dnc_check_logs_campaign_created', table_name='dnc_check_logs')
    op.drop_index('ix_dnc_check_logs_org_created', table_name='dnc_check_logs')

    # Drop tables
    op.drop_table('compliance_violations')
    op.drop_table('dnc_check_logs')
