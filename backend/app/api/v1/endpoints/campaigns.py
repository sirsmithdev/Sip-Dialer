"""
Campaign API endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_roles
from app.models.user import User, UserRole
from app.models.campaign import CampaignStatus, ContactStatus
from app.schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignListResponse,
    CampaignListItem,
    CampaignContactResponse,
    CampaignContactsResponse,
    CampaignStatsResponse,
    CampaignScheduleRequest,
)
from app.schemas.email_settings import SendReportRequest, SendReportResponse
from app.services.campaign_service import campaign_service
from workers.tasks.email_tasks import send_campaign_report_task

router = APIRouter()


# ============================================================================
# Campaign Endpoints
# ============================================================================

@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[CampaignStatus] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """List campaigns for the current organization."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    campaigns, total = await campaign_service.list_campaigns(
        db=db,
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        status=status,
        search=search,
    )

    return CampaignListResponse(
        items=[CampaignListItem.model_validate(c) for c in campaigns],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    data: CampaignCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """Create a new campaign."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    try:
        campaign = await campaign_service.create_campaign(
            db=db,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
            data=data,
        )
        return CampaignResponse.model_validate(campaign)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """Get a campaign by ID."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    campaign = await campaign_service.get_campaign(
        db=db,
        campaign_id=campaign_id,
        organization_id=current_user.organization_id,
    )

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    return CampaignResponse.model_validate(campaign)


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    data: CampaignUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """Update a campaign."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    campaign = await campaign_service.get_campaign(
        db=db,
        campaign_id=campaign_id,
        organization_id=current_user.organization_id,
    )

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    try:
        campaign = await campaign_service.update_campaign(
            db=db,
            campaign=campaign,
            data=data,
        )
        return CampaignResponse.model_validate(campaign)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: str,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """Delete a campaign."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    campaign = await campaign_service.get_campaign(
        db=db,
        campaign_id=campaign_id,
        organization_id=current_user.organization_id,
    )

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    try:
        await campaign_service.delete_campaign(db=db, campaign=campaign)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============================================================================
# Campaign Status Control Endpoints
# ============================================================================

@router.post("/{campaign_id}/start", response_model=CampaignResponse)
async def start_campaign(
    campaign_id: str,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """Start a campaign."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    campaign = await campaign_service.get_campaign(
        db=db,
        campaign_id=campaign_id,
        organization_id=current_user.organization_id,
    )

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    try:
        campaign = await campaign_service.update_status(
            db=db,
            campaign=campaign,
            new_status=CampaignStatus.RUNNING,
        )
        return CampaignResponse.model_validate(campaign)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(
    campaign_id: str,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """Pause a running campaign."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    campaign = await campaign_service.get_campaign(
        db=db,
        campaign_id=campaign_id,
        organization_id=current_user.organization_id,
    )

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    try:
        campaign = await campaign_service.update_status(
            db=db,
            campaign=campaign,
            new_status=CampaignStatus.PAUSED,
        )
        return CampaignResponse.model_validate(campaign)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{campaign_id}/resume", response_model=CampaignResponse)
async def resume_campaign(
    campaign_id: str,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused campaign."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    campaign = await campaign_service.get_campaign(
        db=db,
        campaign_id=campaign_id,
        organization_id=current_user.organization_id,
    )

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    try:
        campaign = await campaign_service.update_status(
            db=db,
            campaign=campaign,
            new_status=CampaignStatus.RUNNING,
        )
        return CampaignResponse.model_validate(campaign)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{campaign_id}/cancel", response_model=CampaignResponse)
async def cancel_campaign(
    campaign_id: str,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a campaign."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    campaign = await campaign_service.get_campaign(
        db=db,
        campaign_id=campaign_id,
        organization_id=current_user.organization_id,
    )

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    try:
        campaign = await campaign_service.update_status(
            db=db,
            campaign=campaign,
            new_status=CampaignStatus.CANCELLED,
        )
        return CampaignResponse.model_validate(campaign)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{campaign_id}/schedule", response_model=CampaignResponse)
async def schedule_campaign(
    campaign_id: str,
    data: CampaignScheduleRequest,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """Schedule a campaign to start at a specific time."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    campaign = await campaign_service.get_campaign(
        db=db,
        campaign_id=campaign_id,
        organization_id=current_user.organization_id,
    )

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Update scheduled times
    from app.schemas.campaign import CampaignUpdate
    update_data = CampaignUpdate(
        scheduled_start=data.scheduled_start,
        scheduled_end=data.scheduled_end,
    )

    try:
        campaign = await campaign_service.update_campaign(
            db=db,
            campaign=campaign,
            data=update_data,
        )

        # Update status to scheduled
        campaign = await campaign_service.update_status(
            db=db,
            campaign=campaign,
            new_status=CampaignStatus.SCHEDULED,
        )

        return CampaignResponse.model_validate(campaign)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============================================================================
# Campaign Contacts Endpoints
# ============================================================================

@router.get("/{campaign_id}/contacts", response_model=CampaignContactsResponse)
async def get_campaign_contacts(
    campaign_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[ContactStatus] = None,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """Get contacts for a campaign."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    try:
        contacts, total = await campaign_service.get_campaign_contacts(
            db=db,
            campaign_id=campaign_id,
            organization_id=current_user.organization_id,
            page=page,
            page_size=page_size,
            status=status,
        )

        # Transform to response with contact details
        items = []
        for cc in contacts:
            item = CampaignContactResponse(
                id=cc.id,
                campaign_id=cc.campaign_id,
                contact_id=cc.contact_id,
                status=cc.status,
                attempts=cc.attempts,
                last_attempt_at=cc.last_attempt_at,
                next_attempt_at=cc.next_attempt_at,
                last_disposition=cc.last_disposition,
                priority=cc.priority,
                phone_number=cc.contact.phone_number if cc.contact else None,
                first_name=cc.contact.first_name if cc.contact else None,
                last_name=cc.contact.last_name if cc.contact else None,
                created_at=cc.created_at,
                updated_at=cc.updated_at,
            )
            items.append(item)

        return CampaignContactsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ============================================================================
# Campaign Statistics Endpoints
# ============================================================================

@router.get("/{campaign_id}/stats", response_model=CampaignStatsResponse)
async def get_campaign_stats(
    campaign_id: str,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed statistics for a campaign."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    try:
        stats = await campaign_service.get_statistics(
            db=db,
            campaign_id=campaign_id,
            organization_id=current_user.organization_id,
        )
        return stats
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ============================================================================
# Campaign Report Endpoints
# ============================================================================

@router.post("/{campaign_id}/send-report", response_model=SendReportResponse)
async def send_campaign_report(
    campaign_id: str,
    request: SendReportRequest,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a campaign report email to specified recipients.

    The report is generated asynchronously via Celery and sent to the
    provided email addresses. Returns immediately with a task ID.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    # Verify campaign exists and belongs to organization
    campaign = await campaign_service.get_campaign(
        db=db,
        campaign_id=campaign_id,
        organization_id=current_user.organization_id,
    )

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Queue the email task
    task = send_campaign_report_task.delay(
        campaign_id=campaign_id,
        organization_id=current_user.organization_id,
        recipient_emails=[str(email) for email in request.recipient_emails],
    )

    return SendReportResponse(
        success=True,
        message=f"Report generation started. Sending to {len(request.recipient_emails)} recipient(s).",
        task_id=task.id,
        recipients_count=len(request.recipient_emails),
    )
