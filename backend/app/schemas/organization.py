"""
Organization schemas.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class OrganizationBase(BaseModel):
    """Base organization schema."""
    name: str
    slug: str
    is_active: bool = True
    max_concurrent_calls: int = 10
    timezone: str = "UTC"


class OrganizationCreate(OrganizationBase):
    """Organization creation schema."""
    pass


class OrganizationUpdate(BaseModel):
    """Organization update schema."""
    name: Optional[str] = None
    slug: Optional[str] = None
    is_active: Optional[bool] = None
    max_concurrent_calls: Optional[int] = None
    timezone: Optional[str] = None


class OrganizationResponse(OrganizationBase):
    """Organization response schema."""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
