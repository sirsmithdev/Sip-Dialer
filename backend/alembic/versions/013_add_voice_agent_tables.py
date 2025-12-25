"""Add voice agent tables

Revision ID: 013
Revises: 012
Create Date: 2024-12-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '013'
down_revision: Union[str, None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Voice Agent Configs table
    op.create_table(
        'voice_agent_configs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('status', sa.String(20), default='draft'),

        # OpenAI settings
        sa.Column('openai_api_key_encrypted', sa.Text(), nullable=True),
        sa.Column('llm_model', sa.String(50), default='gpt-4o-mini'),
        sa.Column('tts_voice', sa.String(50), default='nova'),
        sa.Column('tts_model', sa.String(50), default='tts-1'),
        sa.Column('whisper_model', sa.String(50), default='whisper-1'),

        # System prompt and messages
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('greeting_message', sa.Text(), default='Hello, thank you for calling. How can I help you today?'),
        sa.Column('fallback_message', sa.Text(), default='I\'m sorry, I didn\'t understand that. Could you please repeat?'),
        sa.Column('goodbye_message', sa.Text(), default='Thank you for calling. Goodbye!'),

        # Conversation settings
        sa.Column('max_turns', sa.Integer(), default=20),
        sa.Column('silence_timeout_seconds', sa.Float(), default=5.0),
        sa.Column('max_call_duration_seconds', sa.Integer(), default=600),

        # VAD settings
        sa.Column('vad_energy_threshold', sa.Float(), default=0.02),
        sa.Column('vad_silence_duration', sa.Float(), default=0.8),
        sa.Column('vad_min_speech_duration', sa.Float(), default=0.3),

        # LLM settings
        sa.Column('llm_temperature', sa.Float(), default=0.7),
        sa.Column('llm_max_tokens', sa.Integer(), default=150),

        # Plugin configuration
        sa.Column('plugins_config', postgresql.JSONB(), default=[]),

        # Transfer settings
        sa.Column('default_transfer_extension', sa.String(50), nullable=True),
        sa.Column('transfer_message', sa.Text(), default='Please hold while I transfer you to an agent.'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create index on organization_id
    op.create_index('ix_voice_agent_configs_organization_id', 'voice_agent_configs', ['organization_id'])

    # Inbound Routes table
    op.create_table(
        'inbound_routes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('did_pattern', sa.String(50), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('agent_config_id', sa.String(36), sa.ForeignKey('voice_agent_configs.id'), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('priority', sa.Integer(), default=100),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes
    op.create_index('ix_inbound_routes_organization_id', 'inbound_routes', ['organization_id'])
    op.create_index('ix_inbound_routes_agent_config_id', 'inbound_routes', ['agent_config_id'])

    # Voice Agent Conversations table
    op.create_table(
        'voice_agent_conversations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('call_log_id', sa.String(36), sa.ForeignKey('call_logs.id'), nullable=True),
        sa.Column('agent_config_id', sa.String(36), sa.ForeignKey('voice_agent_configs.id'), nullable=False),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id'), nullable=False),

        # Call metadata
        sa.Column('caller_number', sa.String(50), nullable=False),
        sa.Column('called_number', sa.String(50), nullable=True),
        sa.Column('call_duration_seconds', sa.Integer(), default=0),

        # Conversation timing
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),

        # Conversation data
        sa.Column('transcript', postgresql.JSONB(), default=[]),
        sa.Column('turn_count', sa.Integer(), default=0),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('sentiment', sa.String(50), nullable=True),
        sa.Column('detected_intent', sa.String(255), nullable=True),

        # Outcome
        sa.Column('resolution_status', sa.String(50), default='resolved'),
        sa.Column('transfer_destination', sa.String(50), nullable=True),
        sa.Column('transfer_reason', sa.Text(), nullable=True),

        # Plugin data
        sa.Column('plugin_data', postgresql.JSONB(), default={}),

        # Error information
        sa.Column('error_message', sa.Text(), nullable=True),

        # Cost tracking
        sa.Column('whisper_seconds', sa.Float(), default=0.0),
        sa.Column('llm_input_tokens', sa.Integer(), default=0),
        sa.Column('llm_output_tokens', sa.Integer(), default=0),
        sa.Column('tts_characters', sa.Integer(), default=0),
        sa.Column('estimated_cost_usd', sa.Float(), default=0.0),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes
    op.create_index('ix_voice_agent_conversations_organization_id', 'voice_agent_conversations', ['organization_id'])
    op.create_index('ix_voice_agent_conversations_agent_config_id', 'voice_agent_conversations', ['agent_config_id'])
    op.create_index('ix_voice_agent_conversations_caller_number', 'voice_agent_conversations', ['caller_number'])
    op.create_index('ix_voice_agent_conversations_started_at', 'voice_agent_conversations', ['started_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('voice_agent_conversations')
    op.drop_table('inbound_routes')
    op.drop_table('voice_agent_configs')
