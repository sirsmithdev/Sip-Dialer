"""
Report scheduling and execution models.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey, Text, Integer, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import Organization, User


class ReportType(str, enum.Enum):
    """Report type enumeration."""
    CAMPAIGN_SUMMARY = "campaign_summary"
    CALL_DETAIL = "call_detail"
    AGENT_PERFORMANCE = "agent_performance"
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_SUMMARY = "weekly_summary"
    CUSTOM = "custom"


class ReportFormat(str, enum.Enum):
    """Report output format."""
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"
    JSON = "json"


class ScheduleFrequency(str, enum.Enum):
    """Schedule frequency enumeration."""
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ExecutionStatus(str, enum.Enum):
    """Report execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportSchedule(Base, UUIDMixin, TimestampMixin):
    """Scheduled report configuration."""

    __tablename__ = "report_schedules"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Organization
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    organization: Mapped["Organization"] = relationship("Organization")

    # Report configuration
    report_type: Mapped[ReportType] = mapped_column(
        SQLEnum(ReportType), nullable=False
    )
    report_format: Mapped[ReportFormat] = mapped_column(
        SQLEnum(ReportFormat), default=ReportFormat.CSV
    )

    # Filters and parameters
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Scheduling
    frequency: Mapped[ScheduleFrequency] = mapped_column(
        SQLEnum(ScheduleFrequency), default=ScheduleFrequency.ONCE
    )
    scheduled_time: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Delivery
    email_recipients: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Created by
    created_by_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    def __repr__(self) -> str:
        return f"<ReportSchedule {self.name}>"


class ReportExecution(Base, UUIDMixin, TimestampMixin):
    """Report execution history."""

    __tablename__ = "report_executions"

    # Schedule reference (optional - can be ad-hoc)
    schedule_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("report_schedules.id"), nullable=True
    )
    schedule: Mapped[Optional["ReportSchedule"]] = relationship("ReportSchedule")

    # Organization
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )

    # Report details
    report_type: Mapped[ReportType] = mapped_column(
        SQLEnum(ReportType), nullable=False
    )
    report_format: Mapped[ReportFormat] = mapped_column(
        SQLEnum(ReportFormat), default=ReportFormat.CSV
    )
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Execution status
    status: Mapped[ExecutionStatus] = mapped_column(
        SQLEnum(ExecutionStatus), default=ExecutionStatus.PENDING
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Result
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Requested by
    requested_by_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    def __repr__(self) -> str:
        return f"<ReportExecution {self.id} status={self.status}>"
