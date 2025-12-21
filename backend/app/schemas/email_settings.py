"""
Email Settings schemas for SMTP and Resend configuration.
"""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, EmailStr

from app.models.email_settings import EmailProvider


class EmailSettingsBase(BaseModel):
    """Base email settings schema."""
    provider: EmailProvider = Field(
        default=EmailProvider.RESEND,
        description="Email provider (resend or smtp)"
    )
    from_email: EmailStr = Field(..., description="From email address")
    from_name: str = Field("SIP Auto-Dialer", description="From name displayed in emails")
    # SMTP settings (optional, only needed for SMTP provider)
    smtp_host: Optional[str] = Field(None, description="SMTP server hostname")
    smtp_port: Optional[int] = Field(587, description="SMTP port (587 for TLS, 465 for SSL)")
    smtp_username: Optional[str] = Field(None, description="SMTP username/email")
    use_tls: bool = Field(True, description="Use STARTTLS")
    use_ssl: bool = Field(False, description="Use SSL/TLS on connect")


class EmailSettingsCreate(EmailSettingsBase):
    """Email settings creation schema."""
    # Resend settings
    resend_api_key: Optional[str] = Field(None, description="Resend API key")
    # SMTP settings
    smtp_password: Optional[str] = Field(None, description="SMTP password or app password")


class EmailSettingsUpdate(BaseModel):
    """Email settings update schema."""
    provider: Optional[EmailProvider] = None
    resend_api_key: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    from_email: Optional[EmailStr] = None
    from_name: Optional[str] = None
    use_tls: Optional[bool] = None
    use_ssl: Optional[bool] = None
    is_active: Optional[bool] = None


class EmailSettingsResponse(BaseModel):
    """Email settings response schema (excludes credentials)."""
    id: str
    organization_id: str
    provider: EmailProvider
    from_email: str
    from_name: str
    # SMTP settings (if using SMTP provider)
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    use_tls: bool = True
    use_ssl: bool = False
    # Status
    is_active: bool
    has_resend_key: bool = False  # Indicates if Resend API key is configured
    has_smtp_password: bool = False  # Indicates if SMTP password is configured
    last_test_at: Optional[datetime] = None
    last_test_success: Optional[bool] = None
    last_test_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EmailConnectionTestRequest(BaseModel):
    """Request schema for testing email connection with custom settings."""
    provider: EmailProvider = Field(
        default=EmailProvider.RESEND,
        description="Email provider to test"
    )
    # Resend settings
    resend_api_key: Optional[str] = None
    # SMTP settings
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    use_tls: Optional[bool] = True
    use_ssl: Optional[bool] = False


class EmailConnectionTestResponse(BaseModel):
    """Response schema for email connection test."""
    success: bool
    message: str
    server_response: Optional[str] = None


class SendTestEmailRequest(BaseModel):
    """Request schema for sending a test email."""
    to_email: EmailStr = Field(..., description="Recipient email address")


class SendTestEmailResponse(BaseModel):
    """Response schema for sending a test email."""
    success: bool
    message: str
    log_id: Optional[str] = None


class EmailLogResponse(BaseModel):
    """Email log response schema."""
    id: str
    recipient_email: str
    subject: str
    email_type: str
    status: str
    error_message: Optional[str] = None
    retry_count: int
    sent_at: Optional[datetime] = None
    campaign_id: Optional[str] = None
    smtp_message_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EmailLogListResponse(BaseModel):
    """Response schema for email log list."""
    items: List[EmailLogResponse]
    total: int
    offset: int
    limit: int


class SendReportRequest(BaseModel):
    """Request schema for sending a campaign report."""
    recipient_emails: List[EmailStr] = Field(
        ...,
        description="List of recipient email addresses",
        min_length=1
    )


class SendReportResponse(BaseModel):
    """Response schema for sending a report."""
    success: bool
    message: str
    task_id: Optional[str] = None
    recipients_count: int
