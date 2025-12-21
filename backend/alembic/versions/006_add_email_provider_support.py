"""add_email_provider_support

Add email provider selection (Resend/SMTP) and Resend API key field to email_settings.

Revision ID: 006
Revises: 005
Create Date: 2025-12-21 10:00:00.000000

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
    # Create email_provider ENUM type
    email_provider_enum = postgresql.ENUM(
        'smtp',
        'resend',
        name='email_provider',
        create_type=True
    )
    email_provider_enum.create(op.get_bind(), checkfirst=True)

    # Add provider column with default 'resend'
    op.add_column(
        'email_settings',
        sa.Column(
            'provider',
            email_provider_enum,
            nullable=False,
            server_default='resend'
        )
    )

    # Add resend_api_key_encrypted column
    op.add_column(
        'email_settings',
        sa.Column(
            'resend_api_key_encrypted',
            sa.String(500),
            nullable=True
        )
    )

    # Make SMTP fields nullable (they're only required for SMTP provider)
    op.alter_column(
        'email_settings',
        'smtp_host',
        existing_type=sa.String(255),
        nullable=True
    )
    op.alter_column(
        'email_settings',
        'smtp_username',
        existing_type=sa.String(255),
        nullable=True
    )
    op.alter_column(
        'email_settings',
        'smtp_password_encrypted',
        existing_type=sa.String(500),
        nullable=True
    )


def downgrade() -> None:
    # Make SMTP fields required again
    op.alter_column(
        'email_settings',
        'smtp_password_encrypted',
        existing_type=sa.String(500),
        nullable=False
    )
    op.alter_column(
        'email_settings',
        'smtp_username',
        existing_type=sa.String(255),
        nullable=False
    )
    op.alter_column(
        'email_settings',
        'smtp_host',
        existing_type=sa.String(255),
        nullable=False
    )

    # Drop resend_api_key_encrypted column
    op.drop_column('email_settings', 'resend_api_key_encrypted')

    # Drop provider column
    op.drop_column('email_settings', 'provider')

    # Drop email_provider ENUM type
    op.execute('DROP TYPE IF EXISTS email_provider')
