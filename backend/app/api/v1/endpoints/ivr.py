"""
IVR Flow API endpoints.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.ivr import IVRFlow, IVRFlowVersion, IVRFlowStatus
from app.schemas.ivr import (
    IVRFlowCreate,
    IVRFlowUpdate,
    IVRFlowResponse,
    IVRFlowDetailResponse,
    IVRFlowListResponse,
    IVRFlowVersionCreate,
    IVRFlowVersionResponse,
    IVRFlowPublishRequest,
    IVRFlowPublishResponse,
    IVRFlowDuplicateRequest,
    IVRFlowValidationResult,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================

async def get_flow_or_404(
    db: AsyncSession,
    flow_id: str,
    organization_id: str
) -> IVRFlow:
    """Get an IVR flow by ID or raise 404."""
    result = await db.execute(
        select(IVRFlow)
        .options(selectinload(IVRFlow.versions))
        .where(
            IVRFlow.id == flow_id,
            IVRFlow.organization_id == organization_id
        )
    )
    flow = result.scalar_one_or_none()
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IVR flow not found"
        )
    return flow


def validate_flow_definition(definition: dict) -> IVRFlowValidationResult:
    """Validate an IVR flow definition."""
    errors = []
    warnings = []

    nodes = definition.get("nodes", [])
    edges = definition.get("edges", [])
    start_node = definition.get("start_node")

    # Check for nodes
    if not nodes:
        errors.append("Flow must have at least one node")
        return IVRFlowValidationResult(is_valid=False, errors=errors, warnings=warnings)

    node_ids = {node.get("id") for node in nodes}

    # Check for start node
    if not start_node:
        # Try to find a START node
        start_nodes = [n for n in nodes if n.get("type") == "start"]
        if start_nodes:
            warnings.append("start_node not specified, using first START node")
        else:
            errors.append("No start_node specified and no START node found")

    elif start_node not in node_ids:
        errors.append(f"start_node '{start_node}' not found in nodes")

    # Validate edges reference valid nodes
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source not in node_ids:
            errors.append(f"Edge source '{source}' not found in nodes")
        if target not in node_ids:
            errors.append(f"Edge target '{target}' not found in nodes")

    # Check for orphan nodes (no incoming or outgoing edges)
    sources = {edge.get("source") for edge in edges}
    targets = {edge.get("target") for edge in edges}
    connected = sources | targets
    orphans = node_ids - connected - {start_node}
    if orphans:
        warnings.append(f"Orphan nodes detected: {orphans}")

    # Check for required audio files in audio nodes
    for node in nodes:
        node_type = node.get("type")
        data = node.get("data", {})
        if node_type == "play_audio" and not data.get("audio_file_id"):
            warnings.append(f"Node '{node.get('id')}' (play_audio) missing audio_file_id")
        if node_type == "menu" and not data.get("prompt_audio_id"):
            warnings.append(f"Node '{node.get('id')}' (menu) missing prompt_audio_id")
        if node_type == "survey_question":
            if not data.get("prompt_audio_id"):
                warnings.append(f"Node '{node.get('id')}' (survey_question) missing prompt_audio_id")
            if not data.get("question_id"):
                warnings.append(f"Node '{node.get('id')}' (survey_question) missing question_id")

    return IVRFlowValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


# =============================================================================
# Flow Endpoints
# =============================================================================

@router.get("", response_model=IVRFlowListResponse)
async def list_ivr_flows(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[IVRFlowStatus] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List IVR flows for the current organization."""
    query = select(IVRFlow).where(
        IVRFlow.organization_id == current_user.organization_id
    )

    if status_filter:
        query = query.where(IVRFlow.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    query = query.order_by(IVRFlow.updated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    flows = result.scalars().all()

    # Get version counts
    items = []
    for flow in flows:
        version_count_result = await db.execute(
            select(func.count()).where(IVRFlowVersion.flow_id == flow.id)
        )
        version_count = version_count_result.scalar() or 0

        flow_dict = IVRFlowResponse.model_validate(flow).model_dump()
        flow_dict["version_count"] = version_count
        items.append(IVRFlowResponse(**flow_dict))

    return IVRFlowListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=IVRFlowDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_ivr_flow(
    flow_data: IVRFlowCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new IVR flow."""
    # Create the flow
    flow = IVRFlow(
        name=flow_data.name,
        description=flow_data.description,
        organization_id=current_user.organization_id,
        status=IVRFlowStatus.DRAFT,
        created_by_id=current_user.id,
    )
    db.add(flow)
    await db.flush()

    # Create initial version if definition provided
    version = None
    if flow_data.definition:
        definition_dict = flow_data.definition.model_dump()
        version = IVRFlowVersion(
            flow_id=flow.id,
            version=1,
            definition=definition_dict,
            created_by_id=current_user.id,
        )
        db.add(version)
        await db.flush()

        # Set as active version
        flow.active_version_id = version.id

    await db.commit()
    await db.refresh(flow)

    logger.info(f"Created IVR flow {flow.id}: {flow.name}")

    response = IVRFlowDetailResponse.model_validate(flow)
    if version:
        response.active_version = IVRFlowVersionResponse.model_validate(version)
    response.version_count = 1 if version else 0

    return response


@router.get("/{flow_id}", response_model=IVRFlowDetailResponse)
async def get_ivr_flow(
    flow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get an IVR flow by ID with its active version."""
    flow = await get_flow_or_404(db, flow_id, current_user.organization_id)

    response = IVRFlowDetailResponse.model_validate(flow)
    response.version_count = len(flow.versions)

    # Get active version
    if flow.active_version_id:
        version_result = await db.execute(
            select(IVRFlowVersion).where(IVRFlowVersion.id == flow.active_version_id)
        )
        active_version = version_result.scalar_one_or_none()
        if active_version:
            response.active_version = IVRFlowVersionResponse.model_validate(active_version)

    return response


@router.patch("/{flow_id}", response_model=IVRFlowResponse)
async def update_ivr_flow(
    flow_id: str,
    update_data: IVRFlowUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update IVR flow metadata."""
    flow = await get_flow_or_404(db, flow_id, current_user.organization_id)

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(flow, field, value)

    await db.commit()
    await db.refresh(flow)

    logger.info(f"Updated IVR flow {flow.id}")
    return IVRFlowResponse.model_validate(flow)


@router.delete("/{flow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ivr_flow(
    flow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an IVR flow and all its versions."""
    flow = await get_flow_or_404(db, flow_id, current_user.organization_id)

    # Check if flow is used by any campaigns
    from app.models.campaign import Campaign
    campaign_result = await db.execute(
        select(Campaign.id).where(Campaign.ivr_flow_id == flow_id).limit(1)
    )
    if campaign_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete IVR flow that is used by campaigns"
        )

    await db.delete(flow)
    await db.commit()

    logger.info(f"Deleted IVR flow {flow_id}")


# =============================================================================
# Version Endpoints
# =============================================================================

@router.get("/{flow_id}/versions", response_model=list[IVRFlowVersionResponse])
async def list_flow_versions(
    flow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all versions of an IVR flow."""
    flow = await get_flow_or_404(db, flow_id, current_user.organization_id)

    result = await db.execute(
        select(IVRFlowVersion)
        .where(IVRFlowVersion.flow_id == flow_id)
        .order_by(IVRFlowVersion.version.desc())
    )
    versions = result.scalars().all()

    return [IVRFlowVersionResponse.model_validate(v) for v in versions]


@router.post("/{flow_id}/versions", response_model=IVRFlowVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_flow_version(
    flow_id: str,
    version_data: IVRFlowVersionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new version of an IVR flow."""
    flow = await get_flow_or_404(db, flow_id, current_user.organization_id)

    # Get the next version number
    max_version_result = await db.execute(
        select(func.max(IVRFlowVersion.version)).where(IVRFlowVersion.flow_id == flow_id)
    )
    max_version = max_version_result.scalar() or 0

    # Create new version
    definition_dict = version_data.definition.model_dump()
    viewport_dict = version_data.viewport.model_dump() if version_data.viewport else None

    version = IVRFlowVersion(
        flow_id=flow_id,
        version=max_version + 1,
        definition=definition_dict,
        viewport=viewport_dict,
        notes=version_data.notes,
        created_by_id=current_user.id,
    )
    db.add(version)

    # Set as active version and update flow to draft if it was published
    flow.active_version_id = version.id
    if flow.status == IVRFlowStatus.PUBLISHED:
        flow.status = IVRFlowStatus.DRAFT

    await db.commit()
    await db.refresh(version)

    logger.info(f"Created IVR flow version {version.id} (v{version.version})")
    return IVRFlowVersionResponse.model_validate(version)


@router.get("/{flow_id}/versions/{version_id}", response_model=IVRFlowVersionResponse)
async def get_flow_version(
    flow_id: str,
    version_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific version of an IVR flow."""
    # Verify flow ownership
    await get_flow_or_404(db, flow_id, current_user.organization_id)

    result = await db.execute(
        select(IVRFlowVersion).where(
            IVRFlowVersion.id == version_id,
            IVRFlowVersion.flow_id == flow_id
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    return IVRFlowVersionResponse.model_validate(version)


# =============================================================================
# Action Endpoints
# =============================================================================

@router.post("/{flow_id}/publish", response_model=IVRFlowPublishResponse)
async def publish_ivr_flow(
    flow_id: str,
    publish_data: IVRFlowPublishRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Publish an IVR flow, making it available for use in campaigns."""
    flow = await get_flow_or_404(db, flow_id, current_user.organization_id)

    # Determine which version to publish
    if publish_data and publish_data.version_id:
        version_id = publish_data.version_id
        # Verify version exists
        result = await db.execute(
            select(IVRFlowVersion).where(
                IVRFlowVersion.id == version_id,
                IVRFlowVersion.flow_id == flow_id
            )
        )
        version = result.scalar_one_or_none()
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Version not found"
            )
    else:
        # Use active version or latest version
        if flow.active_version_id:
            version_id = flow.active_version_id
        else:
            # Get latest version
            result = await db.execute(
                select(IVRFlowVersion)
                .where(IVRFlowVersion.flow_id == flow_id)
                .order_by(IVRFlowVersion.version.desc())
                .limit(1)
            )
            version = result.scalar_one_or_none()
            if not version:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No versions exist for this flow"
                )
            version_id = version.id

    # Validate the flow definition
    version_result = await db.execute(
        select(IVRFlowVersion).where(IVRFlowVersion.id == version_id)
    )
    version = version_result.scalar_one()
    validation = validate_flow_definition(version.definition)

    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Flow validation failed: {', '.join(validation.errors)}"
        )

    # Update flow status
    flow.status = IVRFlowStatus.PUBLISHED
    flow.active_version_id = version_id

    await db.commit()

    logger.info(f"Published IVR flow {flow.id} with version {version_id}")

    return IVRFlowPublishResponse(
        id=flow.id,
        status=flow.status,
        active_version_id=version_id,
        message=f"Flow published successfully (v{version.version})"
    )


@router.post("/{flow_id}/duplicate", response_model=IVRFlowDetailResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_ivr_flow(
    flow_id: str,
    duplicate_data: IVRFlowDuplicateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Duplicate an IVR flow with all its versions."""
    flow = await get_flow_or_404(db, flow_id, current_user.organization_id)

    # Create new flow
    new_flow = IVRFlow(
        name=duplicate_data.name,
        description=duplicate_data.description or flow.description,
        organization_id=current_user.organization_id,
        status=IVRFlowStatus.DRAFT,
        created_by_id=current_user.id,
    )
    db.add(new_flow)
    await db.flush()

    # Copy active version
    if flow.active_version_id:
        version_result = await db.execute(
            select(IVRFlowVersion).where(IVRFlowVersion.id == flow.active_version_id)
        )
        original_version = version_result.scalar_one()

        new_version = IVRFlowVersion(
            flow_id=new_flow.id,
            version=1,
            definition=original_version.definition,
            viewport=original_version.viewport,
            notes="Duplicated from original flow",
            created_by_id=current_user.id,
        )
        db.add(new_version)
        await db.flush()

        new_flow.active_version_id = new_version.id

    await db.commit()
    await db.refresh(new_flow)

    logger.info(f"Duplicated IVR flow {flow_id} to {new_flow.id}")

    response = IVRFlowDetailResponse.model_validate(new_flow)
    response.version_count = 1 if new_flow.active_version_id else 0

    return response


@router.post("/{flow_id}/validate", response_model=IVRFlowValidationResult)
async def validate_ivr_flow(
    flow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate the current IVR flow definition."""
    flow = await get_flow_or_404(db, flow_id, current_user.organization_id)

    if not flow.active_version_id:
        return IVRFlowValidationResult(
            is_valid=False,
            errors=["No active version to validate"],
            warnings=[]
        )

    version_result = await db.execute(
        select(IVRFlowVersion).where(IVRFlowVersion.id == flow.active_version_id)
    )
    version = version_result.scalar_one()

    return validate_flow_definition(version.definition)


@router.post("/{flow_id}/archive", response_model=IVRFlowResponse)
async def archive_ivr_flow(
    flow_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Archive an IVR flow."""
    flow = await get_flow_or_404(db, flow_id, current_user.organization_id)

    flow.status = IVRFlowStatus.ARCHIVED
    await db.commit()
    await db.refresh(flow)

    logger.info(f"Archived IVR flow {flow.id}")
    return IVRFlowResponse.model_validate(flow)
