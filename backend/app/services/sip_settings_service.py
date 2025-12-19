"""
SIP Settings service for managing PJSIP extension configuration.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sip_settings import SIPSettings, ConnectionStatus
from app.schemas.sip_settings import SIPSettingsCreate, SIPSettingsUpdate
from app.core.security import encrypt_value, decrypt_value


class SIPSettingsService:
    """Service for SIP settings operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_organization(self, organization_id: str) -> Optional[SIPSettings]:
        """Get SIP settings for an organization."""
        result = await self.db.execute(
            select(SIPSettings).where(SIPSettings.organization_id == organization_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        organization_id: str,
        settings_in: SIPSettingsCreate
    ) -> SIPSettings:
        """Create SIP settings for an organization."""
        settings = SIPSettings(
            organization_id=organization_id,
            sip_server=settings_in.sip_server,
            sip_port=settings_in.sip_port,
            sip_username=settings_in.sip_username,
            sip_password_encrypted=encrypt_value(settings_in.sip_password),
            sip_transport=settings_in.sip_transport,
            registration_required=settings_in.registration_required,
            register_expires=settings_in.register_expires,
            keepalive_enabled=settings_in.keepalive_enabled,
            keepalive_interval=settings_in.keepalive_interval,
            rtp_port_start=settings_in.rtp_port_start,
            rtp_port_end=settings_in.rtp_port_end,
            codecs=settings_in.codecs,
            default_caller_id=settings_in.default_caller_id,
            caller_id_name=settings_in.caller_id_name,
        )
        self.db.add(settings)
        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    async def update(
        self,
        settings: SIPSettings,
        settings_in: SIPSettingsUpdate
    ) -> SIPSettings:
        """Update SIP settings."""
        update_data = settings_in.model_dump(exclude_unset=True)

        # Handle password encryption
        if "sip_password" in update_data:
            update_data["sip_password_encrypted"] = encrypt_value(update_data.pop("sip_password"))

        for field, value in update_data.items():
            setattr(settings, field, value)

        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    async def update_connection_status(
        self,
        settings: SIPSettings,
        status: ConnectionStatus,
        error: Optional[str] = None
    ) -> SIPSettings:
        """Update connection status."""
        settings.connection_status = status
        if error:
            settings.last_error = error
        if status == ConnectionStatus.CONNECTED or status == ConnectionStatus.REGISTERED:
            from datetime import datetime, timezone
            settings.last_connected_at = datetime.now(timezone.utc)
            settings.last_error = None

        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    def get_decrypted_sip_password(self, settings: SIPSettings) -> str:
        """Get decrypted SIP password."""
        return decrypt_value(settings.sip_password_encrypted)

    async def delete(self, settings: SIPSettings) -> None:
        """Delete SIP settings."""
        await self.db.delete(settings)
        await self.db.commit()
