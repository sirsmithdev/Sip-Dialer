"""
User schemas.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    role: UserRole = UserRole.OPERATOR


class UserCreate(UserBase):
    """User creation schema."""
    password: str
    organization_id: Optional[str] = None


class UserUpdate(BaseModel):
    """User update schema."""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class UserResponse(UserBase):
    """User response schema."""
    id: str
    organization_id: Optional[str] = None
    is_superuser: bool = False
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    """User in database schema (includes hashed password)."""
    hashed_password: str
