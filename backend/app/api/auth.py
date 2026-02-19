"""
Auth API — Authentication endpoints (login, register).

Security:
- Passwords hashed with bcrypt (12 rounds)
- JWT tokens with configurable expiry
- Registration restricted to admin role
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserLogin, UserCreate, UserResponse, TokenResponse
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    hash_password,
)
from app.middleware.role_guard import get_current_user, require_admin

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and return JWT access token.
    """
    user = await authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
    })

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Register a new user. Admin-only endpoint.
    Enforces unique email constraint.
    """
    # Check for existing email
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    user = User(
        name=user_data.name,
        email=user_data.email,
        role=UserRole(user_data.role),
        hashed_password=hash_password(user_data.password),
    )
    db.add(user)
    await db.flush()

    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Return the currently authenticated user's information."""
    return UserResponse.model_validate(current_user)
