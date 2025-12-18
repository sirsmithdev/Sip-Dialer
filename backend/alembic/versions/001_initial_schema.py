"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Organizations table
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('max_concurrent_calls', sa.Integer(), default=10),
        sa.Column('timezone', sa.String(50), default='UTC'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100)),
        sa.Column('last_name', sa.String(100)),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_superuser', sa.Boolean(), default=False),
        sa.Column('role', sa.String(20), default='operator'),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Contact lists table
    op.create_table(
        'contact_lists',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('total_contacts', sa.Integer(), default=0),
        sa.Column('valid_contacts', sa.Integer(), default=0),
        sa.Column('invalid_contacts', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('original_filename', sa.String(255)),
        sa.Column('uploaded_by_id', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Contacts table
    op.create_table(
        'contacts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('contact_list_id', sa.String(36), sa.ForeignKey('contact_lists.id'), nullable=False, index=True),
        sa.Column('phone_number', sa.String(20), nullable=False, index=True),
        sa.Column('phone_number_e164', sa.String(20), index=True),
        sa.Column('first_name', sa.String(100)),
        sa.Column('last_name', sa.String(100)),
        sa.Column('email', sa.String(255)),
        sa.Column('custom_fields', postgresql.JSONB(), default={}),
        sa.Column('is_valid', sa.Boolean(), default=True),
        sa.Column('validation_error', sa.String(255)),
        sa.Column('timezone', sa.String(50)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # DNC entries table
    op.create_table(
        'dnc_entries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('phone_number', sa.String(20), nullable=False, unique=True, index=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), index=True),
        sa.Column('source', sa.String(50), default='manual'),
        sa.Column('reason', sa.Text()),
        sa.Column('added_by_id', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Audio files table
    op.create_table(
        'audio_files',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(500)),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('original_format', sa.String(10), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('storage_path', sa.String(500), nullable=False),
        sa.Column('storage_bucket', sa.String(100), default='audio'),
        sa.Column('transcoded_paths', postgresql.JSONB(), default={}),
        sa.Column('duration_seconds', sa.Float()),
        sa.Column('sample_rate', sa.Integer()),
        sa.Column('channels', sa.Integer()),
        sa.Column('status', sa.String(20), default='uploading'),
        sa.Column('error_message', sa.String(500)),
        sa.Column('uploaded_by_id', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # IVR flows table
    op.create_table(
        'ivr_flows',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('status', sa.String(20), default='draft'),
        sa.Column('active_version_id', sa.String(36)),  # FK added later
        sa.Column('created_by_id', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # IVR flow versions table
    op.create_table(
        'ivr_flow_versions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('flow_id', sa.String(36), sa.ForeignKey('ivr_flows.id'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('definition', postgresql.JSONB(), nullable=False, default={}),
        sa.Column('viewport', postgresql.JSONB()),
        sa.Column('notes', sa.Text()),
        sa.Column('created_by_id', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Add FK for active_version_id
    op.create_foreign_key(
        'fk_ivr_flows_active_version',
        'ivr_flows', 'ivr_flow_versions',
        ['active_version_id'], ['id'],
        use_alter=True
    )

    # Campaigns table
    op.create_table(
        'campaigns',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('status', sa.String(20), default='draft'),
        sa.Column('contact_list_id', sa.String(36), sa.ForeignKey('contact_lists.id'), nullable=False),
        sa.Column('ivr_flow_id', sa.String(36), sa.ForeignKey('ivr_flows.id')),
        sa.Column('greeting_audio_id', sa.String(36), sa.ForeignKey('audio_files.id')),
        sa.Column('voicemail_audio_id', sa.String(36), sa.ForeignKey('audio_files.id')),
        sa.Column('dialing_mode', sa.String(20), default='progressive'),
        sa.Column('max_concurrent_calls', sa.Integer(), default=5),
        sa.Column('calls_per_minute', sa.Integer()),
        sa.Column('max_retries', sa.Integer(), default=2),
        sa.Column('retry_delay_minutes', sa.Integer(), default=30),
        sa.Column('retry_on_no_answer', sa.Boolean(), default=True),
        sa.Column('retry_on_busy', sa.Boolean(), default=True),
        sa.Column('retry_on_failed', sa.Boolean(), default=False),
        sa.Column('ring_timeout_seconds', sa.Integer(), default=30),
        sa.Column('amd_enabled', sa.Boolean(), default=True),
        sa.Column('amd_action_human', sa.String(50), default='play_ivr'),
        sa.Column('amd_action_machine', sa.String(50), default='leave_message'),
        sa.Column('scheduled_start', sa.DateTime(timezone=True)),
        sa.Column('scheduled_end', sa.DateTime(timezone=True)),
        sa.Column('calling_hours_start', sa.Time(), default='09:00:00'),
        sa.Column('calling_hours_end', sa.Time(), default='21:00:00'),
        sa.Column('respect_timezone', sa.Boolean(), default=True),
        sa.Column('total_contacts', sa.Integer(), default=0),
        sa.Column('contacts_called', sa.Integer(), default=0),
        sa.Column('contacts_answered', sa.Integer(), default=0),
        sa.Column('contacts_completed', sa.Integer(), default=0),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('created_by_id', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Campaign contacts table
    op.create_table(
        'campaign_contacts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('campaign_id', sa.String(36), sa.ForeignKey('campaigns.id'), nullable=False, index=True),
        sa.Column('contact_id', sa.String(36), sa.ForeignKey('contacts.id'), nullable=False, index=True),
        sa.Column('status', sa.String(20), default='pending', index=True),
        sa.Column('attempts', sa.Integer(), default=0),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True)),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), index=True),
        sa.Column('last_disposition', sa.String(30)),
        sa.Column('priority', sa.Integer(), default=100),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Call logs table
    op.create_table(
        'call_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('campaign_id', sa.String(36), sa.ForeignKey('campaigns.id'), index=True),
        sa.Column('contact_id', sa.String(36), sa.ForeignKey('contacts.id'), index=True),
        sa.Column('channel_id', sa.String(100), index=True),
        sa.Column('unique_id', sa.String(100), unique=True, index=True),
        sa.Column('caller_id', sa.String(20), nullable=False),
        sa.Column('destination', sa.String(20), nullable=False, index=True),
        sa.Column('direction', sa.String(10), default='outbound'),
        sa.Column('initiated_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('answered_at', sa.DateTime(timezone=True)),
        sa.Column('ended_at', sa.DateTime(timezone=True)),
        sa.Column('ring_duration_seconds', sa.Integer()),
        sa.Column('talk_duration_seconds', sa.Integer()),
        sa.Column('total_duration_seconds', sa.Integer()),
        sa.Column('result', sa.String(20), nullable=False),
        sa.Column('hangup_cause', sa.String(50)),
        sa.Column('hangup_cause_code', sa.Integer()),
        sa.Column('amd_result', sa.String(20), default='not_used'),
        sa.Column('amd_confidence', sa.Float()),
        sa.Column('ivr_flow_id', sa.String(36), sa.ForeignKey('ivr_flows.id')),
        sa.Column('ivr_completed', sa.Boolean(), default=False),
        sa.Column('dtmf_inputs', postgresql.JSONB(), default=[]),
        sa.Column('recording_path', sa.String(500)),
        sa.Column('recording_duration_seconds', sa.Integer()),
        sa.Column('metadata', postgresql.JSONB(), default={}),
        sa.Column('error_message', sa.Text()),
        sa.Column('asterisk_channel', sa.String(100)),
        sa.Column('asterisk_linked_id', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Survey responses table
    op.create_table(
        'survey_responses',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('call_log_id', sa.String(36), sa.ForeignKey('call_logs.id'), nullable=False, index=True),
        sa.Column('campaign_id', sa.String(36), sa.ForeignKey('campaigns.id'), nullable=False, index=True),
        sa.Column('contact_id', sa.String(36), sa.ForeignKey('contacts.id'), index=True),
        sa.Column('ivr_flow_id', sa.String(36), sa.ForeignKey('ivr_flows.id'), nullable=False),
        sa.Column('ivr_flow_version', sa.Integer(), nullable=False),
        sa.Column('phone_number', sa.String(20), nullable=False, index=True),
        sa.Column('responses', postgresql.JSONB(), nullable=False, default={}),
        sa.Column('is_complete', sa.Boolean(), default=False),
        sa.Column('questions_answered', sa.Integer(), default=0),
        sa.Column('total_questions', sa.Integer(), default=0),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('duration_seconds', sa.Integer()),
        sa.Column('notes', sa.Text()),
        sa.Column('metadata', postgresql.JSONB(), default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # SIP settings table
    op.create_table(
        'sip_settings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False, unique=True),
        sa.Column('sip_server', sa.String(255), nullable=False),
        sa.Column('sip_port', sa.Integer(), default=5060),
        sa.Column('sip_username', sa.String(100), nullable=False),
        sa.Column('sip_password_encrypted', sa.String(255), nullable=False),
        sa.Column('sip_transport', sa.String(10), default='UDP'),
        sa.Column('registration_required', sa.Boolean(), default=True),
        sa.Column('register_expires', sa.Integer(), default=3600),
        sa.Column('keepalive_enabled', sa.Boolean(), default=True),
        sa.Column('keepalive_interval', sa.Integer(), default=30),
        sa.Column('rtp_port_start', sa.Integer(), default=10000),
        sa.Column('rtp_port_end', sa.Integer(), default=20000),
        sa.Column('codecs', postgresql.JSONB(), default=['ulaw', 'alaw', 'g722']),
        sa.Column('ami_host', sa.String(255)),
        sa.Column('ami_port', sa.Integer(), default=5038),
        sa.Column('ami_username', sa.String(100)),
        sa.Column('ami_password_encrypted', sa.String(255)),
        sa.Column('default_caller_id', sa.String(50)),
        sa.Column('caller_id_name', sa.String(100)),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('connection_status', sa.String(20), default='disconnected'),
        sa.Column('last_connected_at', sa.DateTime(timezone=True)),
        sa.Column('last_error', sa.String(500)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('sip_settings')
    op.drop_table('survey_responses')
    op.drop_table('call_logs')
    op.drop_table('campaign_contacts')
    op.drop_table('campaigns')
    op.drop_constraint('fk_ivr_flows_active_version', 'ivr_flows', type_='foreignkey')
    op.drop_table('ivr_flow_versions')
    op.drop_table('ivr_flows')
    op.drop_table('audio_files')
    op.drop_table('dnc_entries')
    op.drop_table('contacts')
    op.drop_table('contact_lists')
    op.drop_table('users')
    op.drop_table('organizations')
