"""add_channel_driver_to_sip_settings

Revision ID: 003
Revises: 002
Create Date: 2025-12-19 01:15:36.539743

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ChannelDriver ENUM type
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'channeldriver') THEN
                CREATE TYPE channeldriver AS ENUM ('PJSIP', 'SIP');
            END IF;
        END$$;
    """)

    # Create enum object for column definition
    channel_driver_enum = postgresql.ENUM(
        'PJSIP',
        'SIP',
        name='channeldriver',
        create_type=False
    )

    # Add channel_driver column to sip_settings table with default PJSIP
    op.add_column(
        'sip_settings',
        sa.Column('channel_driver', channel_driver_enum, nullable=False, server_default='PJSIP')
    )


def downgrade() -> None:
    # Drop column
    op.drop_column('sip_settings', 'channel_driver')

    # Drop ENUM type
    op.execute('DROP TYPE IF EXISTS channeldriver')
