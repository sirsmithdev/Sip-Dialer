"""
IVR Flow models.
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey, Text, Integer, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import Organization


class IVRNodeType(str, enum.Enum):
    """Types of IVR nodes."""
    START = "start"
    PLAY_AUDIO = "play_audio"
    MENU = "menu"
    SURVEY_QUESTION = "survey_question"
    RECORD = "record"
    TRANSFER = "transfer"
    CONDITIONAL = "conditional"
    SET_VARIABLE = "set_variable"
    HANGUP = "hangup"


class IVRFlowStatus(str, enum.Enum):
    """IVR flow status."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class IVRFlow(Base, UUIDMixin, TimestampMixin):
    """IVR Flow model for storing customizable IVR configurations."""

    __tablename__ = "ivr_flows"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Organization
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"), nullable=False
    )
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="ivr_flows"
    )

    # Status
    status: Mapped[IVRFlowStatus] = mapped_column(
        SQLEnum(IVRFlowStatus), default=IVRFlowStatus.DRAFT
    )

    # Active version
    active_version_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("ivr_flow_versions.id", use_alter=True), nullable=True
    )

    # Created by
    created_by_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # Versions
    versions: Mapped[List["IVRFlowVersion"]] = relationship(
        "IVRFlowVersion",
        back_populates="flow",
        foreign_keys="IVRFlowVersion.flow_id",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<IVRFlow {self.name}>"


class IVRFlowVersion(Base, UUIDMixin, TimestampMixin):
    """Versioned IVR flow definition."""

    __tablename__ = "ivr_flow_versions"

    # Parent flow
    flow_id: Mapped[str] = mapped_column(
        ForeignKey("ivr_flows.id"), nullable=False
    )
    flow: Mapped["IVRFlow"] = relationship(
        "IVRFlow", back_populates="versions", foreign_keys=[flow_id]
    )

    # Version number
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Flow definition as JSON
    # Structure:
    # {
    #   "nodes": [
    #     {
    #       "id": "node_1",
    #       "type": "play_audio",
    #       "position": {"x": 100, "y": 100},
    #       "data": {
    #         "audio_file_id": "...",
    #         "wait_for_dtmf": false
    #       }
    #     },
    #     {
    #       "id": "node_2",
    #       "type": "menu",
    #       "position": {"x": 100, "y": 200},
    #       "data": {
    #         "prompt_audio_id": "...",
    #         "timeout": 5,
    #         "max_retries": 3,
    #         "options": {
    #           "1": "node_3",
    #           "2": "node_4",
    #           "timeout": "node_5"
    #         }
    #       }
    #     },
    #     {
    #       "id": "node_3",
    #       "type": "survey_question",
    #       "data": {
    #         "question_id": "satisfaction",
    #         "prompt_audio_id": "...",
    #         "valid_inputs": ["1", "2", "3", "4", "5"]
    #       }
    #     }
    #   ],
    #   "edges": [
    #     {"source": "node_1", "target": "node_2"},
    #     ...
    #   ],
    #   "start_node": "node_1"
    # }
    definition: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # React Flow viewport state for UI restoration
    viewport: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Notes for this version
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Created by
    created_by_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    def __repr__(self) -> str:
        return f"<IVRFlowVersion {self.flow_id} v{self.version}>"
