"""
Settings endpoints (SIP/PJSIP and Email configuration).
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_db, get_current_active_user, require_roles
from app.schemas.sip_settings import (
    SIPSettingsCreate,
    SIPSettingsUpdate,
    SIPSettingsResponse,
    SIPConnectionTestResponse,
)
from app.schemas.email_settings import (
    EmailSettingsCreate,
    EmailSettingsUpdate,
    EmailSettingsResponse,
    EmailConnectionTestRequest,
    EmailConnectionTestResponse,
    SendTestEmailRequest,
    SendTestEmailResponse,
    EmailLogResponse,
    EmailLogListResponse,
)
from app.services.sip_settings_service import SIPSettingsService
from app.services.connection_test_service import ConnectionTestService
from app.services.email_service import EmailService
from app.models.user import User, UserRole
from app.models.email_settings import EmailSettings, EmailProvider
from app.models.email_log import EmailLog, EmailType, EmailStatus

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


@router.get("/dialer/status")
async def get_dialer_status(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """
    Get the current status of the dialer engine and call manager.

    Returns:
    - SIP registration status
    - Active calls count
    - Call manager status (concurrent calls per campaign)
    """
    import json
    from app.db.redis import get_redis

    try:
        r = await get_redis()

        # Get SIP status
        sip_status_data = await r.get("dialer:sip_status")
        sip_status = json.loads(sip_status_data) if sip_status_data else None

        # Get call manager status (if available)
        call_manager_data = await r.get("dialer:call_manager_status")
        call_manager_status = json.loads(call_manager_data) if call_manager_data else None

        # Note: Don't close the shared Redis client here

        return {
            "sip": sip_status or {
                "status": "unknown",
                "message": "Dialer engine not running or not connected"
            },
            "call_manager": call_manager_status,
            "is_online": sip_status and sip_status.get("status") == "registered"
        }

    except Exception as e:
        logger.error(f"Failed to get dialer status: {e}")
        return {
            "sip": {
                "status": "error",
                "message": f"Failed to get status: {str(e)}"
            },
            "call_manager": None,
            "is_online": False
        }


@router.post("/dialer/test-call")
async def make_test_call(
    phone_number: str = Query(..., description="Phone number to call"),
    caller_id: Optional[str] = Query(None, description="Caller ID to use"),
    audio_file: Optional[str] = Query(None, description="Audio file ID to play for human answer"),
    voicemail_audio_file: Optional[str] = Query(None, description="Audio file ID to play for voicemail"),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """
    Make a test call to verify SIP configuration.

    Sends a request to the dialer engine via Redis to place an outbound call.
    The call will connect and optionally play an audio file if specified.

    Returns:
    - success: Whether the call request was sent
    - message: Status message
    """
    import json
    from app.db.redis import get_redis

    try:
        r = await get_redis()

        # Check if dialer is online - try sip_status first, fallback to call_manager_status
        sip_status_data = await r.get("dialer:sip_status")
        call_manager_data = await r.get("dialer:call_manager_status")

        dialer_online = False
        if sip_status_data:
            sip_status = json.loads(sip_status_data)
            if sip_status.get("status") == "registered":
                dialer_online = True
            else:
                return {
                    "success": False,
                    "message": "Dialer is not registered with SIP server. Please check SIP settings."
                }
        elif call_manager_data:
            # Dialer is running (call manager publishing status) - SIP status may have expired
            dialer_online = True

        if not dialer_online:
            return {
                "success": False,
                "message": "Dialer engine is not running or not connected."
            }

        # Publish test call request to Redis
        call_request = {
            "destination": phone_number,
            "caller_id": caller_id or "",
            "audio_file": audio_file,
            "voicemail_audio_file": voicemail_audio_file
        }
        await r.publish("dialer:test_call", json.dumps(call_request))

        logger.info(f"Test call request sent to {phone_number} by user {current_user.email}")

        return {
            "success": True,
            "message": f"Test call initiated to {phone_number}. Check dialer status for call progress."
        }

    except Exception as e:
        logger.error(f"Failed to initiate test call: {e}")
        return {
            "success": False,
            "message": f"Failed to initiate test call: {str(e)}"
        }


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


# =============================================================================
# Email Settings Endpoints
# =============================================================================


def _email_settings_to_response(settings: EmailSettings) -> EmailSettingsResponse:
    """Convert EmailSettings model to response schema with computed fields."""
    return EmailSettingsResponse(
        id=str(settings.id),
        organization_id=str(settings.organization_id),
        provider=settings.provider,
        from_email=settings.from_email,
        from_name=settings.from_name,
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_username=settings.smtp_username,
        use_tls=settings.use_tls,
        use_ssl=settings.use_ssl,
        is_active=settings.is_active,
        has_resend_key=bool(settings.resend_api_key_encrypted),
        has_smtp_password=bool(settings.smtp_password_encrypted),
        last_test_at=settings.last_test_at,
        last_test_success=settings.last_test_success,
        last_test_error=settings.last_test_error,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


@router.get("/email", response_model=EmailSettingsResponse)
async def get_email_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """
    Get email settings for the current user's organization.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    result = await db.execute(
        select(EmailSettings).where(
            EmailSettings.organization_id == current_user.organization_id
        )
    )
    settings = result.scalar_one_or_none()

    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email settings not configured"
        )

    return _email_settings_to_response(settings)


@router.post("/email", response_model=EmailSettingsResponse, status_code=status.HTTP_201_CREATED)
async def create_email_settings(
    settings_in: EmailSettingsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Create email settings for the current user's organization.

    Supports both Resend API and SMTP providers.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    # Check if settings already exist
    result = await db.execute(
        select(EmailSettings).where(
            EmailSettings.organization_id == current_user.organization_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email settings already exist. Use PUT to update."
        )

    # Validate provider-specific fields
    if settings_in.provider == EmailProvider.RESEND and not settings_in.resend_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resend API key is required when using Resend provider"
        )

    if settings_in.provider == EmailProvider.SMTP:
        if not settings_in.smtp_host:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SMTP host is required when using SMTP provider"
            )
        if not settings_in.smtp_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SMTP password is required when using SMTP provider"
            )

    email_service = EmailService(db)
    settings = await email_service.create_email_settings(
        organization_id=current_user.organization_id,
        provider=settings_in.provider,
        resend_api_key=settings_in.resend_api_key,
        smtp_host=settings_in.smtp_host,
        smtp_port=settings_in.smtp_port,
        smtp_username=settings_in.smtp_username,
        smtp_password=settings_in.smtp_password,
        from_email=settings_in.from_email,
        from_name=settings_in.from_name,
        use_tls=settings_in.use_tls,
        use_ssl=settings_in.use_ssl,
    )
    return _email_settings_to_response(settings)


@router.put("/email", response_model=EmailSettingsResponse)
async def update_email_settings(
    settings_in: EmailSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Update email settings for the current user's organization.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    result = await db.execute(
        select(EmailSettings).where(
            EmailSettings.organization_id == current_user.organization_id
        )
    )
    settings = result.scalar_one_or_none()

    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email settings not found. Use POST to create."
        )

    email_service = EmailService(db)
    settings = await email_service.update_email_settings(
        email_settings=settings,
        provider=settings_in.provider,
        resend_api_key=settings_in.resend_api_key,
        smtp_host=settings_in.smtp_host,
        smtp_port=settings_in.smtp_port,
        smtp_username=settings_in.smtp_username,
        smtp_password=settings_in.smtp_password,
        from_email=settings_in.from_email,
        from_name=settings_in.from_name,
        use_tls=settings_in.use_tls,
        use_ssl=settings_in.use_ssl,
        is_active=settings_in.is_active,
    )
    return _email_settings_to_response(settings)


@router.delete("/email", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Delete email settings for the current user's organization.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    result = await db.execute(
        select(EmailSettings).where(
            EmailSettings.organization_id == current_user.organization_id
        )
    )
    settings = result.scalar_one_or_none()

    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email settings not found"
        )

    await db.delete(settings)
    await db.commit()


@router.post("/email/test", response_model=EmailConnectionTestResponse)
async def test_email_connection(
    test_request: Optional[EmailConnectionTestRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """
    Test email connection.

    If no parameters provided, tests the saved organization settings.
    If parameters provided, tests with those custom settings.

    Supports both Resend API and SMTP providers.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    email_service = EmailService(db)

    if test_request:
        # Test with custom settings based on provider
        if test_request.provider == EmailProvider.RESEND:
            result = await email_service.test_connection(
                provider=EmailProvider.RESEND,
                resend_api_key=test_request.resend_api_key,
            )
        elif test_request.smtp_host:
            result = await email_service.test_connection(
                provider=EmailProvider.SMTP,
                smtp_host=test_request.smtp_host,
                smtp_port=test_request.smtp_port,
                smtp_username=test_request.smtp_username,
                smtp_password=test_request.smtp_password,
                use_tls=test_request.use_tls,
                use_ssl=test_request.use_ssl,
            )
        else:
            # Test with saved settings
            result = await email_service.test_connection(
                organization_id=current_user.organization_id
            )
    else:
        # Test with saved settings
        result = await email_service.test_connection(
            organization_id=current_user.organization_id
        )

    return EmailConnectionTestResponse(
        success=result.success,
        message="Connection successful" if result.success else (result.error or "Connection failed"),
        server_response=result.server_response
    )


@router.post("/email/send-test", response_model=SendTestEmailResponse)
async def send_test_email(
    request: SendTestEmailRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """
    Send a test email to verify email configuration.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    email_service = EmailService(db)
    result = await email_service.send_test_email(
        organization_id=current_user.organization_id,
        to_email=request.to_email,
    )

    return SendTestEmailResponse(
        success=result.success,
        message="Test email sent successfully" if result.success else (result.error or "Failed to send"),
        log_id=result.log_id
    )


@router.get("/email/logs", response_model=EmailLogListResponse)
async def get_email_logs(
    email_type: Optional[str] = Query(None, description="Filter by email type"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    campaign_id: Optional[str] = Query(None, description="Filter by campaign ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))
):
    """
    Get email logs for the current user's organization.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with an organization"
        )

    # Convert string filters to enums
    email_type_enum = None
    if email_type:
        try:
            email_type_enum = EmailType(email_type)
        except ValueError:
            pass

    status_enum = None
    if status_filter:
        try:
            status_enum = EmailStatus(status_filter)
        except ValueError:
            pass

    email_service = EmailService(db)
    logs = await email_service.get_email_logs(
        organization_id=current_user.organization_id,
        email_type=email_type_enum,
        status=status_enum,
        campaign_id=campaign_id,
        limit=limit,
        offset=offset,
    )

    # Get total count
    query = select(func.count(EmailLog.id)).where(
        EmailLog.organization_id == current_user.organization_id
    )
    if email_type_enum:
        query = query.where(EmailLog.email_type == email_type_enum)
    if status_enum:
        query = query.where(EmailLog.status == status_enum)
    if campaign_id:
        query = query.where(EmailLog.campaign_id == campaign_id)

    total_result = await db.execute(query)
    total = total_result.scalar() or 0

    return EmailLogListResponse(
        items=[EmailLogResponse(
            id=log.id,
            recipient_email=log.recipient_email,
            subject=log.subject,
            email_type=log.email_type.value,
            status=log.status.value,
            error_message=log.error_message,
            retry_count=log.retry_count,
            sent_at=log.sent_at,
            campaign_id=log.campaign_id,
            smtp_message_id=log.smtp_message_id,
            created_at=log.created_at,
        ) for log in logs],
        total=total,
        offset=offset,
        limit=limit,
    )
