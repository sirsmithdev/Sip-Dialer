"""
Survey response model for storing IVR survey data.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Text, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin, TimestampMixin


class SurveyResponse(Base, UUIDMixin, TimestampMixin):
    """
    Survey response model for capturing IVR survey responses.

    Each row represents a complete survey response from a single call.
    Individual question responses are stored in the responses JSON field.
    """

    __tablename__ = "survey_responses"

    # Call reference
    call_log_id: Mapped[str] = mapped_column(
        ForeignKey("call_logs.id"), nullable=False, index=True
    )

    # Campaign reference
    campaign_id: Mapped[str] = mapped_column(
        ForeignKey("campaigns.id"), nullable=False, index=True
    )

    # Contact reference
    contact_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("contacts.id"), nullable=True, index=True
    )

    # IVR Flow reference
    ivr_flow_id: Mapped[str] = mapped_column(
        ForeignKey("ivr_flows.id"), nullable=False
    )
    ivr_flow_version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Phone number for reference
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Survey responses as JSON
    # Structure:
    # {
    #   "question_1_id": {
    #     "question_text": "How satisfied are you?",
    #     "response": "5",
    #     "timestamp": "2024-01-15T10:30:00Z"
    #   },
    #   "question_2_id": {
    #     "question_text": "Would you recommend us?",
    #     "response": "1",
    #     "timestamp": "2024-01-15T10:30:15Z"
    #   }
    # }
    responses: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Completion status
    is_complete: Mapped[bool] = mapped_column(default=False)
    questions_answered: Mapped[int] = mapped_column(Integer, default=0)
    total_questions: Mapped[int] = mapped_column(Integer, default=0)

    # Timing
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Additional notes or metadata
    notes: Mapped[Optional[str]] = mapped_column(Text)
    survey_metadata: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    def __repr__(self) -> str:
        return f"<SurveyResponse {self.id} call={self.call_log_id}>"
