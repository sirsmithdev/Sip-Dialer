"""
Voice Agent REST API endpoints.
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.voice_agent import (
    VoiceAgentConfig,
    VoiceAgentStatus,
    InboundRoute,
    VoiceAgentConversation,
    ResolutionStatus
)
from app.schemas.voice_agent import (
    VoiceAgentConfigCreate,
    VoiceAgentConfigUpdate,
    VoiceAgentConfigResponse,
    InboundRouteCreate,
    InboundRouteUpdate,
    InboundRouteResponse,
    VoiceAgentConversationResponse,
    ConversationListResponse,
    VoiceAgentStats
)
from app.core.security import encrypt_value

router = APIRouter(prefix="/voice-agents", tags=["Voice Agent"])


# ============ Voice Agent Config Endpoints ============

@router.get("", response_model=List[VoiceAgentConfigResponse])
async def list_voice_agents(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all voice agent configurations for the organization."""
    query = select(VoiceAgentConfig).where(
        VoiceAgentConfig.organization_id == current_user.organization_id
    )

    if status:
        query = query.where(VoiceAgentConfig.status == status)

    query = query.order_by(VoiceAgentConfig.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=VoiceAgentConfigResponse)
async def create_voice_agent(
    data: VoiceAgentConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new voice agent configuration."""
    # Encrypt API key if provided
    encrypted_key = None
    if data.openai_api_key:
        encrypted_key = encrypt_value(data.openai_api_key)

    agent = VoiceAgentConfig(
        organization_id=current_user.organization_id,
        name=data.name,
        description=data.description,
        system_prompt=data.system_prompt,
        greeting_message=data.greeting_message,
        fallback_message=data.fallback_message,
        goodbye_message=data.goodbye_message,
        transfer_message=data.transfer_message,
        openai_api_key_encrypted=encrypted_key,
        llm_model=data.llm_model,
        tts_voice=data.tts_voice,
        tts_model=data.tts_model,
        whisper_model=data.whisper_model,
        max_turns=data.max_turns,
        silence_timeout_seconds=data.silence_timeout_seconds,
        max_call_duration_seconds=data.max_call_duration_seconds,
        vad_energy_threshold=data.vad_energy_threshold,
        vad_silence_duration=data.vad_silence_duration,
        vad_min_speech_duration=data.vad_min_speech_duration,
        llm_temperature=data.llm_temperature,
        llm_max_tokens=data.llm_max_tokens,
        plugins_config=data.plugins_config,
        default_transfer_extension=data.default_transfer_extension,
        status=VoiceAgentStatus.DRAFT
    )

    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/{agent_id}", response_model=VoiceAgentConfigResponse)
async def get_voice_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a voice agent configuration by ID."""
    result = await db.execute(
        select(VoiceAgentConfig).where(
            and_(
                VoiceAgentConfig.id == agent_id,
                VoiceAgentConfig.organization_id == current_user.organization_id
            )
        )
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Voice agent not found")

    return agent


@router.put("/{agent_id}", response_model=VoiceAgentConfigResponse)
async def update_voice_agent(
    agent_id: str,
    data: VoiceAgentConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a voice agent configuration."""
    result = await db.execute(
        select(VoiceAgentConfig).where(
            and_(
                VoiceAgentConfig.id == agent_id,
                VoiceAgentConfig.organization_id == current_user.organization_id
            )
        )
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Voice agent not found")

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            value = VoiceAgentStatus(value)
        setattr(agent, field, value)

    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/{agent_id}")
async def delete_voice_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a voice agent configuration."""
    result = await db.execute(
        select(VoiceAgentConfig).where(
            and_(
                VoiceAgentConfig.id == agent_id,
                VoiceAgentConfig.organization_id == current_user.organization_id
            )
        )
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Voice agent not found")

    await db.delete(agent)
    await db.commit()
    return {"message": "Voice agent deleted"}


@router.post("/{agent_id}/activate", response_model=VoiceAgentConfigResponse)
async def activate_voice_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Activate a voice agent (set status to active)."""
    result = await db.execute(
        select(VoiceAgentConfig).where(
            and_(
                VoiceAgentConfig.id == agent_id,
                VoiceAgentConfig.organization_id == current_user.organization_id
            )
        )
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Voice agent not found")

    agent.status = VoiceAgentStatus.ACTIVE
    await db.commit()
    await db.refresh(agent)
    return agent


@router.post("/{agent_id}/deactivate", response_model=VoiceAgentConfigResponse)
async def deactivate_voice_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deactivate a voice agent."""
    result = await db.execute(
        select(VoiceAgentConfig).where(
            and_(
                VoiceAgentConfig.id == agent_id,
                VoiceAgentConfig.organization_id == current_user.organization_id
            )
        )
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Voice agent not found")

    agent.status = VoiceAgentStatus.INACTIVE
    await db.commit()
    await db.refresh(agent)
    return agent


# ============ Inbound Route Endpoints ============

@router.get("/routes", response_model=List[InboundRouteResponse])
async def list_inbound_routes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all inbound routes for the organization."""
    result = await db.execute(
        select(InboundRoute)
        .where(InboundRoute.organization_id == current_user.organization_id)
        .order_by(InboundRoute.priority, InboundRoute.created_at.desc())
    )
    return result.scalars().all()


@router.post("/routes", response_model=InboundRouteResponse)
async def create_inbound_route(
    data: InboundRouteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new inbound route."""
    # Verify agent exists
    result = await db.execute(
        select(VoiceAgentConfig).where(
            and_(
                VoiceAgentConfig.id == data.agent_config_id,
                VoiceAgentConfig.organization_id == current_user.organization_id
            )
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Voice agent not found")

    route = InboundRoute(
        organization_id=current_user.organization_id,
        did_pattern=data.did_pattern,
        description=data.description,
        agent_config_id=data.agent_config_id,
        is_active=data.is_active,
        priority=data.priority
    )

    db.add(route)
    await db.commit()
    await db.refresh(route)
    return route


@router.put("/routes/{route_id}", response_model=InboundRouteResponse)
async def update_inbound_route(
    route_id: str,
    data: InboundRouteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an inbound route."""
    result = await db.execute(
        select(InboundRoute).where(
            and_(
                InboundRoute.id == route_id,
                InboundRoute.organization_id == current_user.organization_id
            )
        )
    )
    route = result.scalar_one_or_none()

    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(route, field, value)

    await db.commit()
    await db.refresh(route)
    return route


@router.delete("/routes/{route_id}")
async def delete_inbound_route(
    route_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an inbound route."""
    result = await db.execute(
        select(InboundRoute).where(
            and_(
                InboundRoute.id == route_id,
                InboundRoute.organization_id == current_user.organization_id
            )
        )
    )
    route = result.scalar_one_or_none()

    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    await db.delete(route)
    await db.commit()
    return {"message": "Route deleted"}


# ============ Conversation Endpoints ============

@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    agent_id: Optional[str] = None,
    resolution_status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List voice agent conversations with pagination and filters."""
    query = select(VoiceAgentConversation).where(
        VoiceAgentConversation.organization_id == current_user.organization_id
    )

    if agent_id:
        query = query.where(VoiceAgentConversation.agent_config_id == agent_id)
    if resolution_status:
        query = query.where(VoiceAgentConversation.resolution_status == resolution_status)
    if start_date:
        query = query.where(VoiceAgentConversation.started_at >= start_date)
    if end_date:
        query = query.where(VoiceAgentConversation.started_at <= end_date)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    query = query.order_by(VoiceAgentConversation.started_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = result.scalars().all()

    return ConversationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/conversations/{conversation_id}", response_model=VoiceAgentConversationResponse)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a conversation by ID."""
    result = await db.execute(
        select(VoiceAgentConversation).where(
            and_(
                VoiceAgentConversation.id == conversation_id,
                VoiceAgentConversation.organization_id == current_user.organization_id
            )
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


# ============ Stats Endpoints ============

@router.get("/stats", response_model=VoiceAgentStats)
async def get_voice_agent_stats(
    days: int = Query(7, ge=1, le=90),
    agent_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get voice agent usage statistics."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    query = select(VoiceAgentConversation).where(
        and_(
            VoiceAgentConversation.organization_id == current_user.organization_id,
            VoiceAgentConversation.started_at >= start_date,
            VoiceAgentConversation.started_at <= end_date
        )
    )

    if agent_id:
        query = query.where(VoiceAgentConversation.agent_config_id == agent_id)

    result = await db.execute(query)
    conversations = result.scalars().all()

    # Calculate stats
    total_conversations = len(conversations)
    total_duration = sum(c.call_duration_seconds for c in conversations)
    total_turns = sum(c.turn_count for c in conversations)
    total_cost = sum(c.estimated_cost_usd for c in conversations)

    resolution_breakdown = {}
    sentiment_breakdown = {}

    for conv in conversations:
        # Resolution
        status = conv.resolution_status.value if hasattr(conv.resolution_status, 'value') else str(conv.resolution_status)
        resolution_breakdown[status] = resolution_breakdown.get(status, 0) + 1

        # Sentiment
        if conv.sentiment:
            sentiment_breakdown[conv.sentiment] = sentiment_breakdown.get(conv.sentiment, 0) + 1

    return VoiceAgentStats(
        total_conversations=total_conversations,
        total_duration_seconds=total_duration,
        avg_duration_seconds=total_duration / total_conversations if total_conversations else 0,
        total_turns=total_turns,
        avg_turns=total_turns / total_conversations if total_conversations else 0,
        resolution_breakdown=resolution_breakdown,
        sentiment_breakdown=sentiment_breakdown,
        total_cost_usd=total_cost,
        period_start=start_date,
        period_end=end_date
    )
