"""
User service for user management operations.
"""
from typing import Optional
from datetime import datetime, timezone as tz

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password


class UserService:
    """Service for user operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def create(self, user_in: UserCreate) -> User:
        """Create a new user."""
        user = User(
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
            first_name=user_in.first_name,
            last_name=user_in.last_name,
            is_active=user_in.is_active,
            role=user_in.role,
            organization_id=user_in.organization_id,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user: User, user_in: UserUpdate) -> User:
        """Update a user."""
        update_data = user_in.model_dump(exclude_unset=True)

        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user."""
        user = await self.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def update_last_login(self, user: User) -> User:
        """Update user's last login timestamp."""
        user.last_login = datetime.now(tz.utc)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        """Delete a user."""
        await self.db.delete(user)
        await self.db.commit()
