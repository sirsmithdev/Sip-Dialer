"""
Reports and Analytics API endpoints.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_roles
from app.models.user import User, UserRole
from app.schemas.reporting import (
    CallAnalyticsResponse,
    CampaignComparisonResponse,
    CampaignTrendsResponse,
    ContactListQualityResponse,
    RealTimeMetrics,
    IVRSurveyAnalyticsResponse,
    ComplianceReportResponse,
)
from app.services.reporting_service import ReportingService

router = APIRouter()
reporting_service = ReportingService()


# ============================================================================
# Call Analytics Endpoints
# ============================================================================

@router.get("/call-analytics", response_model=CallAnalyticsResponse)
async def get_call_analytics(
    campaign_id: Optional[str] = Query(None, description="Filter by campaign ID"),
    date_from: datetime = Query(..., description="Start date (ISO 8601)"),
    date_to: datetime = Query(..., description="End date (ISO 8601)"),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive call analytics report.

    Includes:
    - Duration statistics (average, median, min, max)
    - Hourly and daily distribution
    - Outcome breakdown
    - AMD accuracy
    - Failure reasons
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    try:
        return await reporting_service.get_call_analytics(
            db=db,
            organization_id=current_user.organization_id,
            campaign_id=campaign_id,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============================================================================
# Campaign Performance Endpoints
# ============================================================================

@router.get("/campaign-comparison", response_model=CampaignComparisonResponse)
async def get_campaign_comparison(
    campaign_ids: List[str] = Query(..., description="Campaign IDs to compare"),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """
    Compare multiple campaigns side-by-side.

    Metrics include:
    - Total calls
    - Answer rate
    - Human rate
    - Average talk time
    - Contacts per hour
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    if len(campaign_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 campaigns required for comparison",
        )

    try:
        return await reporting_service.get_campaign_comparison(
            db=db,
            organization_id=current_user.organization_id,
            campaign_ids=campaign_ids,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/campaign-trends/{campaign_id}", response_model=CampaignTrendsResponse)
async def get_campaign_trends(
    campaign_id: str,
    date_from: datetime = Query(..., description="Start date (ISO 8601)"),
    date_to: datetime = Query(..., description="End date (ISO 8601)"),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get historical performance trends for a campaign.

    Shows daily and weekly statistics over time.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    try:
        return await reporting_service.get_campaign_trends(
            db=db,
            organization_id=current_user.organization_id,
            campaign_id=campaign_id,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ============================================================================
# Contact List Quality Endpoints
# ============================================================================

@router.get("/contact-list-quality", response_model=ContactListQualityResponse)
async def get_contact_list_quality(
    list_id: Optional[str] = Query(None, description="Contact list ID"),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze contact list data quality.

    Includes:
    - Valid/invalid contact counts
    - DNC hits
    - Answer rates by list
    - Best performing lists
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    try:
        return await reporting_service.get_contact_list_quality(
            db=db,
            organization_id=current_user.organization_id,
            list_id=list_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ============================================================================
# Real-Time Monitoring Endpoints
# ============================================================================

@router.get("/real-time-metrics", response_model=RealTimeMetrics)
async def get_real_time_metrics(
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get live campaign metrics for real-time monitoring.

    Includes:
    - Active calls
    - Queued calls
    - Calls per minute
    - Current answer rate
    - Line utilization
    - Active campaigns count
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    return await reporting_service.get_real_time_metrics(
        db=db,
        organization_id=current_user.organization_id,
    )


# ============================================================================
# IVR & Survey Analytics Endpoints
# ============================================================================

@router.get("/ivr-survey-analytics", response_model=IVRSurveyAnalyticsResponse)
async def get_ivr_survey_analytics(
    survey_id: Optional[str] = Query(None, description="Survey ID"),
    date_from: datetime = Query(..., description="Start date (ISO 8601)"),
    date_to: datetime = Query(..., description="End date (ISO 8601)"),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze IVR and survey response data.

    Includes:
    - Total responses
    - Completion rate
    - Response distribution by question
    - Drop-off points
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    try:
        return await reporting_service.get_ivr_survey_analytics(
            db=db,
            organization_id=current_user.organization_id,
            survey_id=survey_id,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ============================================================================
# Compliance & Quality Endpoints
# ============================================================================

@router.get("/compliance", response_model=ComplianceReportResponse)
async def get_compliance_report(
    date_from: datetime = Query(..., description="Start date (ISO 8601)"),
    date_to: datetime = Query(..., description="End date (ISO 8601)"),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate TCPA and quality compliance report.

    Includes:
    - Calls outside permitted hours
    - TCPA violations
    - DNC compliance
    - Call recording rate
    - Quality scores
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    return await reporting_service.get_compliance_report(
        db=db,
        organization_id=current_user.organization_id,
        date_from=date_from,
        date_to=date_to,
    )
