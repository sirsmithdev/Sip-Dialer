"""
Settings endpoints (SIP/PJSIP configuration).
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user, require_roles
from app.schemas.sip_settings import (
    SIPSettingsCreate,
    SIPSettingsUpdate,
    SIPSettingsResponse,
    SIPConnectionTestResponse,
)
from app.services.sip_settings_service import SIPSettingsService
from app.services.connection_test_service import ConnectionTestService
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/sip", response_model=SIPSettingsResponse)
async def get_sip_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """
    Get SIP settings for the current user's organization.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = SIPSettingsService(db)
    settings = await service.get_by_organization(current_user.organization_id)

    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SIP settings not configured"
        )

    return settings


@router.post("/sip", response_model=SIPSettingsResponse, status_code=status.HTTP_201_CREATED)
async def create_sip_settings(
    settings_in: SIPSettingsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Create SIP settings for the current user's organization.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = SIPSettingsService(db)

    # Check if settings already exist
    existing = await service.get_by_organization(current_user.organization_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SIP settings already exist. Use PUT to update."
        )

    settings = await service.create(current_user.organization_id, settings_in)
    return settings


@router.put("/sip", response_model=SIPSettingsResponse)
async def update_sip_settings(
    settings_in: SIPSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Update SIP settings for the current user's organization.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = SIPSettingsService(db)
    settings = await service.get_by_organization(current_user.organization_id)

    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SIP settings not found. Use POST to create."
        )

    settings = await service.update(settings, settings_in)
    return settings


@router.post("/sip/test", response_model=SIPConnectionTestResponse)
async def test_sip_connection(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """
    Test SIP connection to the PJSIP server.

    Sends a SIP OPTIONS request to verify:
    - Network connectivity to the SIP server
    - DNS resolution
    - SIP server responsiveness
    - Server capabilities
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = SIPSettingsService(db)
    settings = await service.get_by_organization(current_user.organization_id)

    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SIP settings not configured"
        )

    # Use the connection test service for proper SIP OPTIONS test
    test_service = ConnectionTestService(db, logger)
    return await test_service.test_sip_connection(settings)


@router.delete("/sip", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sip_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Delete SIP settings for the current user's organization.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    service = SIPSettingsService(db)
    settings = await service.get_by_organization(current_user.organization_id)

    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SIP settings not found"
        )

    await service.delete(settings)
