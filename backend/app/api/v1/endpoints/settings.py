"""
Settings endpoints (SIP configuration).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user, require_roles
from app.schemas.sip_settings import (
    SIPSettingsCreate,
    SIPSettingsUpdate,
    SIPSettingsResponse,
    SIPConnectionTestRequest,
    SIPConnectionTestResponse,
)
from app.services.sip_settings_service import SIPSettingsService
from app.models.user import User, UserRole

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
    test_request: SIPConnectionTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """
    Test SIP/AMI connection to the PBX.
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

    if test_request.test_type == "ami":
        # Test AMI connection
        try:
            import socket

            ami_host = settings.ami_host or settings.sip_server
            ami_port = settings.ami_port

            # Simple TCP connection test
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((ami_host, ami_port))
            sock.close()

            if result == 0:
                return SIPConnectionTestResponse(
                    success=True,
                    message=f"Successfully connected to AMI at {ami_host}:{ami_port}",
                    details={"host": ami_host, "port": ami_port}
                )
            else:
                return SIPConnectionTestResponse(
                    success=False,
                    message=f"Could not connect to AMI at {ami_host}:{ami_port}",
                    details={"error_code": result}
                )
        except socket.timeout:
            return SIPConnectionTestResponse(
                success=False,
                message="Connection timed out"
            )
        except Exception as e:
            return SIPConnectionTestResponse(
                success=False,
                message=f"Connection failed: {str(e)}"
            )

    elif test_request.test_type == "sip":
        # Basic SIP OPTIONS ping (simplified)
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)

            sip_server = settings.sip_server
            sip_port = settings.sip_port

            # Simple UDP connectivity test
            sock.sendto(b"OPTIONS sip:ping@test SIP/2.0\r\n\r\n", (sip_server, sip_port))
            sock.close()

            return SIPConnectionTestResponse(
                success=True,
                message=f"SIP OPTIONS sent to {sip_server}:{sip_port}",
                details={"host": sip_server, "port": sip_port, "note": "Basic connectivity test only"}
            )
        except Exception as e:
            return SIPConnectionTestResponse(
                success=False,
                message=f"SIP test failed: {str(e)}"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid test type. Use 'ami' or 'sip'."
        )


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
