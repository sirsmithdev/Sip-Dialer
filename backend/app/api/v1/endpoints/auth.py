"""
Authentication endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.schemas.auth import Token, LoginRequest, RefreshTokenRequest
from app.schemas.user import UserResponse
from app.services.user_service import UserService
from app.models.user import User

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 compatible login endpoint.
    Returns access and refresh tokens.
    """
    user_service = UserService(db)
    user = await user_service.authenticate(
        email=form_data.username,
        password=form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    # Update last login
    await user_service.update_last_login(user)

    # Create tokens with additional claims
    additional_claims = {
        "email": user.email,
        "role": user.role,
        "org_id": user.organization_id,
    }

    return Token(
        access_token=create_access_token(
            subject=user.id,
            additional_claims=additional_claims
        ),
        refresh_token=create_refresh_token(subject=user.id),
        token_type="bearer"
    )


@router.post("/login/json", response_model=Token)
async def login_json(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    JSON login endpoint (alternative to OAuth2 form).
    Returns access and refresh tokens.
    """
    user_service = UserService(db)
    user = await user_service.authenticate(
        email=login_data.email,
        password=login_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    await user_service.update_last_login(user)

    additional_claims = {
        "email": user.email,
        "role": user.role,
        "org_id": user.organization_id,
    }

    return Token(
        access_token=create_access_token(
            subject=user.id,
            additional_claims=additional_claims
        ),
        refresh_token=create_refresh_token(subject=user.id),
        token_type="bearer"
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    payload = decode_token(refresh_data.refresh_token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    additional_claims = {
        "email": user.email,
        "role": user.role,
        "org_id": user.organization_id,
    }

    return Token(
        access_token=create_access_token(
            subject=user.id,
            additional_claims=additional_claims
        ),
        refresh_token=create_refresh_token(subject=user.id),
        token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information.
    """
    return current_user


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout endpoint.
    Note: JWT tokens are stateless, so this is mostly for client-side cleanup.
    In production, you might want to implement token blacklisting.
    """
    return {"message": "Successfully logged out"}
