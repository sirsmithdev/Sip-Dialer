"""
IVR Flow schemas.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

from app.models.ivr import IVRFlowStatus, IVRNodeType


# =============================================================================
# Node Schemas
# =============================================================================

class IVRNodePosition(BaseModel):
    """Position of a node in the flow editor."""
    x: float
    y: float


class IVRNodeData(BaseModel):
    """Data for an IVR node. Structure depends on node type."""
    # Common fields
    label: Optional[str] = None

    # Audio-related
    audio_file_id: Optional[str] = None
    prompt_audio_id: Optional[str] = None

    # Menu options (key = DTMF digit, value = target node ID)
    options: Optional[Dict[str, str]] = None
    timeout: Optional[int] = Field(None, ge=1, le=60)
    max_retries: Optional[int] = Field(None, ge=1, le=10)

    # Survey question
    question_id: Optional[str] = None
    valid_inputs: Optional[List[str]] = None

    # Transfer
    transfer_number: Optional[str] = None

    # Conditional
    condition: Optional[str] = None
    true_target: Optional[str] = None
    false_target: Optional[str] = None

    # Variable
    variable_name: Optional[str] = None
    variable_value: Optional[str] = None

    # Wait for DTMF after playing audio
    wait_for_dtmf: Optional[bool] = False

    class Config:
        extra = "allow"  # Allow additional fields for extensibility


class IVRNode(BaseModel):
    """An IVR flow node."""
    id: str = Field(..., description="Unique node identifier")
    type: IVRNodeType = Field(..., description="Node type")
    position: IVRNodePosition = Field(..., description="Position in flow editor")
    data: IVRNodeData = Field(default_factory=IVRNodeData)


class IVREdge(BaseModel):
    """An edge connecting two nodes."""
    id: Optional[str] = None
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None


class IVRFlowDefinition(BaseModel):
    """Complete IVR flow definition."""
    nodes: List[IVRNode] = Field(default_factory=list)
    edges: List[IVREdge] = Field(default_factory=list)
    start_node: Optional[str] = None


class IVRViewport(BaseModel):
    """React Flow viewport state."""
    x: float = 0
    y: float = 0
    zoom: float = 1


# =============================================================================
# Version Schemas
# =============================================================================

class IVRFlowVersionBase(BaseModel):
    """Base version schema."""
    notes: Optional[str] = Field(None, max_length=1000)


class IVRFlowVersionCreate(IVRFlowVersionBase):
    """Schema for creating a new version."""
    definition: IVRFlowDefinition = Field(..., description="Flow definition")
    viewport: Optional[IVRViewport] = None


class IVRFlowVersionResponse(IVRFlowVersionBase):
    """Version response schema."""
    id: str
    flow_id: str
    version: int
    definition: Dict[str, Any]  # Raw dict for flexibility
    viewport: Optional[Dict[str, Any]] = None
    created_at: datetime
    created_by_id: Optional[str] = None

    class Config:
        from_attributes = True


# =============================================================================
# Flow Schemas
# =============================================================================

class IVRFlowBase(BaseModel):
    """Base IVR flow schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Flow name")
    description: Optional[str] = Field(None, max_length=1000)


class IVRFlowCreate(IVRFlowBase):
    """Schema for creating an IVR flow."""
    definition: Optional[IVRFlowDefinition] = Field(
        None,
        description="Initial flow definition (creates first version)"
    )


class IVRFlowUpdate(BaseModel):
    """Schema for updating IVR flow metadata."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class IVRFlowResponse(IVRFlowBase):
    """IVR flow response schema."""
    id: str
    organization_id: str
    status: IVRFlowStatus
    active_version_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[str] = None

    # Include latest version info if available
    version_count: Optional[int] = None

    class Config:
        from_attributes = True


class IVRFlowDetailResponse(IVRFlowResponse):
    """Detailed IVR flow response with active version definition."""
    active_version: Optional[IVRFlowVersionResponse] = None


class IVRFlowListResponse(BaseModel):
    """Response for listing IVR flows."""
    items: List[IVRFlowResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# Action Schemas
# =============================================================================

class IVRFlowPublishRequest(BaseModel):
    """Request to publish a specific version."""
    version_id: Optional[str] = Field(
        None,
        description="Version ID to publish. If not provided, publishes the latest version."
    )


class IVRFlowPublishResponse(BaseModel):
    """Response after publishing."""
    id: str
    status: IVRFlowStatus
    active_version_id: str
    message: str


class IVRFlowDuplicateRequest(BaseModel):
    """Request to duplicate an IVR flow."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class IVRFlowValidationResult(BaseModel):
    """Result of validating an IVR flow definition."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
