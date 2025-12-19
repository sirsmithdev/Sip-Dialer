"""remove_ami_fields

Remove AMI fields and channel_driver from sip_settings table.
The application now connects directly as a PJSIP extension.

Revision ID: 004
Revises: 003
Create Date: 2025-12-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop AMI columns from sip_settings table
    op.drop_column('sip_settings', 'ami_host')
    op.drop_column('sip_settings', 'ami_port')
    op.drop_column('sip_settings', 'ami_username')
    op.drop_column('sip_settings', 'ami_password_encrypted')

    # Drop channel_driver column (always PJSIP now)
    op.drop_column('sip_settings', 'channel_driver')

    # Drop the channeldriver ENUM type
    op.execute('DROP TYPE IF EXISTS channeldriver')


def downgrade() -> None:
    # Recreate ChannelDriver ENUM type
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'channeldriver') THEN
                CREATE TYPE channeldriver AS ENUM ('PJSIP', 'SIP');
            END IF;
        END$$;
    """)

    channel_driver_enum = postgresql.ENUM(
        'PJSIP',
        'SIP',
        name='channeldriver',
        create_type=False
    )

    # Re-add channel_driver column
    op.add_column(
        'sip_settings',
        sa.Column('channel_driver', channel_driver_enum, nullable=False, server_default='PJSIP')
    )

    # Re-add AMI columns
    op.add_column(
        'sip_settings',
        sa.Column('ami_host', sa.String(255), nullable=True)
    )
    op.add_column(
        'sip_settings',
        sa.Column('ami_port', sa.Integer(), nullable=True, server_default='5038')
    )
    op.add_column(
        'sip_settings',
        sa.Column('ami_username', sa.String(100), nullable=True)
    )
    op.add_column(
        'sip_settings',
        sa.Column('ami_password_encrypted', sa.String(255), nullable=True)
    )
