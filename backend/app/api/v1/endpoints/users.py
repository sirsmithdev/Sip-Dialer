"""
User management endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user, get_current_superuser
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.user_service import UserService
from app.models.user import User

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List users. Non-superusers only see users in their organization.
    """
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
    current_user: User = Depends(get_current_superuser)
):
    """
    Create a new user. Superuser only.
    """
    user_service = UserService(db)

    existing_user = await user_service.get_by_email(user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
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
    Update user. Users can update their own profile, superusers can update anyone.
    """
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check permissions
    if not current_user.is_superuser and user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )

    # Non-superusers cannot change their own role
    if not current_user.is_superuser and user_in.role is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change your own role"
        )

    user = await user_service.update(user, user_in)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    Delete user. Superuser only.
    """
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

    await user_service.delete(user)
