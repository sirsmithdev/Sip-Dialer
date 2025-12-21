"""
Email Service for sending emails via SMTP or Resend API.
Supports async sending, HTML emails, and email logging.
"""
import asyncio
import logging
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from dataclasses import dataclass

import aiosmtplib
import resend
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import encrypt_value, decrypt_value
from app.models.email_settings import EmailSettings, EmailProvider
from app.models.email_log import EmailLog, EmailType, EmailStatus


logger = logging.getLogger(__name__)


@dataclass
class EmailResult:
    """Result of an email send operation."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    log_id: Optional[str] = None


@dataclass
class ConnectionTestResult:
    """Result of email connection test."""
    success: bool
    error: Optional[str] = None
    server_response: Optional[str] = None


class EmailService:
    """
    Service for sending emails via SMTP or Resend API.

    Supports:
    - Organization-specific email settings
    - Fallback to global settings
    - Async email sending
    - Email logging for audit trail
    - Multiple providers (SMTP, Resend)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_email_settings(self, organization_id: str) -> Optional[EmailSettings]:
        """Get email settings for an organization."""
        result = await self.db.execute(
            select(EmailSettings).where(
                EmailSettings.organization_id == organization_id,
                EmailSettings.is_active == True
            )
        )
        return result.scalar_one_or_none()

    async def create_email_settings(
        self,
        organization_id: str,
        provider: EmailProvider = EmailProvider.RESEND,
        # Resend settings
        resend_api_key: Optional[str] = None,
        # SMTP settings
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        use_tls: bool = True,
        use_ssl: bool = False,
        # Common settings
        from_email: str = "",
        from_name: str = "SIP Auto-Dialer",
    ) -> EmailSettings:
        """Create email settings for an organization."""
        email_settings = EmailSettings(
            organization_id=organization_id,
            provider=provider,
            # Resend
            resend_api_key_encrypted=encrypt_value(resend_api_key) if resend_api_key else None,
            # SMTP
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            smtp_password_encrypted=encrypt_value(smtp_password) if smtp_password else None,
            use_tls=use_tls,
            use_ssl=use_ssl,
            # Common
            from_email=from_email,
            from_name=from_name,
            is_active=False,
        )
        self.db.add(email_settings)
        await self.db.commit()
        await self.db.refresh(email_settings)
        return email_settings

    async def update_email_settings(
        self,
        email_settings: EmailSettings,
        provider: Optional[EmailProvider] = None,
        resend_api_key: Optional[str] = None,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        use_tls: Optional[bool] = None,
        use_ssl: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> EmailSettings:
        """Update email settings."""
        if provider is not None:
            email_settings.provider = provider
        if resend_api_key is not None:
            email_settings.resend_api_key_encrypted = encrypt_value(resend_api_key)
        if smtp_host is not None:
            email_settings.smtp_host = smtp_host
        if smtp_port is not None:
            email_settings.smtp_port = smtp_port
        if smtp_username is not None:
            email_settings.smtp_username = smtp_username
        if smtp_password is not None:
            email_settings.smtp_password_encrypted = encrypt_value(smtp_password)
        if from_email is not None:
            email_settings.from_email = from_email
        if from_name is not None:
            email_settings.from_name = from_name
        if use_tls is not None:
            email_settings.use_tls = use_tls
        if use_ssl is not None:
            email_settings.use_ssl = use_ssl
        if is_active is not None:
            email_settings.is_active = is_active

        await self.db.commit()
        await self.db.refresh(email_settings)
        return email_settings

    def _get_decrypted_password(self, email_settings: EmailSettings) -> Optional[str]:
        """Get decrypted SMTP password."""
        if email_settings.smtp_password_encrypted:
            return decrypt_value(email_settings.smtp_password_encrypted)
        return None

    def _get_decrypted_resend_key(self, email_settings: EmailSettings) -> Optional[str]:
        """Get decrypted Resend API key."""
        if email_settings.resend_api_key_encrypted:
            return decrypt_value(email_settings.resend_api_key_encrypted)
        return None

    def _get_global_smtp_config(self) -> dict:
        """Get global SMTP configuration from settings."""
        return {
            "hostname": settings.smtp_host,
            "port": settings.smtp_port,
            "username": settings.smtp_username,
            "password": settings.smtp_password,
            "from_email": settings.smtp_from_email,
            "from_name": settings.smtp_from_name,
            "use_tls": settings.smtp_use_tls,
        }

    async def _create_email_log(
        self,
        organization_id: str,
        recipient_email: str,
        subject: str,
        email_type: EmailType,
        campaign_id: Optional[str] = None,
        report_schedule_id: Optional[str] = None,
    ) -> EmailLog:
        """Create an email log entry."""
        email_log = EmailLog(
            organization_id=organization_id,
            recipient_email=recipient_email,
            subject=subject,
            email_type=email_type,
            status=EmailStatus.PENDING,
            campaign_id=campaign_id,
            report_schedule_id=report_schedule_id,
        )
        self.db.add(email_log)
        await self.db.commit()
        await self.db.refresh(email_log)
        return email_log

    async def _update_email_log(
        self,
        email_log: EmailLog,
        status: EmailStatus,
        error: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> EmailLog:
        """Update email log with send result."""
        email_log.status = status
        if error:
            email_log.error_message = error
            email_log.retry_count += 1
        if message_id:
            email_log.smtp_message_id = message_id
        if status == EmailStatus.SENT:
            email_log.sent_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(email_log)
        return email_log

    async def send_email(
        self,
        organization_id: str,
        to_emails: List[str],
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        email_type: EmailType = EmailType.SYSTEM_ALERT,
        campaign_id: Optional[str] = None,
        report_schedule_id: Optional[str] = None,
    ) -> List[EmailResult]:
        """
        Send an email to one or more recipients.

        Uses organization-specific settings if available,
        otherwise falls back to global settings.
        """
        results = []

        # Get email settings
        email_settings = await self.get_email_settings(organization_id)

        # Determine provider and config
        provider = EmailProvider.RESEND  # Default
        use_org_settings = False

        if email_settings:
            provider = email_settings.provider
            use_org_settings = True

        # Send to each recipient
        for recipient in to_emails:
            # Create log entry
            email_log = await self._create_email_log(
                organization_id=organization_id,
                recipient_email=recipient,
                subject=subject,
                email_type=email_type,
                campaign_id=campaign_id,
                report_schedule_id=report_schedule_id,
            )

            try:
                # Update status to sending
                await self._update_email_log(email_log, EmailStatus.SENDING)

                message_id = None

                if provider == EmailProvider.RESEND:
                    # Send via Resend
                    if use_org_settings:
                        message_id = await self._send_via_resend(
                            email_settings=email_settings,
                            recipient=recipient,
                            subject=subject,
                            body_html=body_html,
                            body_text=body_text,
                        )
                    else:
                        # Use global Resend settings
                        message_id = await self._send_via_resend_global(
                            recipient=recipient,
                            subject=subject,
                            body_html=body_html,
                            body_text=body_text,
                        )
                else:
                    # Send via SMTP
                    if use_org_settings:
                        smtp_config = {
                            "hostname": email_settings.smtp_host,
                            "port": email_settings.smtp_port,
                            "username": email_settings.smtp_username,
                            "password": self._get_decrypted_password(email_settings),
                            "from_email": email_settings.from_email,
                            "from_name": email_settings.from_name,
                            "use_tls": email_settings.use_tls,
                            "use_ssl": email_settings.use_ssl,
                        }
                    else:
                        # Fall back to global settings
                        if not settings.smtp_enabled or not settings.smtp_host:
                            raise Exception("Email not configured. Please configure SMTP settings.")
                        smtp_config = self._get_global_smtp_config()
                        smtp_config["use_ssl"] = False

                    # Build the email message
                    msg = MIMEMultipart("alternative")
                    msg["Subject"] = subject
                    msg["From"] = f"{smtp_config['from_name']} <{smtp_config['from_email']}>"
                    msg["To"] = recipient

                    if body_text:
                        text_part = MIMEText(body_text, "plain", "utf-8")
                        msg.attach(text_part)

                    html_part = MIMEText(body_html, "html", "utf-8")
                    msg.attach(html_part)

                    message_id = await self._send_via_smtp(msg, smtp_config)

                # Update log with success
                await self._update_email_log(
                    email_log, EmailStatus.SENT, message_id=message_id
                )

                results.append(EmailResult(
                    success=True,
                    message_id=message_id,
                    log_id=email_log.id
                ))

                logger.info(
                    f"Email sent successfully to {recipient} "
                    f"(type={email_type.value}, provider={provider.value}, log_id={email_log.id})"
                )

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to send email to {recipient}: {error_msg}")

                # Update log with failure
                await self._update_email_log(
                    email_log, EmailStatus.FAILED, error=error_msg
                )

                results.append(EmailResult(
                    success=False,
                    error=error_msg,
                    log_id=email_log.id
                ))

        return results

    async def _send_via_resend(
        self,
        email_settings: EmailSettings,
        recipient: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
    ) -> Optional[str]:
        """Send email via Resend using organization settings."""
        api_key = self._get_decrypted_resend_key(email_settings)
        if not api_key:
            raise Exception("Resend API key not configured")

        resend.api_key = api_key

        params = {
            "from": f"{email_settings.from_name} <{email_settings.from_email}>",
            "to": [recipient],
            "subject": subject,
            "html": body_html,
        }
        if body_text:
            params["text"] = body_text

        # Run in thread pool since resend library is synchronous
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: resend.Emails.send(params)
        )

        return response.get("id") if response else None

    async def _send_via_resend_global(
        self,
        recipient: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
    ) -> Optional[str]:
        """Send email via Resend using global settings."""
        if not settings.resend_api_key:
            raise Exception("Global Resend API key not configured")

        resend.api_key = settings.resend_api_key

        from_email = settings.email_from_address or "noreply@example.com"
        from_name = settings.email_from_name or "SIP Auto-Dialer"

        params = {
            "from": f"{from_name} <{from_email}>",
            "to": [recipient],
            "subject": subject,
            "html": body_html,
        }
        if body_text:
            params["text"] = body_text

        # Run in thread pool since resend library is synchronous
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: resend.Emails.send(params)
        )

        return response.get("id") if response else None

    async def _send_via_smtp(
        self,
        msg: MIMEMultipart,
        smtp_config: dict,
    ) -> Optional[str]:
        """Send email via SMTP and return message ID."""
        # Determine connection parameters
        use_ssl = smtp_config.get("use_ssl", False)
        use_tls = smtp_config.get("use_tls", True) and not use_ssl

        # Connect and send
        smtp = aiosmtplib.SMTP(
            hostname=smtp_config["hostname"],
            port=smtp_config["port"],
            use_tls=use_ssl,  # SSL on connect
        )

        await smtp.connect()

        if use_tls:
            await smtp.starttls()

        if smtp_config.get("username") and smtp_config.get("password"):
            await smtp.login(smtp_config["username"], smtp_config["password"])

        response = await smtp.send_message(msg)
        await smtp.quit()

        # Extract message ID from response if available
        if response and len(response) > 0:
            return str(response[0])
        return None

    async def test_connection(
        self,
        organization_id: Optional[str] = None,
        provider: EmailProvider = EmailProvider.RESEND,
        # Resend settings
        resend_api_key: Optional[str] = None,
        # SMTP settings
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        use_tls: bool = True,
        use_ssl: bool = False,
    ) -> ConnectionTestResult:
        """
        Test email connection.

        Can test either:
        - Organization settings (if organization_id provided)
        - Custom settings (if explicit parameters provided)
        """
        try:
            # Determine which settings to use
            if organization_id and not smtp_host and not resend_api_key:
                # Use organization settings
                email_settings = await self.get_email_settings(organization_id)
                if not email_settings:
                    # Try to get even inactive settings for testing
                    result = await self.db.execute(
                        select(EmailSettings).where(
                            EmailSettings.organization_id == organization_id
                        )
                    )
                    email_settings = result.scalar_one_or_none()

                if not email_settings:
                    return ConnectionTestResult(
                        success=False,
                        error="No email settings found for organization"
                    )

                provider = email_settings.provider

                if provider == EmailProvider.RESEND:
                    return await self._test_resend(
                        api_key=self._get_decrypted_resend_key(email_settings)
                    )
                else:
                    return await self._test_smtp({
                        "hostname": email_settings.smtp_host,
                        "port": email_settings.smtp_port,
                        "username": email_settings.smtp_username,
                        "password": self._get_decrypted_password(email_settings),
                        "use_tls": email_settings.use_tls,
                        "use_ssl": email_settings.use_ssl,
                    })

            elif resend_api_key or provider == EmailProvider.RESEND:
                # Test Resend with provided key or global key
                return await self._test_resend(api_key=resend_api_key)

            elif smtp_host:
                # Test SMTP with provided settings
                return await self._test_smtp({
                    "hostname": smtp_host,
                    "port": smtp_port or 587,
                    "username": smtp_username,
                    "password": smtp_password,
                    "use_tls": use_tls,
                    "use_ssl": use_ssl,
                })

            else:
                # Test global settings
                if settings.resend_api_key:
                    return await self._test_resend(api_key=settings.resend_api_key)
                elif settings.smtp_host:
                    return await self._test_smtp({
                        "hostname": settings.smtp_host,
                        "port": settings.smtp_port,
                        "username": settings.smtp_username,
                        "password": settings.smtp_password,
                        "use_tls": settings.smtp_use_tls,
                        "use_ssl": False,
                    })
                else:
                    return ConnectionTestResult(
                        success=False,
                        error="No email settings configured"
                    )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Email connection test failed: {error_msg}")
            return ConnectionTestResult(
                success=False,
                error=error_msg
            )

    async def _test_resend(self, api_key: Optional[str] = None) -> ConnectionTestResult:
        """Test Resend API connection."""
        try:
            key = api_key or settings.resend_api_key
            if not key:
                return ConnectionTestResult(
                    success=False,
                    error="Resend API key not provided"
                )

            resend.api_key = key

            # Test by fetching domains (lightweight API call)
            loop = asyncio.get_event_loop()
            domains = await loop.run_in_executor(
                None,
                lambda: resend.Domains.list()
            )

            return ConnectionTestResult(
                success=True,
                server_response=f"Connected to Resend API. {len(domains.get('data', []))} domain(s) configured."
            )

        except Exception as e:
            return ConnectionTestResult(
                success=False,
                error=str(e)
            )

    async def _test_smtp(self, smtp_config: dict) -> ConnectionTestResult:
        """Test SMTP connection."""
        try:
            use_ssl_connect = smtp_config.get("use_ssl", False)
            use_tls_starttls = smtp_config.get("use_tls", True) and not use_ssl_connect

            smtp = aiosmtplib.SMTP(
                hostname=smtp_config["hostname"],
                port=smtp_config["port"],
                use_tls=use_ssl_connect,
                timeout=10,
            )

            await smtp.connect()

            if use_tls_starttls:
                await smtp.starttls()

            if smtp_config.get("username") and smtp_config.get("password"):
                await smtp.login(smtp_config["username"], smtp_config["password"])

            # Get server response
            response = await smtp.noop()
            await smtp.quit()

            return ConnectionTestResult(
                success=True,
                server_response=str(response) if response else "Connection successful"
            )

        except Exception as e:
            return ConnectionTestResult(
                success=False,
                error=str(e)
            )

    async def send_test_email(
        self,
        organization_id: str,
        to_email: str,
    ) -> EmailResult:
        """Send a test email to verify configuration."""
        subject = "SIP Auto-Dialer - Test Email"
        body_html = """
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #7c3aed;">Test Email</h2>
            <p>This is a test email from your SIP Auto-Dialer system.</p>
            <p>If you received this email, your email configuration is working correctly.</p>
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
            <p style="color: #6b7280; font-size: 12px;">
                SIP Auto-Dialer - Automated Calling System
            </p>
        </body>
        </html>
        """
        body_text = """
        Test Email

        This is a test email from your SIP Auto-Dialer system.
        If you received this email, your email configuration is working correctly.

        ---
        SIP Auto-Dialer - Automated Calling System
        """

        results = await self.send_email(
            organization_id=organization_id,
            to_emails=[to_email],
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            email_type=EmailType.TEST,
        )

        return results[0] if results else EmailResult(
            success=False,
            error="No result returned from send_email"
        )

    async def get_email_logs(
        self,
        organization_id: str,
        email_type: Optional[EmailType] = None,
        status: Optional[EmailStatus] = None,
        campaign_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[EmailLog]:
        """Get email logs for an organization with optional filters."""
        query = select(EmailLog).where(EmailLog.organization_id == organization_id)

        if email_type:
            query = query.where(EmailLog.email_type == email_type)
        if status:
            query = query.where(EmailLog.status == status)
        if campaign_id:
            query = query.where(EmailLog.campaign_id == campaign_id)

        query = query.order_by(EmailLog.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def retry_failed_email(self, email_log_id: str) -> EmailResult:
        """Retry sending a failed email."""
        result = await self.db.execute(
            select(EmailLog).where(EmailLog.id == email_log_id)
        )
        email_log = result.scalar_one_or_none()

        if not email_log:
            return EmailResult(success=False, error="Email log not found")

        if email_log.status != EmailStatus.FAILED:
            return EmailResult(
                success=False,
                error=f"Email is not in failed status (current: {email_log.status.value})"
            )

        # For retry, we need the original email content which we don't store
        # In a production system, you might want to store the content for retries
        return EmailResult(
            success=False,
            error="Retry not supported - email content not stored. Please send a new email."
        )
