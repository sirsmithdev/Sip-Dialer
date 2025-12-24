"""
User management endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user, get_current_superuser, require_roles
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.user_service import UserService
from app.models.user import User, UserRole

router = APIRouter()


def can_manage_users(user: User) -> bool:
    """Check if user has permission to manage other users."""
    return user.is_superuser or user.role == UserRole.ADMIN


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List users. Non-superusers only see users in their organization.
    Requires admin role or superuser status.
    """
    if not can_manage_users(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to list users"
        )

    query = select(User)

    if not current_user.is_superuser:
        query = query.where(User.organization_id == current_user.organization_id)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return users


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new user. Requires admin role or superuser status.
    Admins can only create users in their own organization.
    """
    if not can_manage_users(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create users"
        )

    user_service = UserService(db)

    existing_user = await user_service.get_by_email(user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Non-superusers can only create users in their organization
    if not current_user.is_superuser:
        # Force the new user into the same organization
        user_in_dict = user_in.model_dump()
        user_in_dict['organization_id'] = current_user.organization_id
        user_in = UserCreate(**user_in_dict)

    # Admins cannot create superusers
    if not current_user.is_superuser and hasattr(user_in, 'is_superuser') and user_in.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can create other superusers"
        )

    user = await user_service.create(user_in)
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get user by ID.
    """
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Non-superusers can only view users in their organization
    if not current_user.is_superuser and user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user"
        )

    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update user. Users can update their own profile.
    Admins can update users in their organization.
    Superusers can update anyone.
    """
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    is_self = user.id == current_user.id
    is_admin = can_manage_users(current_user)
    is_same_org = user.organization_id == current_user.organization_id

    # Check permissions
    if not current_user.is_superuser:
        # Non-superusers can only update users in their organization
        if not is_same_org and not is_self:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this user"
            )
        # Non-admins can only update themselves
        if not is_admin and not is_self:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this user"
            )

    # Users cannot change their own role
    if is_self and user_in.role is not None and user_in.role != user.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change your own role"
        )

    # Non-superusers cannot promote to superuser
    if not current_user.is_superuser and hasattr(user_in, 'is_superuser') and user_in.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can promote to superuser"
        )

    # Admins cannot modify superusers
    if not current_user.is_superuser and user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify superuser accounts"
        )

    user = await user_service.update(user, user_in)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete user. Requires admin role or superuser status.
    Admins can only delete users in their organization.
    """
    if not can_manage_users(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete users"
        )

    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )

    # Non-superusers can only delete users in their organization
    if not current_user.is_superuser and user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user"
        )

    # Admins cannot delete superusers
    if not current_user.is_superuser and user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete superuser accounts"
        )

    await user_service.delete(user)
